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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile
import os

# -------------------------------------------------
# 1. AUTHENTICATION & SESSION MANAGEMENT
# -------------------------------------------------
def check_password():
    """Handles professional login and session clearing."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("""
        <style>
        .stApp { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); }
        .login-box {
            background: white; padding: 3rem; border-radius: 20px;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); margin-top: 50px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:#1e3a8a;'>Risk Portal Access</h2>", unsafe_allow_html=True)
        u = st.text_input("Username", key="login_user")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("Secure Sign In", use_container_width=True):
            if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Invalid username or password")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

# -------------------------------------------------
# 2. PDF UTILITIES & ENHANCED GLOSSARY
# -------------------------------------------------
def get_pdf_glossary():
    """Returns a comprehensive, easy-to-read metric explanation list."""
    return [
        ["Metric", "Description", "Formula / Logic", "Importance"],
        ["Loan Status", "Current state of the account.", "Active vs Settled", "Identifies ongoing exposure."],
        ["Active Period", "Duration the loan has been live.", "Months from first DPD", "Used for aging analysis."],
        ["Delinquency Density", "Frequency of payment misses.", "Delinquent Months / Total", "Shows chronic instability."],
        ["LTD Cumulative DPD", "Sum of all days past due.", "Sum of all DPD values", "Quantifies total volume."],
        ["Maximum DPD", "Highest DPD point reached.", "Max(DPD)", "Critical for risk tiering."],
        ["Current DPD", "Most recent reported status.", "Latest DPD entry", "Urgency indicator."],
        ["Episodes", "Count of delinquency cycles.", "Active -> Cure cycles", "Shows recurring default."],
        ["Sticky Bucket", "Risk tier based on peak DPD.", "0-29 / 30-89 / 90+", "Standard Basel III buckets."]
    ]

def add_glossary_to_pdf(story, styles):
    """Adds a dedicated, legible page for metric explanations."""
    story.append(PageBreak())
    title_style = ParagraphStyle('GlossaryTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=20, textColor=colors.HexColor('#1e3a8a'))
    story.append(Paragraph("Risk Metric Glossary & Definitions", title_style))
    
    data = get_pdf_glossary()
    # Wide columns to ensure it is not compact
    table = Table(data, colWidths=[1.1*inch, 1.8*inch, 1.6*inch, 2.0*inch])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white])
    ]))
    story.append(table)

def create_pdf_chart(df):
    """Generates a PDF chart with accurate months and peak highlights."""
    # Filter to relevant lifecycle (Exclude pre-disbursement)
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    
    fig, ax = plt.subplots(figsize=(6.5, 3), dpi=150)
    ax.set_facecolor('#f8f9fa')
    
    # Lines
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#667eea", linewidth=2, label="DPD", markersize=4)
    ax.plot(plot_df.index, plot_df["Rolling_3M"], linestyle="--", color="#764ba2", alpha=0.7, label="3M Avg")
    
    # Peak Highlight
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        peak_idx = plot_df["DPD"].idxmax()
        peak_val = plot_df["DPD"].max()
        ax.scatter(peak_idx, peak_val, color='red', s=40, zorder=5)
        ax.annotate(f'Peak: {int(peak_val)}', xy=(peak_idx, peak_val), xytext=(5, 5),
                    textcoords='offset points', fontsize=8, fontweight='bold', color='#dc2626')

    # Formatting X-Axis accurately with Months
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45, fontsize=7)
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.legend(prop={'size': 7}, loc='upper left')
    
    plt.tight_layout()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp.name, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return tmp.name

# -------------------------------------------------
# 3. CORE ANALYTICS
# -------------------------------------------------
def analyze_loan(row, months):
    dpd = row[months].astype(object)
    first_valid_idx = dpd.first_valid_index()
    if first_valid_idx is None:
        df = pd.DataFrame({"Month": months.astype(str), "DPD": [0.0]*len(months), "Status": ["Not Disbursed"]*len(months)})
        return df, pd.DataFrame([("Status", "Not Disbursed", "N/A")], columns=["Metric", "Value", "Interpretation"])

    last_valid_idx = dpd.last_valid_index()
    first_v_pos = months.get_loc(first_valid_idx)
    last_v_pos = months.get_loc(last_valid_idx)
    
    active_dpd = dpd.iloc[first_v_pos:last_v_pos+1].fillna(0).astype(float)
    status = ["Not Disbursed"]*first_v_pos + ["Active"]*(last_v_pos - first_v_pos + 1) + ["Settled"]*(len(months) - 1 - last_v_pos)
    
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd.fillna(0).astype(float).values, "Status": status})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean()

    total_m = len(active_dpd)
    max_d = active_dpd.max()
    
    metrics = [
        ("Loan Status", "Settled" if last_v_pos < len(months)-1 else "Active", "State"),
        ("Active Period", f"{total_m} months", "Duration"),
        ("Delinquency Density", f"{(active_dpd > 0).sum()/total_m:.1%}", "Density"),
        ("LTD Cumulative DPD", f"{int(active_dpd.sum())} days", "Total"),
        ("Maximum DPD", f"{int(max_d)} days", "Peak"),
        ("Sticky Bucket", "90+" if max_d >= 90 else "30-89" if max_d >= 30 else "0-29", "Risk Tier")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

# -------------------------------------------------
# 4. MAIN APP LOGIC
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Risk Intel Portal", layout="wide")

    # Styling
    st.markdown("""
    <style>
        .stApp { background-color: #f8fafc; }
        .block-container { background-color: white; border-radius: 15px; padding: 2rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        .hero-section { text-align: center; padding: 4rem 2rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 20px; margin-bottom: 2rem; }
        .metric-card { background: white; padding: 1.5rem; border-radius: 12px; border-left: 5px solid #3b82f6; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("🛡️ Risk Portal")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        uploaded_file = st.file_uploader("Upload Excel Data", type=["xlsx"])

    if not uploaded_file:
        # REDESIGNED LANDING PAGE
        st.markdown("""
            <div class="hero-section">
                <h1 style="color: #1e3a8a; font-size: 3rem; font-weight: 800;">Risk Intelligence Dashboard</h1>
                <p style="color: #475569; font-size: 1.25rem; max-width: 800px; margin: 1.5rem auto;">
                    Professional-grade loan delinquency tracking, automated DPD trend analysis, and PDF risk reporting.
                </p>
                <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 3rem;">
                    <div style="background: white; padding: 2rem; border-radius: 15px; width: 250px;">
                        <h4 style="color: #3b82f6;">📊 Analytics</h4>
                        <p style="font-size: 0.9rem; color: #64748b;">Automated DPD density & cycle calculations.</p>
                    </div>
                    <div style="background: white; padding: 2rem; border-radius: 15px; width: 250px;">
                        <h4 style="color: #3b82f6;">📥 Reporting</h4>
                        <p style="font-size: 0.9rem; color: #64748b;">Single and bulk PDF report generation.</p>
                    </div>
                    <div style="background: white; padding: 2rem; border-radius: 15px; width: 250px;">
                        <h4 style="color: #3b82f6;">🔍 Auditing</h4>
                        <p style="font-size: 0.9rem; color: #64748b;">Peak highlight tracking and risk tiering.</p>
                    </div>
                </div>
                <p style="margin-top: 4rem; color: #94a3b8; font-style: italic;">Please upload an Excel file in the sidebar to begin.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        raw = pd.read_excel(uploaded_file)
        codes = raw.iloc[:, 0].astype(str).unique()
        months = raw.columns[3:]

        # Bulk Download Feature
        if st.sidebar.button("📦 Generate Bulk PDF (All Loans)"):
            bulk_buf = BytesIO()
            doc = SimpleDocTemplate(bulk_buf, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            for code in codes:
                subset = raw[raw.iloc[:, 0].astype(str) == code].iloc[0]
                df, m_df = analyze_loan(subset, months)
                
                # Single Report Content
                story.append(Paragraph(f"Loan Risk Report: {code}", styles['Heading1']))
                story.append(Spacer(1, 12))
                
                # Metrics Table
                data = [[m['Metric'], m['Value']] for _, m in m_df.iterrows()]
                t = Table(data, colWidths=[2.5*inch, 2.5*inch])
                t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                story.append(t)
                story.append(Spacer(1, 15))
                
                # Chart
                c_path = create_pdf_chart(df)
                story.append(Image(c_path, width=5.5*inch, height=2.3*inch))
                story.append(PageBreak())

            add_glossary_to_pdf(story, styles)
            doc.build(story)
            st.sidebar.download_button("💾 Download All Reports", bulk_buf.getvalue(), "Consolidated_Risk_Report.pdf")

        # Tabs for Individual Loans
        tabs = st.tabs(list(codes))
        for tab, code in zip(tabs, codes):
            with tab:
                row = raw[raw.iloc[:, 0].astype(str) == code].iloc[0]
                df, m_df = analyze_loan(row, months)
                
                st.header(f"Account: {code}")
                
                # Metrics Grid
                m_cols = st.columns(3)
                for i, (_, m) in enumerate(m_df.iterrows()):
                    with m_cols[i % 3]:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div style="color: #64748b; font-size: 0.8rem; font-weight: 600;">{m['Metric']}</div>
                            <div style="color: #1e3a8a; font-size: 1.5rem; font-weight: 700;">{m['Value']}</div>
                            <div style="color: #94a3b8; font-size: 0.75rem;">{m['Interpretation']}</div>
                        </div><br>
                        """, unsafe_allow_html=True)

                # Individual Chart
                fig, ax = plt.subplots(figsize=(12, 4))
                plot_data = df[df["Status"] != "Not Disbursed"]
                ax.plot(plot_data["Month"], plot_data["DPD"], marker="o", color="#3b82f6")
                ax.set_facecolor('#f8fafc')
                plt.xticks(rotation=45)
                st.pyplot(fig)

                # Individual PDF
                pdf_buf = BytesIO()
                doc = SimpleDocTemplate(pdf_buf, pagesize=letter)
                story = []
                styles = getSampleStyleSheet()
                
                story.append(Paragraph(f"Loan Risk Report: {code}", styles['Heading1']))
                story.append(Spacer(1, 20))
                
                # Metrics
                data = [[m['Metric'], m['Value']] for _, m in m_df.iterrows()]
                t = Table(data, colWidths=[2.5*inch, 2.5*inch])
                t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTSIZE', (0,0), (-1,-1), 9)]))
                story.append(t)
                story.append(Spacer(1, 20))
                
                # Chart
                c_path = create_pdf_chart(df)
                story.append(Image(c_path, width=5.5*inch, height=2.3*inch))
                
                add_glossary_to_pdf(story, styles)
                doc.build(story)
                st.download_button(f"📄 Download Report {code}", pdf_buf.getvalue(), f"Report_{code}.pdf")
