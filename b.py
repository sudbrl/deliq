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

# 1. Page Configuration
st.set_page_config(
    page_title="Risk Analytics Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# STYLING - Restored & Rectified for Contrast
# -------------------------------------------------
def apply_custom_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        * { font-family: 'Poppins', sans-serif; }
        
        /* Background fix for readability */
        .stApp {
            background-color: #f4f7f9;
            color: #1a1a2e;
        }

        /* Modern Pill Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #e2e8f0;
            padding: 6px;
            border-radius: 12px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 8px;
            color: #475569;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4f46e5 !important;
            color: white !important;
        }

        /* Metric Cards */
        .metric-box {
            background: white;
            padding: 1.2rem;
            border-radius: 15px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .login-box {
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
            margin: auto;
            max-width: 450px;
        }
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# CORE ANALYTICS
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
        ("Loan Status", "Settled" if end_pos < len(months)-1 else "Active", "Status"),
        ("Max DPD", f"{int(max_d)} Days", "Peak Risk"),
        ("Density", f"{(active_dpd > 0).sum()/len(active_dpd):.1%}", "Frequency")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Importance"])

# -------------------------------------------------
# CHARTING WITH HIGHLIGHTING
# -------------------------------------------------
def get_annotated_plot(df, is_pdf=False):
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
    
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#4f46e5", linewidth=2, label="DPD")
    
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        p_idx = plot_df["DPD"].idxmax()
        p_val = plot_df["DPD"].max()
        # Highlight point
        ax.scatter(p_idx, p_val, color='red', s=120, zorder=5, edgecolors='black')
        ax.annotate(f'PEAK: {int(p_val)}', (p_idx, p_val), xytext=(0, 10), 
                    textcoords='offset points', ha='center', weight='bold', color='red')
    
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45)
    plt.tight_layout()
    
    if is_pdf:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(tmp.name)
        plt.close(fig)
        return tmp.name
    return fig

# -------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------
def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated: return True
    apply_custom_styling()
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<div class='login-box'><h2 style='text-align:center'>🛡️ Risk Portal</h2>", unsafe_allow_html=True)
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Sign In", use_container_width=True):
            if "passwords" in st.secrets and u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state.authenticated = True
                st.rerun()
            elif u == "admin" and p == "admin": # Default fallback
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Access Denied")
    return False

# -------------------------------------------------
# MAIN APP
# -------------------------------------------------
if check_password():
    apply_custom_styling()
    with st.sidebar:
        st.title("🛡️ Risk Analytics")
        if st.button("Logout"): 
            st.session_state.authenticated = False
            st.rerun()
        uploaded_file = st.file_uploader("Upload Delinquency File", type=["xlsx"])

    if not uploaded_file:
        st.markdown("<div style='text-align:center; padding-top:100px;'><h1>Ready for Analysis</h1><p>Upload your Excel file to begin.</p></div>", unsafe_allow_html=True)
    else:
        raw_data = pd.read_excel(uploaded_file)
        codes = raw_data.iloc[:, 0].unique()
        months = raw_data.columns[3:]
        
        output_excel = BytesIO()
        bulk_metrics = []
        
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            tabs = st.tabs([f"A/C {c}" for c in codes])
            
            for tab, code in zip(tabs, codes):
                row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                df, metrics_df = analyze_loan(row, months)
                
                # Build metric record for Excel summary sheet
                m_record = metrics_df.set_index('Metric')['Value'].to_dict()
                m_record['Account_Code'] = code
                bulk_metrics.append(m_record)
                
                # Write individual account data to Excel
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)
                
                with tab:
                    st.markdown(f"### Performance: {code}")
                    cols = st.columns(3)
                    for i, (idx, m_row) in enumerate(metrics_df.iterrows()):
                        cols[i].markdown(f"<div class='metric-box'><b>{m_row['Metric']}</b><br>{m_row['Value']}</div>", unsafe_allow_html=True)
                    
                    st.pyplot(get_annotated_plot(df))
                    
                    # Individual PDF Report with Highlight
                    pdf_buf = BytesIO()
                    doc = SimpleDocTemplate(pdf_buf, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = [
                        Paragraph(f"Risk Report: {code}", styles['Heading1']),
                        Spacer(1, 12),
                        Image(get_annotated_plot(df, True), width=6*inch, height=2.5*inch)
                    ]
                    doc.build(story)
                    st.download_button(f"📥 PDF Report {code}", pdf_buf.getvalue(), f"{code}.pdf")

            # Finalize Excel Summary Metrics Sheet
            pd.DataFrame(bulk_metrics).to_excel(writer, sheet_name="Summary_Metrics", index=False)

        st.sidebar.markdown("---")
        st.sidebar.download_button("📂 Bulk Export (Excel)", output_excel.getvalue(), "Risk_Analysis_Complete.xlsx")
