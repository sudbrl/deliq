import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile

# 1. Must be the first Streamlit command
st.set_page_config(
    page_title="Risk Analytics Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# STYLING - Clean Professional Theme
# -------------------------------------------------
def apply_custom_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        
        * { font-family: 'Poppins', sans-serif; }
        
        .stApp {
            background: linear-gradient(to bottom, #0f0c29, #302b63, #24243e);
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Centered Login Box Fix */
        .login-box {
            background: rgba(255, 255, 255, 0.95);
            padding: 2.5rem;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 450px;
            margin: auto;
        }
        
        .login-header { text-align: center; margin-bottom: 1.5rem; }
        .login-icon { font-size: 3.5rem; }
        .login-title { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; }
        
        .metric-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 15px;
            color: white;
            box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
            margin-bottom: 1rem;
        }
        
        .badge-low { background: #10b981; color: white; padding: 0.2rem 1rem; border-radius: 20px; }
        .badge-medium { background: #f59e0b; color: white; padding: 0.2rem 1rem; border-radius: 20px; }
        .badge-high { background: #ef4444; color: white; padding: 0.2rem 1rem; border-radius: 20px; }
        
        .status-badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; border-radius: 20px; font-weight: 600; }
        .status-active { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid #10b981; }
        .status-settled { background: rgba(100, 116, 139, 0.1); color: #94a3b8; border: 1px solid #94a3b8; }
        
        .landing-container {
            background: rgba(255, 255, 255, 0.95);
            padding: 3rem 2rem;
            border-radius: 20px;
            text-align: center;
            margin-top: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True

    apply_custom_styling()
    
    # Professional Login UI
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class='login-box'>
                <div class='login-header'>
                    <div class='login-icon'>🛡️</div>
                    <h1 class='login-title'>Risk Analytics Platform</h1>
                    <p style='color: #666;'>Secure Portfolio Access</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Inputs moved outside markdown for functionality
        u = st.text_input("Username", key="u_field")
        p = st.text_input("Password", type="password", key="p_field")
        
        if st.button("🔐 Sign In", use_container_width=True):
            # Check if secrets exist to avoid crash
            if "passwords" in st.secrets:
                if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
            else:
                # Local dev fallback
                if u == "admin" and p == "admin":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.warning("Credential secret not configured.")
    return False

# -------------------------------------------------
# ANALYTICS ENGINE (Your Original Logic)
# -------------------------------------------------
def analyze_loan(row, months):
    dpd = row[months].astype(object)
    first_idx = dpd.first_valid_index()
    
    if first_idx is None:
        return pd.DataFrame(), pd.DataFrame()
    
    last_idx = dpd.last_valid_index()
    start_pos = months.get_loc(first_idx)
    end_pos = months.get_loc(last_idx)
    
    active_dpd = dpd.iloc[start_pos:end_pos+1].fillna(0).astype(float)
    status = ["Not Disbursed"]*start_pos + ["Active"]*(end_pos - start_pos + 1) + ["Settled"]*(len(months) - 1 - end_pos)
    
    df = pd.DataFrame({
        "Month": months.astype(str),
        "DPD": dpd.fillna(0).astype(float).values,
        "Status": status
    })
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    
    max_d = active_dpd.max()
    metrics = [
        ("Loan Status", "Settled" if end_pos < len(months)-1 else "Active", "Current State"),
        ("Active Tenure", f"{len(active_dpd)} Months", "Loan Age"),
        ("Delinquency Density", f"{(active_dpd > 0).sum()/len(active_dpd):.1%}", "Frequency"),
        ("Maximum DPD", f"{int(max_d)} Days", "Peak Risk"),
        ("Sticky Bucket", "90+" if max_d >= 90 else "30-89" if max_d >= 30 else "0-29", "Risk Tier"),
        ("Total Cumulative DPD", f"{int(active_dpd.sum())}", "Risk Volume")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Importance"])

# -------------------------------------------------
# PDF GENERATION (Your Original Logic)
# -------------------------------------------------
def create_pdf_chart(df):
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#667eea", label="DPD")
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45, fontsize=8)
    plt.tight_layout()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp.name)
    plt.close(fig)
    return tmp.name

def build_pdf(story, code, row, df, metrics_df, styles):
    story.append(Paragraph(f"Loan Performance Report: {code}", styles['Heading1']))
    m_data = [["Metric", "Value", "Perspective"]] + metrics_df.values.tolist()
    mt = Table(m_data, colWidths=[2*inch, 1.5*inch, 3*inch])
    mt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#667eea')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    story.append(mt)
    story.append(Spacer(1, 20))
    story.append(Image(create_pdf_chart(df), width=6*inch, height=3*inch))
    story.append(PageBreak())

# -------------------------------------------------
# DISPLAY METRICS (Your Original UI)
# -------------------------------------------------
def display_metrics(metrics_df, sanctioned, balance):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='metric-box'><div class='metric-label'>SANCTIONED</div><div class='metric-value'>Rs. {sanctioned:,.0f}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-box'><div class='metric-label'>OUTSTANDING</div><div class='metric-value'>Rs. {balance:,.0f}</div></div>", unsafe_allow_html=True)
    
    cols = st.columns(3)
    for idx, (_, row) in enumerate(metrics_df.iterrows()):
        with cols[idx % 3]:
            st.markdown(f"<div class='metric-box'><strong>{row['Metric']}</strong><br>{row['Value']}</div>", unsafe_allow_html=True)

# -------------------------------------------------
# MAIN APPLICATION LOGIC
# -------------------------------------------------
if not check_password():
    st.stop()

apply_custom_styling()

with st.sidebar:
    st.markdown("### 🛡️ Risk Portal")
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()
    uploaded_file = st.file_uploader("📁 Upload Excel File", type=["xlsx"])

if not uploaded_file:
    # RECTIFIED: This block now only runs when NO file is present
    st.markdown("""
        <div class='landing-container'>
            <h1 style='color: #302b63;'>Risk Analytics Platform</h1>
            <p>Please upload an Excel file from the sidebar to begin analysis.</p>
            <div style='display: flex; justify-content: space-around; margin-top: 2rem;'>
                <div>📊 <b>Analytics</b></div>
                <div>📋 <b>PDF Reports</b></div>
                <div>🔒 <b>Secure</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    # RECTIFIED: Logic to prevent crash if file format is wrong
    try:
        raw_data = pd.read_excel(uploaded_file)
        codes = raw_data.iloc[:, 0].unique()
        months = raw_data.columns[3:]
        
        output_excel = BytesIO()
        bulk_buf = BytesIO()
        doc = SimpleDocTemplate(bulk_buf, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            tabs = st.tabs([f"📄 {str(c)}" for c in codes])
            for tab, code in zip(tabs, codes):
                row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                df, metrics_df = analyze_loan(row, months)
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)
                
                with tab:
                    st.markdown(f"## Account: {code}")
                    display_metrics(metrics_df, row.iloc[1], row.iloc[2])
                    
                    # Charting
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(df["Month"], df["DPD"], marker="o", color="#667eea")
                    plt.xticks(rotation=45)
                    st.pyplot(fig)
                    
                    # Individual PDF
                    single_buf = BytesIO()
                    single_doc = SimpleDocTemplate(single_buf, pagesize=letter)
                    single_story = []
                    build_pdf(single_story, code, row, df, metrics_df, styles)
                    single_doc.build(single_story)
                    st.download_button(f"📥 Download Report {code}", single_buf.getvalue(), f"Report_{code}.pdf")
                    
                    build_pdf(story, code, row, df, metrics_df, styles)

        doc.build(story)
        st.sidebar.markdown("---")
        st.sidebar.download_button("📂 Download All (Excel)", output_excel.getvalue(), "Portfolio.xlsx")
        st.sidebar.download_button("📦 Download All (PDF)", bulk_buf.getvalue(), "Reports.pdf")
        
    except Exception as e:
        st.error(f"Error processing file. Please ensure columns follow the format [ID, Sanctioned, Balance, Months...]. Error: {e}")
