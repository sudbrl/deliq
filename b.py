import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Risk Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- AUTHENTICATION --------------------
def check_password():
    """Returns `True` if the user had the correct password."""

    if "auth" not in st.session_state:
        st.session_state.auth = False

    if st.session_state.auth:
        return True

    # --- LOGIN PAGE SPECIFIC STYLES ---
    st.markdown("""
    <style>
    /* Background & Global */
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"], header, footer { visibility: hidden !important; }
    
    /* Login Box Container */
    .login-container {
        background: white;
        padding: 3rem;
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    
    .login-header {
        font-size: 1.75rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #0f172a;
    }
    
    .login-sub {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }

    /* Custom Input Styling Override - Matches DTI Profile */
    div[data-testid="stTextInput"] input {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        padding: 0.75rem 1rem !important;
        background: #f8fafc !important;
    }
    
    /* Sign In Button */
    div.stButton > button:first-child[kind="primary"] {
        width: 100%;
        border-radius: 12px;
        padding: 0.6rem;
        background: #0f172a;
        font-weight: 600;
        border: none;
    }
    
    /* Center the layout vertically */
    .main .block-container {
        padding-top: 10% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Layout: Small in the middle
    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        st.markdown("""
        <div class="login-container">
            <div class="login-header">Welcome Back</div>
            <div class="login-sub">Sign in to Risk Intelligence Platform</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Use a form to capture inputs cleanly
        with st.form("login_form", clear_on_submit=False):
            # Attempt to use st.secrets if available, otherwise fallback to "admin" for testing
            username = st.text_input("Username", placeholder="admin", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="password", label_visibility="collapsed")
            submit = st.form_submit_button("Sign In", type="primary")

            if submit:
                # Logic: Check against secrets or default
                try:
                    valid_pass = st.secrets["passwords"].get(username)
                    is_correct = (valid_pass == password)
                except:
                    # Fallback for local testing if secrets aren't set up
                    is_correct = (username == "admin" and password == "admin")

                if is_correct:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

    return False

# -------------------- ANALYTICAL LOGIC --------------------
def calc_trend_slope(y):
    x = np.arange(len(y))
    x_mean, y_mean = x.mean(), y.mean()
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)
    return num / den if den != 0 else 0

def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    max_dpd = dpd.max()
    max_month = df.loc[df["DPD"].idxmax(), "Month"]
    metrics = {
        "Mean DPD": round(np.mean(dpd), 2),
        "Max DPD": int(max_dpd),
        "Cumulative DPD": int(dpd.sum()),
        "Trend": round(calc_trend_slope(dpd), 2)
    }
    return df, max_dpd, max_month, metrics

def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", color="#8b5cf6", label="3M Avg")
    ax.text(max_month, max_dpd + 2, f"PEAK: {int(max_dpd)}", ha="center", fontweight="bold", color="red")
    ax.grid(True, alpha=0.1)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- MAIN APP --------------------
if check_password():
    
    # Custom CSS for App & Red Logout Button
    st.markdown("""
    <style>
    /* Hero Section */
    .hero-container {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 50px;
        border-radius: 24px;
        color: white;
        margin-bottom: 2rem;
    }
    
    /* Sidebar Red Logout Button */
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #fee2e2 !important;
        color: #dc2626 !important;
        border: 1px solid #fca5a5 !important;
        font-weight: 600;
        transition: 0.2s;
    }
    div.stButton > button:first-child[kind="secondary"]:hover {
        background-color: #ef4444 !important;
        color: white !important;
        border-color: #ef4444 !important;
    }
    
    /* Stats Cards */
    .stat-card {
        background: white;
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("## 🛡️ Risk Intel")
        st.markdown("---")
        if st.button("🚪 Logout System", use_container_width=True, type="secondary"):
            st.session_state.auth = False
            st.rerun()
        st.markdown("---")
        st.caption("Active Session: " + pd.Timestamp.now().strftime("%H:%M"))

    # Fancy Landing (Shows when no file is uploaded)
    if "file_active" not in st.session_state or not st.session_state.file_active:
        st.markdown("""
        <div class="hero-container">
            <h1 style='color: white; margin:0;'>Welcome back, Analyst</h1>
            <p style='opacity: 0.8; font-size: 1.1rem;'>Upload portfolio data below to generate risk intelligence reports.</p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="stat-card"><h4>Security</h4><p style="color:#64748b;">AES-256 Data Encryption</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="stat-card"><h4>Compliance</h4><p style="color:#64748b;">Regulatory Standards Met</p></div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="stat-card"><h4>Support</h4><p style="color:#64748b;">24/7 Enterprise Tier</p></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # File Uploader
    file = st.file_uploader("📂 Upload Portfolio Excel File", type=["xlsx"])
    
    if file:
        st.session_state.file_active = True
        try:
            raw = pd.read_excel(file)
            codes = raw.iloc[:, 0].unique()
            months = raw.columns[3:]
            
            tabs = st.tabs([f"Account {c}" for c in codes])
            for tab, code in zip(tabs, codes):
                with tab:
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, max_dpd, max_month, metrics = analyze(row, months)
                    
                    c_left, c_right = st.columns([1, 2])
                    with c_left:
                        st.subheader("Key Performance")
                        for k, v in metrics.items():
                            st.metric(k, v)
                    with c_right:
                        st.subheader("DPD Trend")
                        st.pyplot(plot_chart(df, max_dpd, max_month))
        
        except Exception as e:
            st.error(f"Error reading file: {e}")
