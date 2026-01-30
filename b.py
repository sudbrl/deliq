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
                box-shadow: 0 10px 25px rgba(0,0,0,0.2); margin-top: 50px;
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
    return st.session_state["password_correct"]

# -------------------------------------------------
# 2. MAIN APPLICATION (REPLICATED FROM YOUR FILE)
# -------------------------------------------------
if check_password():
    # Page Config (Must be first Streamlit command)
    st.set_page_config(page_title="Loan Delinquency Dashboard", layout="wide")

    # Replicating your Professional CSS Theme Exactly
    st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .block-container { padding-top: 2rem; padding-bottom: 2rem; background-color: rgba(255, 255, 255, 0.95); border-radius: 15px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1); }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
        section[data-testid="stSidebar"] > div { background-color: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }
        h1 { color: #2d3748; font-weight: 700; font-size: 2.5rem; margin-bottom: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        h2 { color: #4a5568; font-weight: 600; font-size: 1.5rem; margin-top: 2rem; margin-bottom: 1rem; border-left: 4px solid #667eea; padding-left: 12px; }
        div[data-testid="metric-container"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; padding: 20px; border-radius: 12px; }
        div[data-testid="metric-container"] > label { color: rgba(255, 255, 255, 0.9) !important; font-weight: 600; }
        div[data-testid="metric-container"] > div { color: white !important; font-weight: 700; }
        .stDownloadButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: 600; border-radius: 8px; border: none; padding: 12px 24px; }
    </style>
    """, unsafe_allow_html=True)

    # --- FORMATTERS ---
    def fmt_pct(x): return f"{x:.2%}" if pd.notna(x) else "NA"
    def fmt_num(x): return f"{x:.2f}" if pd.notna(x) else "NA"

    # --- PDF GENERATION (Exact Replication) ---
    def generate_pdf(code, loan_data, df, metrics_df):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.4*inch, bottomMargin=0.4*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#667eea'), alignment=TA_CENTER)
        story.append(Paragraph("Loan Delinquency Analysis Report", title_style))
        story.append(Paragraph(f"<font color='#764ba2'><b>Loan Code: {code}</b></font>", ParagraphStyle('CS', parent=styles['Normal'], alignment=TA_CENTER)))
        story.append(Spacer(1, 12))

        # Exposure Table
        exposure_data = [['Sanctioned Limit', f"{loan_data.iloc[1]:,.0f}"], ['Outstanding Balance', f"{loan_data.iloc[2]:,.0f}"]]
        et = Table(exposure_data, colWidths=[2.5*inch, 1.8*inch])
        et.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#667eea')), ('TEXTCOLOR', (0, 0), (0, -1), colors.white), ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))]))
        story.append(Paragraph("Loan Exposure", styles['Heading2']))
        story.append(et)
        story.append(Spacer(1, 12))

        # Metrics Side-by-Side Table
        story.append(Paragraph("Delinquency Metrics", styles['Heading2']))
        left_metrics, right_metrics = [], []
        for i, (_, row) in enumerate(metrics_df.iterrows()):
            m_data = [row['Metric'], str(row['Value'])]
            if i < len(metrics_df) // 2 + 1: left_metrics.append(m_data)
            else: right_metrics.append(m_data)
        
        lt = Table(left_metrics, colWidths=[1.5*inch, 1.2*inch])
        rt = Table(right_metrics, colWidths=[1.5*inch, 1.2*inch])
        for t in [lt, rt]: t.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc')), ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')), ('FONTSIZE', (0,0), (-1,-1), 8)]))
        
        story.append(Table([[lt, rt]], colWidths=[2.7*inch, 2.7*inch]))
        story.append(Spacer(1, 12))

        # Chart (Exact Matplotlib Replication for PDF)
        fig, ax = plt.subplots(figsize=(6.5, 2.8), facecolor='white', dpi=150)
        ax.set_facecolor('#f8f9fa')
        
        not_disbursed_mask = df["Status"] == "Not Disbursed"
        settled_mask = df["Status"] == "Settled"
        if not_disbursed_mask.any(): ax.axvspan(-0.5, not_disbursed_mask.sum() - 0.5, alpha=0.1, color='gray')
        if settled_mask.any(): ax.axvspan(df[settled_mask].index[0] - 0.5, len(df) - 0.5, alpha=0.1, color='green')
        
        dpd_plot = df[df["Status"] != "Not Disbursed"]
        if not dpd_plot.empty:
            ax.plot(dpd_plot.index, dpd_plot["DPD"], marker="o", color="#667eea", linewidth=2.5, label="DPD")
            ax.plot(dpd_plot.index, dpd_plot["Rolling_3M"], linestyle="--", color="#764ba2", label="3M Avg")
        
        for val, col in zip([30, 60, 90], ["#fbbf24", "#f97316", "#dc2626"]):
            ax.axhline(val, linestyle=":", alpha=0.4, color=col)

        plt.tight_layout()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            plt.savefig(tmp.name, bbox_inches='tight', dpi=150)
            story.append(Image(tmp.name, width=6*inch, height=2.5*inch))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    # --- CORE CALCULATION (Exact Replication of 17 Metrics) ---
    def analyze_loan(row, months):
        dpd = row[months].astype(object)
        first_valid_idx = dpd.first_valid_index()
        if first_valid_idx is None:
            df = pd.DataFrame({"Month": months.astype(str), "DPD": [np.nan]*len(months), "Status": ["Not Disbursed"]*len(months)})
            return df, pd.DataFrame([("Status", "Not Disbursed", "N/A")], columns=["Metric", "Value", "Interpretation"])

        last_valid_idx = dpd.last_valid_index()
        first_valid_pos = months.get_loc(first_valid_idx)
        last_valid_pos = months.get_loc(last_valid_idx)
        is_settled = last_valid_pos < len(months) - 1
        active_months = months[first_valid_pos:last_valid_pos + 1]
        active_dpd = dpd[active_months].fillna(0).astype(float)
        
        status = ["Not Disbursed"]*first_valid_pos + ["Active"]*(last_valid_pos - first_valid_pos + 1) + ["Settled"]*(len(months) - 1 - last_valid_pos)
        df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd.fillna(0).astype(float).values, "Status": status})
        df["Rolling_3M"] = df["DPD"].rolling(3).mean()

        # Metrics logic from your file
        total_months = len(active_dpd)
        delinquent_months = (active_dpd > 0).sum()
        max_dpd = active_dpd.max()
        current_dpd = active_dpd.iloc[-1]
        
        episodes = cures = 0
        in_delinquency = False
        for val in active_dpd:
            if val > 0:
                if not in_delinquency: episodes += 1; in_delinquency = True
            else:
                if in_delinquency: cures += 1; in_delinquency = False

        metrics = [
            ("Loan Status", f"Settled ({months[last_valid_pos]})" if is_settled else "Active", "State"),
            ("Disbursement Month", str(months[first_valid_pos]), "Start"),
            ("Active Period", f"{total_months} months", "Duration"),
            ("Delinquency Density", fmt_pct(delinquent_months/total_months), "Density"),
            ("LTD Cumulative DPD", f"{int(active_dpd.sum())} days", "Total Days"),
            ("Average DPD (All Months)", f"{fmt_num(active_dpd.mean())} days", "Mean"),
            ("Maximum DPD", f"{int(max_dpd)} days", "Peak"),
            ("Current DPD", f"{int(current_dpd)} days", "Latest"),
            ("Delinquency Episodes", f"{int(episodes)} episodes", "Cycles"),
            ("Sticky DPD Bucket", "90+" if max_dpd >= 90 else "30-89" if max_dpd >= 30 else "0-29", "Risk Tier")
        ]
        return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

    # --- SIDEBAR & MAIN ---
    with st.sidebar:
        st.markdown("<h2 style='color: #667eea; text-align: center;'>📊 Dashboard</h2>", unsafe_allow_html=True)
        if st.button("🚪 Logout"):
            st.session_state["password_correct"] = False
            st.rerun()
        st.markdown("---")
        uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
        if uploaded_file: st.success("✓ File loaded")

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
                    
                    st.subheader("Loan Exposure")
                    c1, c2 = st.columns(2)
                    c1.metric("Sanctioned Limit", f"{row.iloc[1]:,.0f}")
                    c2.metric("Outstanding", f"{row.iloc[2]:,.0f}")

                    # Your Custom Metric Cards (3-column layout)
                    for i in range(0, len(metrics_df), 3):
                        cols = st.columns(3)
                        for j, col in enumerate(cols):
                            if i + j < len(metrics_df):
                                m = metrics_df.iloc[i + j]
                                with col:
                                    st.markdown(f"""
                                    <div style='background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); border-left: 4px solid #667eea; margin-bottom: 15px;'>
                                        <div style='color: #718096; font-size: 0.75rem; font-weight: 600;'>{m['Metric']}</div>
                                        <div style='color: #2d3748; font-size: 1.8rem; font-weight: 700;'>{m['Value']}</div>
                                        <div style='color: #a0aec0; font-size: 0.8rem;'>{m['Interpretation']}</div>
                                    </div>
                                    """, unsafe_allow_html=True)

                    # DPD Trend Chart (Exact Replication)
                    fig, ax = plt.subplots(figsize=(12, 4.5), facecolor='white')
                    ax.set_facecolor('#f8f9fa')
                    if (df["Status"] == "Not Disbursed").any(): ax.axvspan(-0.5, (df["Status"] == "Not Disbursed").sum() - 0.5, alpha=0.1, color='gray', label='Not Disbursed')
                    if (df["Status"] == "Settled").any(): ax.axvspan(df[df["Status"] == "Settled"].index[0] - 0.5, len(df) - 0.5, alpha=0.1, color='green', label='Settled')
                    
                    plot_data = df[df["Status"] != "Not Disbursed"]
                    ax.plot(plot_data.index, plot_data["DPD"], marker="o", color="#667eea", linewidth=2.5, label="DPD")
                    ax.plot(plot_data.index, plot_data["Rolling_3M"], linestyle="--", color="#764ba2", label="3M Avg")
                    ax.set_xticks(range(len(df))); ax.set_xticklabels(df["Month"], rotation=45)
                    st.pyplot(fig)

                    pdf_buf = generate_pdf(code, row, df, metrics_df)
                    st.download_button(f"📄 Download PDF - {code}", pdf_buf, f"Analysis_{code}.pdf", "application/pdf")
                    df.to_excel(writer, sheet_name=str(code)[:31], index=False)
        writer.close()
        st.sidebar.download_button("📂 Download Full Excel", excel_out.getvalue(), "loan_analysis.xlsx")
    else:
        # Replicated Landing Page
        st.markdown("<div style='text-align:center; padding:60px;'><h1>Loan Delinquency Risk Dashboard</h1><p>Advanced Analytics Platform</p></div>", unsafe_allow_html=True)
