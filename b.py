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

# Must be the first Streamlit command
st.set_page_config(
    page_title="Risk Analytics Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# STYLING - Rectified for Visibility
# -------------------------------------------------
def apply_custom_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        
        * { font-family: 'Poppins', sans-serif; }
        
        /* Lightened Background for better text visibility */
        .stApp {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            color: #212529;
        }

        /* Sidebar Visibility */
        [data-testid="stSidebar"] {
            background-color: #1a1a2e !important;
        }
        
        /* Modern Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }

        .stTabs [data-baseweb="tab"] {
            height: 45px;
            white-space: pre-wrap;
            background-color: #ffffff;
            border-radius: 10px;
            color: #495057;
            border: 1px solid #dee2e6;
            padding: 10px 20px;
        }

        .stTabs [aria-selected="true"] {
            background: #667eea !important;
            color: white !important;
            border: none !important;
        }

        /* Metric Box with high contrast */
        .metric-box {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            color: #1a1a2e;
            border: 1px solid #dee2e6;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
        }

        .login-box {
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            max-width: 450px;
            margin: auto;
        }
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# ANALYTICS ENGINE
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
        ("Loan Status", "Settled" if end_pos < len(months)-1 else "Active", "State"),
        ("Max DPD", f"{int(max_d)}", "Peak"),
        ("Density", f"{(active_dpd > 0).sum()/len(active_dpd):.1%}", "Freq")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Importance"])

# -------------------------------------------------
# PDF & CHARTING (Annotated)
# -------------------------------------------------
def create_annotated_chart(df, is_pdf=False):
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
    
    # Chart Styling
    line_color = "#667eea"
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color=line_color, linewidth=2, label="DPD")
    
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        peak_idx = plot_df["DPD"].idxmax()
        peak_val = plot_df["DPD"].max()
        # Highlight Max Point
        ax.scatter(peak_idx, peak_val, color='#ef4444', s=100, zorder=5, edgecolors='black')
        ax.annotate(f'MAX: {int(peak_val)}', (peak_idx, peak_val), 
                   xytext=(0, 10), textcoords='offset points', 
                   ha='center', fontweight='bold', color='#ef4444')
    
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
# AUTH & MAIN
# -------------------------------------------------
def check_password():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if st.session_state.authenticated: return True
    apply_custom_styling()
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='login-box'><h2 style='text-align:center'>🛡️ Risk Login</h2>", unsafe_allow_html=True)
        u = st.text_input("User")
        p = st.text_input("Password", type="password")
        if st.button("Sign In", use_container_width=True):
            if "passwords" in st.secrets and u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state.authenticated = True
                st.rerun()
            elif u == "admin" and p == "admin": # Local Fallback
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Invalid")
    return False

if check_password():
    apply_custom_styling()
    with st.sidebar:
        st.title("🛡️ Controls")
        if st.button("Logout"): 
            st.session_state.authenticated = False
            st.rerun()
        uploaded_file = st.file_uploader("Upload Data", type=["xlsx"])

    if not uploaded_file:
        st.markdown("<div class='login-box' style='max-width:800px; text-align:center'><h1>Welcome</h1><p>Upload Excel to start.</p></div>", unsafe_allow_html=True)
    else:
        raw_data = pd.read_excel(uploaded_file)
        codes = raw_data.iloc[:, 0].unique()
        months = raw_data.columns[3:]
        
        # Buffer for Excel with Metrics
        output_excel = BytesIO()
        bulk_metrics = []
        
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            tabs = st.tabs([f"A/C {c}" for c in codes])
            
            bulk_pdf_buf = BytesIO()
            doc = SimpleDocTemplate(bulk_pdf_buf, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            for tab, code in zip(tabs, codes):
                row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                df, metrics_df = analyze_loan(row, months)
                
                # Save to Excel Sheets
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)
                
                # Collect for Summary Sheet
                m_row = metrics_df.set_index('Metric')['Value'].to_dict()
                m_row['Account'] = code
                bulk_metrics.append(m_row)
                
                with tab:
                    st.markdown(f"### Account Analysis: {code}")
                    # Metrics UI
                    m_cols = st.columns(3)
                    for i, (idx, m_r) in enumerate(metrics_df.iterrows()):
                        m_cols[i].markdown(f"<div class='metric-box'><b>{m_r['Metric']}</b><br>{m_r['Value']}</div>", unsafe_allow_html=True)
                    
                    # Chart with Highlighting
                    st.pyplot(create_annotated_chart(df))
                    
                    # Individual PDF
                    ind_buf = BytesIO()
                    ind_doc = SimpleDocTemplate(ind_buf, pagesize=letter)
                    ind_story = []
                    
                    # Build PDF with Annotation
                    ind_story.append(Paragraph(f"Report: {code}", styles['Heading1']))
                    ind_story.append(Image(create_annotated_chart(df, True), width=6*inch, height=2.5*inch))
                    ind_doc.build(ind_story)
                    
                    st.download_button(f"📥 Download PDF {code}", ind_buf.getvalue(), f"{code}.pdf")

            # Create Summary Metrics Sheet in Excel
            pd.DataFrame(bulk_metrics).to_excel(writer, sheet_name="Summary_Metrics", index=False)

        st.sidebar.markdown("---")
        st.sidebar.download_button("📂 Export All (Excel)", output_excel.getvalue(), "Portfolio_Report.xlsx")
