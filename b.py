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

# -------------------- AUTHENTICATION --------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    
    if st.session_state.auth:
        return True

    # --- LOGIN PAGE SPECIFIC STYLES ---
    st.markdown("""
    <style>
    /* background and layout */
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"], header, footer { visibility: hidden !important; }
    
    /* Centering the box */
    .main .block-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 90vh;
    }

    .login-container {
        background: white;
        padding: 3rem;
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
        text-align: center;
        border: 1px solid #e2e8f0;
        width: 100%;
        max-width: 420px;
        margin: auto;
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

    /* Custom Input Styling Override */
    div[data-testid="stTextInput"] input {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
        background: #f8fafc !important;
        transition: all 0.2s;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1) !important;
        background: white !important;
    }
    
    /* Primary Sign In Button */
    div.stButton > button:first-child[kind="primary"] {
        width: 100%;
        border-radius: 12px;
        padding: 0.6rem;
        background: #0f172a;
        font-weight: 600;
        border: none;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Login UI
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">Risk Intel</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Sign in to access Enterprise Analytics</div>', unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        
        if st.button("Sign In", type="primary"):
            # Check against Streamlit secrets or hardcoded for demo
            if username == "admin" and password == "admin":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)
    
    return False

# -------------------- STATISTICAL ENGINES --------------------
def calc_skew(x):
    m = np.mean(x)
    s = np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 3) if s != 0 else 0

def calc_kurtosis(x):
    m = np.mean(x)
    s = np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 4) if s != 0 else 0

def calc_mode(x):
    mode_result = pd.Series(x).mode()
    return mode_result.iloc[0] if len(mode_result) > 0 else 0

def calc_trend_slope(y):
    x = np.arange(len(y))
    x_mean, y_mean = x.mean(), y.mean()
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)
    return num / den if den != 0 else 0

# -------------------- ANALYSIS FUNCTIONS --------------------
def build_excel_metrics(dpd_series, months):
    dpd = dpd_series.values.astype(float)
    metrics = [
        ["Mean DPD", round(np.mean(dpd), 2), "Average delinquency"],
        ["Max DPD", int(np.max(dpd)), "Worst performing month"],
        ["Std Deviation", round(np.std(dpd, ddof=1), 2), "Volatility"],
        ["Cumulative DPD", int(dpd.sum()), "Total exposure"],
        ["Trend Slope", round(calc_trend_slope(dpd), 2), "Monthly change rate"],
        ["Sticky Bucket", "90+" if np.max(dpd) >= 90 else "Current", "Worst bucket"]
    ]
    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

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
        "Trend Slope": round(calc_trend_slope(dpd), 2)
    }
    return df, max_dpd, max_month, metrics

def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", color="#8b5cf6", label="3M Avg")
    ax.text(max_month, max_dpd + 5, f"MAX {int(max_dpd)}", ha="center", color="red", fontweight="bold")
    ax.grid(True, alpha=0.2)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- MAIN APP --------------------
if check_password():
    
    # CSS for Post-Login App and RED Logout Button
    st.markdown("""
    <style>
    /* Dashboard Hero Design */
    .hero-section {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        padding: 40px;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
    }
    .hero-section h1 { color: white !important; }
    
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }

    /* RED LOGOUT BUTTON STYLING */
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #fee2e2 !important;
        color: #dc2626 !important;
        border: 1px solid #fca5a5 !important;
        font-weight: 600;
        transition: 0.3s;
    }
    div.stButton > button:first-child[kind="secondary"]:hover {
        background-color: #dc2626 !important;
        color: white !important;
        border-color: #dc2626 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("## 🛡️ Risk Intel")
        st.markdown("---")
        if st.button("🚪 Logout System", use_container_width=True, type="secondary"):
            st.session_state.auth = False
            st.rerun()
        st.markdown("---")
        st.info("System Online: v2.4.0")

    # POST-LOGIN LANDING (Fancy Design)
    if "file_processed" not in st.session_state:
        st.markdown("""
        <div class="hero-section">
            <h1>Welcome to Risk Intelligence</h1>
            <p>Upload your portfolio Excel data to generate deep-dive risk metrics, trend analyses, and PDF reports.</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="stat-card"><h4>Secure Analytics</h4><p>Bank-grade data encryption.</p></div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="stat-card"><h4>Automated Reporting</h4><p>One-click PDF/Excel export.</p></div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="stat-card"><h4>Pattern Detection</h4><p>Trend and seasonality engine.</p></div>', unsafe_allow_html=True)
        st.markdown("---")

    # File Upload and Processing
    file = st.file_uploader("📂 Upload Portfolio Excel File", type=["xlsx"])
    
    if file:
        st.session_state.file_processed = True
        try:
            raw = pd.read_excel(file)
            codes = raw.iloc[:, 0].unique()
            months = raw.columns[3:]
            
            excel_buf = BytesIO()
            with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
                tabs = st.tabs([f"Account {c}" for c in codes])
                
                for tab, code in zip(tabs, codes):
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, max_dpd, max_month, metrics = analyze(row, months)
                    
                    with tab:
                        c_left, c_right = st.columns([1, 2])
                        with c_left:
                            st.markdown("#### Key Metrics")
                            for k, v in metrics.items():
                                st.metric(k, v)
                        with c_right:
                            st.markdown("#### DPD Trend")
                            st.pyplot(plot_chart(df, max_dpd, max_month))
                        
                        st.markdown("#### Detailed Risk Metrics")
                        st.dataframe(build_excel_metrics(df["DPD"], months), use_container_width=True, hide_index=True)

            # Download Options
            st.markdown("---")
            st.download_button("📊 Download Compiled Excel Report", excel_buf.getvalue(), "Risk_Analysis.xlsx", use_container_width=True)
            
        except Exception as e:
            st.error(f"Error processing file: {e}")
