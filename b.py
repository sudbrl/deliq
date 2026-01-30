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
from reportlab.lib.enums import TA_CENTER
import tempfile
import os

# -------------------------------------------------
# 1. AUTHENTICATION & SESSION MANAGEMENT
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

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
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
            st.title("🛡️ Risk Portal Login")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.button("Sign In", on_click=password_entered, use_container_width=True)
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("⚠️ Invalid username or password")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

# -------------------------------------------------
# 2. UTILITIES & PDF LOGIC
# -------------------------------------------------
def fmt_pct(x): return f"{x:.2%}" if pd.notna(x) else "NA"
def fmt_num(x): return f"{x:.2f}" if pd.notna(x) else "NA"

def get_metric_explanations():
    return [
        ["Metric", "Definition", "Importance"],
        ["Loan Status", "Current state of the loan (Active or Settled).", "Determines if the account requires monitoring."],
        ["Delinquency Density", "Percentage of active months where DPD > 0.", "Indicates the frequency of repayment failure."],
        ["Maximum DPD", "The highest number of days past due recorded.", "Critical for risk tiering and provisioning."],
        ["Sticky DPD Bucket", "Categorizes the loan based on peak delinquency.", "Helps identify high-risk assets (e.g., 90+ DPD)."],
        ["Delinquency Episodes", "Number of times a loan entered a delinquent state.", "Shows if defaults are isolated or recurring."]
    ]

def create_pdf_chart(df):
    """Generates an optimized chart for the PDF with months and peak highlights."""
    # Filter to show only relevant months (Active/Settled)
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    
    fig, ax = plt.subplots(figsize=(6.5, 3), dpi=150)
    ax.set_facecolor('#f8f9fa')
    
    # Plotting DPD and Moving Average
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#667eea", linewidth=2, label="DPD", markersize=4)
    ax.plot(plot_df.index, plot_df["Rolling_3M"], linestyle="--", color="#764ba2", alpha=0.7, label="3M Avg")
    
    # Highlight Peak DPD
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        peak_idx = plot_df["DPD"].idxmax()
        peak_val = plot_df["DPD"].max()
        ax.scatter(peak_idx, peak_val, color='red', s=50, zorder=5)
        ax.annotate(f'Peak: {int(peak_val)}', xy=(peak_idx, peak_val), xytext=(5, 5),
                    textcoords='offset points', fontsize=8, fontweight='bold', color='#dc2626')

    # Formatting Axis
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45, fontsize=7)
    ax.set_ylabel("Days Past Due", fontsize=8)
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.legend(prop={'size': 7}, loc='upper left')
    
    plt.tight_layout()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp.name, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return tmp.name

def generate_report_content(code, loan_data, df, metrics_df, story, styles):
    """Appends report pages to the story list for PDF generation."""
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#667eea'), alignment=TA_CENTER)
    story.append(Paragraph(f"Loan Delinquency Report: {code}", title_style))
    story.append(Spacer(1, 12))

    # Exposure Table
    exposure_data = [['Sanctioned Limit', f"{loan_data.iloc[1]:,.0f}"], ['Outstanding Balance', f"{loan_data.iloc[2]:,.0f}"]]
    et = Table(exposure_data, colWidths=[2.5*inch, 1.8*inch])
    et.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#667eea')), ('TEXTCOLOR', (0, 0), (0, -1), colors.white), ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0'))]))
    story.append(Paragraph("Loan Exposure", styles['Heading2']))
    story.append(et)
    story.append(Spacer(1, 12))

    # Metrics Table
    m_data = [[m['Metric'], m['Value']] for _, m in metrics_df.iterrows()]
    mt = Table(m_data, colWidths=[2.2*inch, 2.2*inch])
    mt.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 8), ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f7fafc'))]))
    story.append(Paragraph("Key Metrics", styles['Heading2']))
    story.append(mt)
    story.append(Spacer(1, 15))

    # Chart
    chart_path = create_pdf_chart(df)
    story.append(Image(chart_path, width=5.5*inch, height=2.3*inch))
    return story

# -------------------------------------------------
# 3. CORE ANALYTICS LOGIC
# -------------------------------------------------
def analyze_loan(row, months):
    dpd = row[months].astype(object)
    first_valid_idx = dpd.first_valid_index()
    if first_valid_idx is None:
        df = pd.DataFrame({"Month": months.astype(str), "DPD": [0.0]*len(months), "Status": ["Not Disbursed"]*len(months)})
        return df, pd.DataFrame([("Status", "Not Disbursed", "N/A")], columns=["Metric", "Value", "Interpretation"])

    last_valid_idx = dpd.last_valid_index()
    first_valid_pos = months.get_loc(first_valid_idx)
    last_valid_pos = months.get_loc(last_valid_idx)
    is_settled = last_valid_pos < len(months) - 1
    
    active_dpd = dpd.iloc[first_valid_pos:last_valid_pos+1].fillna(0).astype(float)
    status = ["Not Disbursed"]*first_valid_pos + ["Active"]*(last_valid_pos - first_valid_pos + 1) + ["Settled"]*(len(months) - 1 - last_valid_pos)
    
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd.fillna(0).astype(float).values, "Status": status})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean()

    total_months = len(active_dpd)
    delinquent_months = (active_dpd > 0).sum()
    max_dpd = active_dpd.max()
    
    metrics = [
        ("Loan Status", f"Settled" if is_settled else "Active", "State"),
        ("Active Period", f"{total_months} months", "Duration"),
        ("Delinquency Density", fmt_pct(delinquent_months/total_months), "Frequency"),
        ("Maximum DPD", f"{int(max_dpd)} days", "Peak"),
        ("Sticky DPD Bucket", "90+" if max_dpd >= 90 else "30-89" if max_dpd >= 30 else "0-29", "Risk"),
        ("Current DPD", f"{int(active_dpd.iloc[-1])} days", "Latest")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

# -------------------------------------------------
# 4. MAIN APPLICATION
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Loan Risk Dashboard", layout="wide")

    # Custom Professional CSS
    st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .block-container { background-color: rgba(255, 255, 255, 0.98); border-radius: 15px; padding: 2rem; margin-top: 1rem; }
        h1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }
        .metric-card { background: white; padding: 1.2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #667eea; }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<h2 style='color: white;'>Settings</h2>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["password_correct"] = False
            st.rerun()
        uploaded_file = st.file_uploader("Upload Delinquency Data", type=["xlsx"])

    if uploaded_file:
        raw = pd.read_excel(uploaded_file)
        codes = raw.iloc[:, 0].astype(str).unique()
        months = raw.columns[3:]
        
        # Bulk PDF Button in Sidebar
        if st.sidebar.button("📥 Download All Reports (PDF)"):
            bulk_buffer = BytesIO()
            doc = SimpleDocTemplate(bulk_buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            for code in codes:
                subset = raw[raw.iloc[:, 0].astype(str) == code].iloc[0]
                df, m_df = analyze_loan(subset, months)
                generate_report_content(code, subset, df, m_df, story, styles)
                story.append(PageBreak())
            
            # Add Glossary Page at the end
            story.append(Paragraph("Metric Explanation Glossary", styles['Heading1']))
            gt = Table(get_metric_explanations(), colWidths=[1.5*inch, 2.5*inch, 2.0*inch])
            gt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#667eea')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9)]))
            story.append(gt)
            
            doc.build(story)
            st.sidebar.download_button("Click to Download Bulk PDF", bulk_buffer.getvalue(), "Consolidated_Risk_Report.pdf")

        tabs = st.tabs(list(codes))
        for tab, code in zip(tabs, codes):
            with tab:
                row = raw[raw.iloc[:, 0].astype(str) == code].iloc[0]
                df, metrics_df = analyze_loan(row, months)
                
                st.title(f"Analysis: {code}")
                c1, c2 = st.columns(2)
                c1.metric("Sanctioned Limit", f"{row.iloc[1]:,.0f}")
                c2.metric("Current Exposure", f"{row.iloc[2]:,.0f}")

                # Display Metrics
                m_cols = st.columns(3)
                for i, (_, m) in enumerate(metrics_df.iterrows()):
                    with m_cols[i % 3]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div style="color: #718096; font-size: 0.8rem; font-weight: 600;">{m['Metric']}</div>
                            <div style="color: #2d3748; font-size: 1.5rem; font-weight: 700;">{m['Value']}</div>
                            <div style="color: #a0aec0; font-size: 0.75rem;">{m['Interpretation']}</div>
                        </div><br>
                        """, unsafe_allow_html=True)

                # Screen Chart
                fig, ax = plt.subplots(figsize=(12, 4))
                plot_data = df[df["Status"] != "Not Disbursed"]
                ax.plot(plot_data["Month"], plot_data["DPD"], marker="o", color="#667eea", label="DPD")
                ax.set_xticklabels(plot_data["Month"], rotation=45)
                st.pyplot(fig)

                # Individual PDF Download
                pdf_buf = BytesIO()
                doc = SimpleDocTemplate(pdf_buf, pagesize=letter)
                single_story = generate_report_content(code, row, df, metrics_df, [], getSampleStyleSheet())
                
                # Add Glossary to individual report too
                single_story.append(PageBreak())
                single_story.append(Paragraph("Metric Explanation Glossary", getSampleStyleSheet()['Heading1']))
                gt = Table(get_metric_explanations(), colWidths=[1.5*inch, 2.5*inch, 2.0*inch])
                gt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#667eea')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
                single_story.append(gt)
                
                doc.build(single_story)
                st.download_button(f"📄 Download PDF Report - {code}", pdf_buf.getvalue(), f"Risk_Report_{code}.pdf")

    else:
        st.markdown("<div style='text-align:center; padding:5rem;'><h1>Welcome to Risk Portal</h1><p>Upload an Excel file to begin delinquency analysis.</p></div>", unsafe_allow_html=True)
