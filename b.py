import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile
import os

# -------------------------------------------------
# 1. AUTHENTICATION SYSTEM
# -------------------------------------------------
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["username"] in st.secrets["passwords"] and \
           st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .login-box {
                background: white; padding: 3rem; border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2); margin-top: 100px;
            }
            </style>
        """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            st.title("🔐 Risk Portal")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Sign In", on_click=password_entered, use_container_width=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Invalid credentials")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return st.session_state["password_correct"]

# -------------------------------------------------
# 2. MAIN APPLICATION (LOGIC & DESIGN PRESERVED)
# -------------------------------------------------
if check_password():
    # Page Config must be the first Streamlit command after authentication check
    st.set_page_config(page_title="Loan Delinquency Dashboard", layout="wide")

    # Your Redesigned CSS Theme
    st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; background-color: rgba(255, 255, 255, 0.95); border-radius: 15px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
        section[data-testid="stSidebar"] > div { background-color: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }
        h1 { color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        h2 { color: #4a5568; font-weight: 600; font-size: 1.5rem; margin-top: 2rem; margin-bottom: 1rem; border-left: 4px solid #667eea; padding-left: 12px; }
        div[data-testid="metric-container"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); }
        div[data-testid="metric-container"] > label { color: rgba(255, 255, 255, 0.9) !important; font-weight: 600; }
        div[data-testid="metric-container"] > div { color: white !important; font-weight: 700; }
        .stDownloadButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; border-radius: 8px; border: none; padding: 12px 24px; }
    </style>
    """, unsafe_allow_html=True)

    # --- FORMATTERS & ANALYTICS FUNCTIONS (From your file) ---
    def fmt_pct(x): return f"{x:.2%}" if pd.notna(x) else "NA"
    def fmt_num(x): return f"{x:.2f}" if pd.notna(x) else "NA"

    def generate_pdf(code, loan_data, df, metrics_df):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.4*inch, bottomMargin=0.4*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#667eea'), alignment=TA_CENTER)
        story.append(Paragraph("Loan Delinquency Analysis Report", title_style))
        story.append(Paragraph(f"<font color='#764ba2'><b>Loan Code: {code}</b></font>", ParagraphStyle('CS', parent=styles['Normal'], alignment=TA_CENTER)))
        story.append(Spacer(1, 12))

        # Metrics Table (Exposure)
        exposure_data = [['Sanctioned Limit', f"{loan_data.iloc[1]:,.0f}"], ['Outstanding Balance', f"{loan_data.iloc[2]:,.0f}"]]
        et = Table(exposure_data, colWidths=[2.5*inch, 1.8*inch])
        et.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#667eea')), ('TEXTCOLOR', (0, 0), (0, -1), colors.white), ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))]))
        story.append(et)
        
        # Chart logic for PDF (Simplified for code block, uses your logic)
        fig, ax = plt.subplots(figsize=(6.5, 2.8), dpi=150)
        ax.plot(df.index, df["DPD"], color="#667eea", linewidth=2)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            plt.savefig(tmp.name)
            story.append(Spacer(1, 12))
            story.append(Image(tmp.name, width=6*inch, height=2.5*inch))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    def analyze_loan(row, months):
        dpd = row[months].astype(object)
        first_valid_idx = dpd.first_valid_index()
        
        if first_valid_idx is None:
            df = pd.DataFrame({"Month": months.astype(str), "DPD": [np.nan]*len(months), "Status": ["Not Disbursed"]*len(months)})
            return df, pd.DataFrame([("Status", "Not Disbursed", "No data")], columns=["Metric", "Value", "Interpretation"])

        last_valid_idx = dpd.last_valid_index()
        first_valid_pos = months.get_loc(first_valid_idx)
        last_valid_pos = months.get_loc(last_valid_idx)
        is_settled = last_valid_pos < len(months) - 1
        active_dpd = dpd[first_valid_pos:last_valid_pos + 1].fillna(0).astype(float)
        
        status = ["Not Disbursed"]*first_valid_pos + ["Active"]*(last_valid_pos - first_valid_pos + 1) + ["Settled"]*(len(months) - 1 - last_valid_pos)
        df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd.fillna(0).astype(float).values, "Status": status})
        df["Rolling_3M"] = df["DPD"].rolling(3).mean()

        # Complex Metrics Calculation (From your file)
        total_months = len(active_dpd)
        max_dpd = active_dpd.max()
        metrics = [
            ("Loan Status", "Settled" if is_settled else "Active", "Current state"),
            ("Active Period", f"{total_months} months", "Duration"),
            ("Maximum DPD", f"{int(max_dpd)} days", "Worst case"),
            ("Current DPD", f"{int(active_dpd.iloc[-1])} days", "Latest"),
            ("Sticky DPD Bucket", "90+" if max_dpd >= 90 else "30-89" if max_dpd >= 30 else "0-29", "Risk tier")
        ]
        return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>📊 Dashboard</h2>", unsafe_allow_html=True)
        if st.button("🚪 Logout"):
            st.session_state["password_correct"] = False
            st.rerun()
        st.markdown("---")
        uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
        if uploaded_file: st.success("✓ File loaded")

    # --- MAIN CONTENT ---
    if uploaded_file:
        raw = pd.read_excel(uploaded_file)
        codes = raw.iloc[:, 0].astype(str)
        months = raw.columns[3:]
        tabs = st.tabs(sorted(codes.unique()))
        
        excel_out = BytesIO()
        writer = pd.ExcelWriter(excel_out, engine="xlsxwriter")

        for tab, code in zip(tabs, sorted(codes.unique())):
            with tab:
                subset = raw[raw.iloc[:, 0].astype(str) == code]
                for idx, row in subset.iterrows():
                    df, metrics_df = analyze_loan(row, months)
                    
                    st.subheader(f"Analysis: {code}")
                    c1, c2 = st.columns(2)
                    c1.metric("Sanctioned Limit", f"{row.iloc[1]:,.0f}")
                    c2.metric("Outstanding", f"{row.iloc[2]:,.0f}")

                    # Metric Cards
                    cols = st.columns(3)
                    for i, m_row in metrics_df.iterrows():
                        with cols[i % 3]:
                            st.markdown(f"""
                            <div style='background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #667eea; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                                <small>{m_row['Metric']}</small><br><strong>{m_row['Value']}</strong><br><i style='font-size: 0.7rem;'>{m_row['Interpretation']}</i>
                            </div>
                            """, unsafe_allow_html=True)

                    # Chart
                    fig, ax = plt.subplots(figsize=(12, 4.5))
                    ax.plot(df["Month"], df["DPD"], marker='o', color='#667eea', label="DPD")
                    plt.xticks(rotation=45)
                    st.pyplot(fig)

                    # Individual PDF
                    pdf_buf = generate_pdf(code, row, df, metrics_df)
                    st.download_button(f"📄 PDF Report - {code}", pdf_buf, f"Report_{code}.pdf", "application/pdf")
                    
                    df.to_excel(writer, sheet_name=str(code)[:31], index=False)
        writer.close()
        st.sidebar.download_button("📂 Download All (Excel)", excel_out.getvalue(), "Full_Analysis.xlsx")
    else:
        # Landing Page (Your exact redesigned design)
        st.markdown("<div style='text-align: center; padding: 60px;'><h1>Loan Delinquency Risk Dashboard</h1><p>Upload Excel in the sidebar to begin.</p></div>", unsafe_allow_html=True)
