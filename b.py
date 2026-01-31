import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile

# -------------------------------------------------
# CONFIG & STYLING
# -------------------------------------------------
st.set_page_config(page_title="Risk Analytics Platform", page_icon="🛡️", layout="wide")

def apply_custom_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        * { font-family: 'Poppins', sans-serif; }
        .stApp { background-color: #f8fafc; color: #1e293b; }
        
        /* Modern Pill Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #f1f5f9; padding: 8px; border-radius: 12px; }
        .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px; color: #64748b; padding: 8px 16px; border: 1px solid #e2e8f0; }
        .stTabs [aria-selected="true"] { background-color: #4f46e5 !important; color: white !important; border: none; }

        /* Metric Cards */
        .metric-card {
            background: white;
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 5px solid #4f46e5;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 10px;
        }
        .metric-label { font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
        .metric-value { font-size: 1.2rem; color: #1e293b; font-weight: 700; }
        
        .login-box { background: white; padding: 3rem; border-radius: 20px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.2); max-width: 450px; margin: auto; }
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# CORE ENGINE
# -------------------------------------------------
def analyze_loan(row, months):
    dpd = row[months].astype(object)
    first_idx = dpd.first_valid_index()
    if first_idx is None: return pd.DataFrame(), pd.DataFrame()
    
    last_idx = dpd.last_valid_index()
    start_pos = months.get_loc(first_idx)
    end_pos = months.get_loc(last_idx)
    
    active_dpd = dpd.iloc[start_pos:end_pos+1].fillna(0).astype(float)
    status_list = ["Not Disbursed"]*start_pos + ["Active"]*(end_pos - start_pos + 1) + ["Settled"]*(len(months) - 1 - end_pos)
    
    df = pd.DataFrame({
        "Month": months.astype(str),
        "DPD": dpd.fillna(0).astype(float).values,
        "Status": status_list
    })
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    
    max_d = active_dpd.max()
    metrics = [
        ("Loan Status", "Settled" if end_pos < len(months)-1 else "Active", "Current State"),
        ("Tenure", f"{len(active_dpd)} Months", "Loan Age"),
        ("Density", f"{(active_dpd > 0).sum()/len(active_dpd):.1%}", "Frequency"),
        ("Max DPD", f"{int(max_d)} Days", "Peak Risk"),
        ("Sticky Bucket", "90+" if max_d >= 90 else "30-89" if max_d >= 30 else "0-29", "Risk Tier"),
        ("Total DPD", f"{int(active_dpd.sum())}", "Risk Volume")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Importance"])

# -------------------------------------------------
# CHART & PDF LOGIC
# -------------------------------------------------
def get_plot(df, is_pdf=False):
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#4f46e5", label="DPD")
    
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        p_idx = plot_df["DPD"].idxmax()
        p_val = plot_df["DPD"].max()
        ax.plot(p_idx, p_val, marker='*', color='red', markersize=12)
        ax.annotate(f'PEAK: {int(p_val)}', (p_idx, p_val), xytext=(0, 10), textcoords='offset points', ha='center', weight='bold', color='red')
    
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45)
    plt.tight_layout()
    
    if is_pdf:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(tmp.name)
        plt.close(fig)
        return tmp.name
    return fig

def create_pdf(code, df, metrics_df, sanctioned, balance):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom Style for Table
    story = [
        Paragraph(f"Executive Risk Report: {code}", styles['Heading1']),
        Spacer(1, 10),
        Paragraph(f"Sanctioned: Rs. {sanctioned:,.0f} | Balance: Rs. {balance:,.0f}", styles['Normal']),
        Spacer(1, 15)
    ]
    
    # Metrics Table
    data = [["Metric", "Value", "Observation"]] + metrics_df.values.tolist()
    t = Table(data, colWidths=[1.8*inch, 1.5*inch, 3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(t)
    story.append(Spacer(1, 20))
    story.append(Image(get_plot(df, True), width=6.5*inch, height=2.8*inch))
    doc.build(story)
    return buf.getvalue()

# -------------------------------------------------
# APP LOGIC
# -------------------------------------------------
apply_custom_styling()

if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.title("🛡️ Risk Portal")
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("Sign In", use_container_width=True):
            if u == "admin" and p == "admin": 
                st.session_state.auth = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
else:
    with st.sidebar:
        st.title("🛡️ Risk Engine")
        uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])
        if st.button("Logout"): 
            st.session_state.auth = False
            st.rerun()

    if uploaded_file:
        raw_data = pd.read_excel(uploaded_file)
        codes = raw_data.iloc[:, 0].unique()
        months = raw_data.columns[3:]
        
        output_excel = BytesIO()
        summary_list = []
        
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            tabs = st.tabs([f"A/C {c}" for c in codes])
            for tab, code in zip(tabs, codes):
                row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                df, m_df = analyze_loan(row, months)
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)
                
                # Metrics for Excel Summary
                summary_row = m_df.set_index('Metric')['Value'].to_dict()
                summary_row['Account'] = code
                summary_list.append(summary_row)
                
                with tab:
                    st.markdown(f"### Analysis: {code}")
                    # UI Metrics Display
                    m_cols = st.columns(3)
                    for idx, (_, m_row) in enumerate(m_df.iterrows()):
                        m_cols[idx % 3].markdown(f"""
                            <div class='metric-card'>
                                <div class='metric-label'>{m_row['Metric']}</div>
                                <div class='metric-value'>{m_row['Value']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    st.pyplot(get_plot(df))
                    st.download_button(f"📥 Download Report", create_pdf(code, df, m_df, row.iloc[1], row.iloc[2]), f"{code}.pdf")
            
            pd.DataFrame(summary_list).to_excel(writer, sheet_name="Summary_Metrics", index=False)

        st.sidebar.download_button("📂 Export All (Excel)", output_excel.getvalue(), "Risk_Summary.xlsx")
