import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import tempfile
import os

# -------------------------------------------------
# 1. AUTHENTICATION SYSTEM
# -------------------------------------------------
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets["passwords"] and \
           st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Display Login UI
        st.markdown("""
            <style>
            .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .login-box {
                background: white; padding: 2rem; border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }
            </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            st.title("🔐 Risk Portal Login")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Sign In", on_click=password_entered, use_container_width=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Invalid username or password")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    else:
        return st.session_state["password_correct"]

# -------------------------------------------------
# 2. APP CONFIG & STYLING
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Loan Delinquency Dashboard", layout="wide")

    st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .block-container { padding-top: 2rem; background-color: rgba(255, 255, 255, 0.95); border-radius: 15px; margin-top: 20px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); }
        h1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; }
        h2 { border-left: 4px solid #667eea; padding-left: 12px; color: #4a5568; }
        div[data-testid="metric-container"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 20px; color: white !important; }
        div[data-testid="metric-container"] label, div[data-testid="metric-container"] div { color: white !important; }
        .stDownloadButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; border: none; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 3. HELPER FUNCTIONS
    # -------------------------------------------------
    def fmt_pct(x): return f"{x:.2%}" if pd.notna(x) else "NA"
    def fmt_num(x): return f"{x:.2f}" if pd.notna(x) else "NA"

    def generate_pdf(code, loan_data, df, metrics_df):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#667eea'), alignment=TA_CENTER)
        story.append(Paragraph("Loan Delinquency Analysis Report", title_style))
        story.append(Paragraph(f"Loan Code: {code}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Metrics Table
        data = [["Metric", "Value"]] + metrics_df[['Metric', 'Value']].values.tolist()
        t = Table(data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        story.append(t)
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    def analyze_loan(row, months):
        dpd = row[months].astype(object)
        first_valid_idx = dpd.first_valid_index()
        
        if first_valid_idx is None:
            df = pd.DataFrame({"Month": months.astype(str), "DPD": [np.nan]*len(months), "Status": ["Not Disbursed"]*len(months)})
            return df, pd.DataFrame(columns=["Metric", "Value", "Interpretation"])

        last_valid_idx = dpd.last_valid_index()
        first_valid_pos = months.get_loc(first_valid_idx)
        last_valid_pos = months.get_loc(last_valid_idx)
        
        is_settled = last_valid_pos < len(months) - 1
        active_dpd = dpd[first_valid_pos:last_valid_pos + 1].fillna(0).astype(float)
        
        status = ["Not Disbursed"]*first_valid_pos + ["Active"]*(last_valid_pos - first_valid_pos + 1) + ["Settled"]*(len(months) - 1 - last_valid_pos)
        
        df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd.fillna(0).astype(float).values, "Status": status})
        df["Rolling_3M"] = df["DPD"].rolling(3).mean()

        # Simple Metric Logic
        max_dpd = active_dpd.max()
        metrics = [
            ("Loan Status", "Settled" if is_settled else "Active", ""),
            ("Maximum DPD", f"{int(max_dpd)} days", "Worst historical delinquency"),
            ("Current DPD", f"{int(active_dpd.iloc[-1])} days", "Latest status"),
            ("Active Months", len(active_dpd), "Duration of loan")
        ]
        return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

    # -------------------------------------------------
    # 4. SIDEBAR & FILE UPLOAD
    # -------------------------------------------------
    with st.sidebar:
        st.title("📊 Control Panel")
        if st.button("Log Out"):
            st.session_state["password_correct"] = False
            st.rerun()
        
        st.markdown("---")
        uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
        if uploaded_file:
            st.success("File Ready")

    # -------------------------------------------------
    # 5. MAIN DASHBOARD
    # -------------------------------------------------
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

                    st.header(f"Analysis: {code}")
                    col1, col2 = st.columns(2)
                    col1.metric("Sanctioned", f"{row.iloc[1]:,.0f}")
                    col2.metric("Outstanding", f"{row.iloc[2]:,.0f}")

                    # Chart
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(df["Month"], df["DPD"], marker='o', color='#667eea', linewidth=2)
                    ax.fill_between(df["Month"], df["DPD"], alpha=0.2, color='#764ba2')
                    plt.xticks(rotation=45)
                    st.pyplot(fig)

                    # Download
                    pdf_buf = generate_pdf(code, row, df, metrics_df)
                    st.download_button(f"📥 PDF Report {code}", pdf_buf, f"Report_{code}.pdf", "application/pdf")
                    
                    # Store in Excel
                    df.to_excel(writer, sheet_name=str(code)[:31], index=False)
        
        writer.close()
        st.sidebar.download_button("📂 Download All Analysis (Excel)", excel_out.getvalue(), "Full_Analysis.xlsx")

    else:
        st.markdown("<div style='text-align:center; padding:100px;'><h1>Welcome to the Risk Dashboard</h1><p>Please upload an Excel file in the sidebar to begin.</p></div>", unsafe_allow_html=True)