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
                # Using "admin" as default if no secrets found
                if user == "admin" and pwd == "admin":
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)
    return False

# -------------------- STATISTICAL ENGINES --------------------
def calc_skew(x):
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 3) if s != 0 else 0

def calc_kurtosis(x):
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 4) if s != 0 else 0

def calc_trend_slope(y):
    x = np.arange(len(y))
    num = np.sum((x - x.mean()) * (y - y.mean()))
    den = np.sum((x - x.mean()) ** 2)
    return num / den if den != 0 else 0

def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    max_v = dpd.max()
    max_m = df.loc[df["DPD"].idxmax(), "Month"]
    metrics = {"Mean DPD": round(np.mean(dpd), 2), "Max DPD": int(max_v), "Trend": round(calc_trend_slope(dpd), 2)}
    return df, max_v, max_m, metrics

def build_excel_metrics(dpd_series, months):
    dpd = dpd_series.values.astype(float)
    metrics = [
        ["Mean DPD", round(np.mean(dpd), 2), "Average delinquency"],
        ["Max DPD", int(np.max(dpd)), "Worst performing month"],
        ["Std Deviation", round(np.std(dpd, ddof=1), 2), "Volatility"],
        ["Cumulative DPD", int(dpd.sum()), "Total lifetime exposure"],
        ["Trend Slope", round(calc_trend_slope(dpd), 2), "Monthly change rate"],
        ["Sticky Bucket", "90+" if np.max(dpd) >= 90 else "Current", "Worst historical bucket"]
    ]
    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", color="#8b5cf6", label="3M Avg")
    ax.set_ylabel("DPD")
    ax.grid(True, alpha=0.1)
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def build_pdf(story, code, df, max_dpd, max_month, metrics):
    styles = getSampleStyleSheet()
    story.append(Paragraph(f"Account Analysis: {code}", styles['Heading1']))
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

    # Sidebar: Uploader & Download Buttons
    with st.sidebar:
        st.markdown("## 🛡️ Risk Intelligence")
        st.markdown("---")
        
        file = st.file_uploader("📂 Upload Portfolio Excel", type=["xlsx"])
        
        st.markdown("---")
        if st.button("🚪 Logout System", use_container_width=True, type="secondary"):
            st.session_state.auth = False
            st.rerun()
        
        st.markdown("---")
        st.caption("Active Session | v2.4.0")

    # App Main Body
    if not file:
        st.markdown('<div class="hero-section"><h1>Welcome to Risk Intel</h1><p>Use the sidebar to upload your portfolio data.</p></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown('<div class="stat-card"><h4>Security</h4><p>Bank-grade encryption</p></div>', unsafe_allow_html=True)
        with c2: st.markdown('<div class="stat-card"><h4>Accuracy</h4><p>Verified Risk Logic</p></div>', unsafe_allow_html=True)
        with c3: st.markdown('<div class="stat-card"><h4>Uptime</h4><p>Enterprise Active</p></div>', unsafe_allow_html=True)
    else:
        try:
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
                    
                    with tab:
                        cl, cr = st.columns([1, 2])
                        with cl:
                            st.subheader("Account Metrics")
                            for k, v in metrics.items(): st.metric(k, v)
                        with cr:
                            st.subheader("DPD Trend Analysis")
                            st.pyplot(plot_chart(df, max_v, max_m))
                        
                        st.dataframe(build_excel_metrics(df["DPD"], months), use_container_width=True, hide_index=True)

                    # Export Logic
                    df.to_excel(writer, f"Data_{code}", index=False)
                    build_excel_metrics(df["DPD"], months).to_excel(writer, f"Metrics_{code}", index=False)
                    build_pdf(story, code, df, max_v, max_m, metrics)

            doc.build(story)
            
            # Place downloads in Sidebar once processed
            with st.sidebar:
                st.markdown("### 💾 Export Reports")
                st.download_button("📊 Download Excel", excel_buf.getvalue(), "Risk_Analysis.xlsx", use_container_width=True)
                st.download_button("📄 Download PDF", pdf_buf.getvalue(), "Executive_Report.pdf", use_container_width=True)
                
        except Exception as e:
            st.error(f"Error processing file: {e}")
