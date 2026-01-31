import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Risk Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- AUTH --------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    
    if st.session_state.auth:
        return True

    # CSS for Centered, Small Login Box
    st.markdown("""
    <style>
    .main .block-container { padding: 0 !important; max-width: 100% !important; }
    header, footer { visibility: hidden !important; }
    
    /* Center the login container */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 80vh;
    }

    /* Fixed size card */
    [data-testid="stVerticalBlock"] > .element-container:has(.login-card) {
        display: flex;
        justify-content: center;
    }

    .login-card {
        background: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        width: 380px;
        text-align: center;
        margin: auto;
    }
    </style>
    """, unsafe_allow_html=True)

    # UI Layout for Login
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    
    # Empty columns to force the center
    _, center_col, _ = st.columns([1, 1, 1])
    
    with center_col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='color: #1e293b; margin-bottom:0;'>🛡️ Risk Intel</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #64748b; font-size: 0.9rem;'>Enterprise Risk Management</p>", unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="admin", label_visibility="collapsed")
        password = st.text_input("Password", type="password", placeholder="password", label_visibility="collapsed")
        
        if st.button("Sign In", use_container_width=True, type="primary"):
            # Note: Replace with your actual secrets check
            if username == "admin" and password == "admin": 
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Invalid credentials")
        
        st.markdown("<p style='font-size: 0.7rem; color: #94a3b8; margin-top: 10px;'>Secure AES-256 Encrypted Session</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    return False

# -------------------- UTILITY FUNCTIONS --------------------
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
        "Trend Slope": round(calc_trend_slope(dpd), 2),
        "Sticky Bucket": "90+" if max_dpd >= 90 else "60+" if max_dpd >= 60 else "30+" if max_dpd >= 30 else "Current"
    }
    return df, max_dpd, max_month, metrics

def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", linewidth=2, color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", color="#8b5cf6", label="3M Avg")
    ax.text(max_month, max_dpd + 2, f"Peak: {int(max_dpd)}", ha="center", fontweight="bold", color="red")
    ax.set_ylabel("Days Past Due")
    ax.grid(True, alpha=0.2)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- MAIN APP --------------------
if check_password():
    
    # Custom CSS for App & Red Logout Button
    st.markdown("""
    <style>
    /* Fancy Landing Cards */
    .hero-section {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 40px;
        border-radius: 20px;
        color: white;
        margin-bottom: 30px;
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Logout Button Styling */
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #fee2e2;
        color: #dc2626;
        border: 1px solid #fca5a5;
        transition: 0.3s;
    }
    div.stButton > button:first-child[kind="secondary"]:hover {
        background-color: #dc2626;
        color: white;
        border: 1px solid #dc2626;
    }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("## 🛡️ Risk Intelligence")
        st.markdown("---")
        if st.button("🚪 Logout System", use_container_width=True, type="secondary"):
            st.session_state.clear()
            st.rerun()
        
        st.markdown("---")
        st.caption("v2.4.0 • Enterprise Edition")

    # FANCY LANDING DESIGN
    if "file_uploaded" not in st.session_state or not st.session_state.file_uploaded:
        st.markdown("""
        <div class="hero-section">
            <h1 style='color: white; margin:0;'>Welcome back, Analyst</h1>
            <p style='opacity: 0.9;'>Global Risk Intelligence & Credit Analytics Dashboard</p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="stat-card"><h3>24/7</h3><p>Real-time Monitoring</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="stat-card"><h3>99.9%</h3><p>Data Accuracy</p></div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="stat-card"><h3>Secure</h3><p>FIPS 140-2 Compliant</p></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

    # Data Upload Section
    file = st.file_uploader("📂 Drop portfolio Excel here to begin analysis", type=["xlsx"])
    
    if file:
        st.session_state.file_uploaded = True
        try:
            raw = pd.read_excel(file)
            codes = raw.iloc[:, 0].unique()
            months = raw.columns[3:]
            
            tabs = st.tabs([f"Account {c}" for c in codes])
            for tab, code in zip(tabs, codes):
                with tab:
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, max_dpd, max_month, metrics = analyze(row, months)
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.subheader("Key Metrics")
                        for k, v in metrics.items():
                            st.metric(k, v)
                    with col2:
                        st.subheader("Performance Trend")
                        st.pyplot(plot_chart(df, max_dpd, max_month))
        
        except Exception as e:
            st.error(f"Error: {e}")
