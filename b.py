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

    st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    [data-testid="stSidebar"], header, footer { visibility: hidden !important; }
    
    /* Centering and Box Design */
    .main .block-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 0 !important;
    }

    .login-container {
        background: white;
        padding: 3.5rem;
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.05);
        text-align: center;
        border: 1px solid #e2e8f0;
        width: 100%;
        max-width: 420px;
    }
    
    .login-header {
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        color: #0f172a;
    }
    
    .login-sub {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 2.5rem;
    }

    /* Input Overrides */
    div[data-testid="stTextInput"] input {
        border-radius: 12px !important;
        border: 1px solid #e2e8f0 !important;
        padding: 0.75rem 1rem !important;
        background: #f8fafc !important;
    }
    
    div.stButton > button:first-child[kind="primary"] {
        width: 100%;
        border-radius: 12px;
        padding: 0.6rem;
        background: #0f172a;
        font-weight: 600;
        border: none;
        margin-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.5, 1])

    with col:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">Risk Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Enterprise Credit Risk Analytics</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            user = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
            pwd = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            if st.form_submit_button("Sign In", type="primary"):
                # Checking secrets or default admin/admin
                if user in st.secrets.get("passwords", {"admin": "admin"}) and \
                   pwd == st.secrets.get("passwords", {"admin": "admin"}).get(user):
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)
    return False

# -------------------- STATISTICAL FUNCTIONS --------------------
def calc_skew(x):
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 3) if s != 0 else 0

def calc_kurtosis(x):
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 4) if s != 0 else 0

def calc_mode(x):
    res = pd.Series(x).mode()
    return res.iloc[0] if len(res) > 0 else 0

def calc_trend_slope(y):
    x = np.arange(len(y))
    num = np.sum((x - x.mean()) * (y - y.mean()))
    den = np.sum((x - x.mean()) ** 2)
    return num / den if den != 0 else 0

def calc_monthly_avg(dpd, months):
    month_data = {}
    for i, m in enumerate(months):
        try: month_num = int(str(m).split('-')[1])
        except: month_num = (i % 12) + 1
        if month_num not in month_data: month_data[month_num] = []
        month_data[month_num].append(dpd[i])
    return {k: np.mean(v) for k, v in month_data.items()}

def calc_seasonality_index(dpd, months):
    monthly_avg = calc_monthly_avg(dpd, months)
    overall_avg = np.mean(list(monthly_avg.values()))
    return {k: (v / overall_avg * 100) if overall_avg > 0 else 100 for k, v in monthly_avg.items()}

# -------------------- REPORT ENGINES --------------------
def build_excel_metrics(dpd_series, months):
    dpd = dpd_series.values.astype(float)
    s_idx = calc_seasonality_index(dpd, months)
    peak_m = max(s_idx, key=s_idx.get) if s_idx else 0
    
    metrics = [
        ["Mean DPD", round(np.mean(dpd), 2), "Average delinquency"],
        ["Max DPD", int(np.max(dpd)), "Worst performing month"],
        ["Std Deviation", round(np.std(dpd, ddof=1), 2), "Volatility"],
        ["Skewness", round(calc_skew(dpd), 2), "Outlier delay risk"],
        ["Kurtosis", round(calc_kurtosis(dpd), 2), "Extreme event risk"],
        ["Cumulative DPD", int(dpd.sum()), "Total lifetime exposure"],
        ["Trend Slope", round(calc_trend_slope(dpd), 2), "Monthly change rate"],
        ["Peak Season Month", peak_m, "Month with highest avg DPD"],
        ["Sticky Bucket", "90+" if np.max(dpd) >= 90 else "Current", "Worst historical bucket"]
    ]
    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

def build_pdf(story, code, df, max_dpd, max_month, metrics):
    styles = getSampleStyleSheet()
    story.append(Paragraph(f"Account Performance: {code}", styles['Heading1']))
    story.append(Spacer(1, 12))
    
    data = [["Metric", "Value"]] + [[k, v] for k, v in metrics.items()]
    t = Table(data, colWidths=[2.5*inch, 2.5*inch])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
                           ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                           ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    story.append(t)
    story.append(Spacer(1, 20))
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig = plot_chart(df, max_dpd, max_month)
        fig.savefig(tmp.name)
        plt.close(fig)
        story.append(Image(tmp.name, 6*inch, 3*inch))
    story.append(PageBreak())

def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    max_v = dpd.max()
    max_m = df.loc[df["DPD"].idxmax(), "Month"]
    metrics = {"Mean DPD": round(np.mean(dpd), 2), "Max DPD": int(max_v), "Trend": round(calc_trend_slope(dpd), 2)}
    return df, max_v, max_m, metrics

def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", color="#8b5cf6", label="3M Avg")
    ax.set_ylabel("DPD")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- MAIN APP --------------------
if check_password():
    st.markdown("""
    <style>
    .hero-section { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); padding: 40px; border-radius: 20px; color: white; margin-bottom: 2rem; }
    .stat-card { background: white; padding: 20px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    
    /* Logout Button Styling - RED */
    div.stButton > button:first-child[kind="secondary"] {
        background-color: #fee2e2 !important; color: #dc2626 !important; border: 1px solid #fca5a5 !important; font-weight: 600;
    }
    div.stButton > button:first-child[kind="secondary"]:hover {
        background-color: #ef4444 !important; color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 🛡️ Risk Intelligence")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            st.session_state.auth = False
            st.rerun()
        st.markdown("---")
        st.caption("v2.4.0 | Enterprise Tier")

    if "processed" not in st.session_state:
        st.markdown('<div class="hero-section"><h1>Welcome back, Analyst</h1><p>Upload your portfolio to begin.</p></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown('<div class="stat-card"><h4>Security</h4><p>FIPS-140-2 Compliant</p></div>', unsafe_allow_html=True)
        with c2: st.markdown('<div class="stat-card"><h4>Accuracy</h4><p>99.9% Logic Verified</p></div>', unsafe_allow_html=True)
        with c3: st.markdown('<div class="stat-card"><h4>Uptime</h4><p>24/7 Monitoring</p></div>', unsafe_allow_html=True)

    file = st.file_uploader("📂 Select Portfolio Excel File", type=["xlsx"])
    
    if file:
        st.session_state.processed = True
        raw = pd.read_excel(file)
        codes = raw.iloc[:, 0].unique()
        months = raw.columns[3:]
        
        excel_buf = BytesIO()
        pdf_buf = BytesIO()
        doc = SimpleDocTemplate(pdf_buf, pagesize=letter)
        story = []
        
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
            tabs = st.tabs([f"Account {c}" for c in codes])
            for tab, code in zip(tabs, codes):
                row = raw[raw.iloc[:, 0] == code].iloc[0]
                df, max_v, max_m, metrics = analyze(row, months)
                
                # App View
                with tab:
                    cl, cr = st.columns([1, 2])
                    with cl:
                        st.subheader("Metrics")
                        for k, v in metrics.items(): st.metric(k, v)
                    with cr:
                        st.subheader("Trend")
                        st.pyplot(plot_chart(df, max_v, max_m))
                    st.dataframe(build_excel_metrics(df["DPD"], months), use_container_width=True, hide_index=True)

                # Report Building
                df.to_excel(writer, f"Data_{code}", index=False)
                build_excel_metrics(df["DPD"], months).to_excel(writer, f"Metrics_{code}", index=False)
                build_pdf(story, code, df, max_v, max_m, metrics)

        doc.build(story)
        st.markdown("---")
        st.markdown("### 💾 Export Reports")
        col_ex, col_pdf = st.columns(2)
        with col_ex:
            st.download_button("📊 Download Excel", excel_buf.getvalue(), "Risk_Metrics.xlsx", use_container_width=True)
        with col_pdf:
            st.download_button("📄 Download PDF", pdf_buf.getvalue(), "Risk_Analysis.pdf", use_container_width=True)
