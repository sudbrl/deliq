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

# -------------------------------------------------
# 1. AUTHENTICATION & SESSION
# -------------------------------------------------
def check_password():
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
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Secure Login", use_container_width=True):
            if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Invalid credentials")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

# -------------------------------------------------
# 2. ANALYTICS ENGINE
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
# 3. PDF & CHART GENERATION
# -------------------------------------------------
def get_pdf_glossary_data():
    return [
        ["Metric", "Definition", "Formula", "Importance"],
        ["Delinquency Density", "Frequency of payment failure.", "Count(DPD > 0) / Total Months", "Identifies chronic defaulters."],
        ["Maximum DPD", "The highest risk point reached.", "Max(DPD)", "Determines capital provisioning."],
        ["Sticky Bucket", "Categorization based on peak DPD.", "NPA/Sub-Standard logic", "Regulatory risk classification."],
        ["Rolling 3M Avg", "Moving average of delinquency.", "Sum(Last 3 Months) / 3", "Smooths spikes to show trends."],
        ["Cumulative DPD", "Total days past due across life.", "Sum(All DPD)", "Measures total loss exposure."]
    ]

def create_pdf_chart(df):
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150) # Increased size
    ax.set_facecolor('#ffffff')
    
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#1e3a8a", linewidth=2, label="DPD")
    ax.plot(plot_df.index, plot_df["Rolling_3M"], "--", color="#3b82f6", alpha=0.6, label="3M Avg")
    
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        peak_idx = plot_df["DPD"].idxmax()
        peak_val = plot_df["DPD"].max()
        ax.scatter(peak_idx, peak_val, color='red', s=100, edgecolors='black', zorder=5)
        ax.annotate(f'PEAK: {int(peak_val)}', (peak_idx, peak_val), xytext=(5, 5), textcoords='offset points', fontweight='bold', color='red')

    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45, fontsize=8)
    ax.legend()
    plt.tight_layout()
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp.name, bbox_inches='tight')
    plt.close(fig)
    return tmp.name

def build_pdf(story, code, row, df, metrics_df, styles):
    story.append(Paragraph(f"Loan Performance Report: {code}", styles['Heading1']))
    story.append(Spacer(1, 15))

    # Large Metrics Table (Spanning full width)
    m_data = [["Metric", "Value", "Risk Perspective"]] + metrics_df.values.tolist()
    mt = Table(m_data, colWidths=[2*inch, 1.5*inch, 3*inch])
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(mt)
    story.append(Spacer(1, 25))

    # Large Chart
    story.append(Image(create_pdf_chart(df), width=6.5*inch, height=3.2*inch))
    story.append(PageBreak())

# -------------------------------------------------
# 4. MAIN INTERFACE
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Risk Intel", layout="wide")

    with st.sidebar:
        st.title("🛡️ Risk Portal")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        uploaded_file = st.file_uploader("Upload Delinquency File", type=["xlsx"])

    if not uploaded_file:
        # REDESIGNED LANDING PAGE
        st.markdown("""
            <div style="background: white; padding: 4rem; border-radius: 25px; text-align: center; border: 1px solid #e2e8f0;">
                <h1 style="color: #1e3a8a; font-size: 3.5rem;">Risk Intelligence Dashboard</h1>
                <p style="color: #64748b; font-size: 1.3rem; margin-top: 1rem;">Automated Loan Delinquency Analysis & PDF Reporting Engine</p>
                <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 4rem;">
                    <div style="background: #f8fafc; padding: 2rem; border-radius: 15px; width: 280px; border-bottom: 4px solid #3b82f6;">
                        <h3 style="color: #1e3a8a;">📉 Analytics</h3>
                        <p style="color: #94a3b8; font-size: 0.9rem;">Calculates DPD density, episodes, and risk buckets instantly.</p>
                    </div>
                    <div style="background: #f8fafc; padding: 2rem; border-radius: 15px; width: 280px; border-bottom: 4px solid #3b82f6;">
                        <h3 style="color: #1e3a8a;">📋 Reporting</h3>
                        <p style="color: #94a3b8; font-size: 0.9rem;">Generates full-page PDF reports with trend highlighting.</p>
                    </div>
                </div>
                <p style="margin-top: 5rem; color: #cbd5e1; font-style: italic;">Upload an Excel file to begin processing accounts.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        raw_data = pd.read_excel(uploaded_file)
        codes = raw_data.iloc[:, 0].unique()
        months = raw_data.columns[3:]

        # Excel Writer for multi-sheet download
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            tabs = st.tabs([str(c) for c in codes])
            
            # Prepare Bulk PDF
            bulk_buf = BytesIO()
            doc = SimpleDocTemplate(bulk_buf, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            for tab, code in zip(tabs, codes):
                row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                df, metrics_df = analyze_loan(row, months)
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)
                
                with tab:
                    st.title(f"Analysis: {code}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Sanctioned", f"{row.iloc[1]:,.0f}")
                    c2.metric("Balance", f"{row.iloc[2]:,.0f}")
                    
                    # Screen Chart with Peak Highlight
                    fig, ax = plt.subplots(figsize=(10, 3.5))
                    active_plot = df[df["Status"] != "Not Disbursed"]
                    ax.plot(active_plot["Month"], active_plot["DPD"], marker="o", color="#3b82f6", label="DPD")
                    
                    if not active_plot.empty and active_plot["DPD"].max() > 0:
                        p_val = active_plot["DPD"].max()
                        p_mon = active_plot.loc[active_plot["DPD"].idxmax(), "Month"]
                        ax.plot(p_mon, p_val, 'r*', markersize=15, label="Max Point")
                        ax.text(p_mon, p_val + 5, f"MAX: {int(p_val)}", ha='center', color='red', fontweight='bold')
                    
                    plt.xticks(rotation=45)
                    ax.legend()
                    st.pyplot(fig)

                    # Individual PDF Download
                    single_buf = BytesIO()
                    single_doc = SimpleDocTemplate(single_buf, pagesize=letter)
                    single_story = []
                    build_pdf(single_story, code, row, df, metrics_df, styles)
                    
                    # Add Glossary to individual PDF
                    gloss_data = [["Metric", "Definition", "Formula", "Importance"]] + get_pdf_glossary_data()
                    gt = Table(gloss_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
                    gt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1e3a8a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
                    single_story.append(Paragraph("Metric Explanation", styles['Heading2']))
                    single_story.append(gt)
                    
                    single_doc.build(single_story)
                    st.download_button(f"📥 Download PDF {code}", single_buf.getvalue(), f"Report_{code}.pdf")

                    # Logic for Bulk PDF construction
                    build_pdf(story, code, row, df, metrics_df, styles)

            # Finalize Bulk PDF
            story.append(Paragraph("Full Risk Metric Dictionary", styles['Heading1']))
            story.append(Spacer(1, 15))
            final_glossary = [["Metric", "Definition", "Formula", "Importance"]] + get_pdf_glossary_data()
            ft = Table(final_glossary, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
            ft.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1e3a8a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.5,colors.grey),('FONTSIZE',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
            story.append(ft)
            doc.build(story)

        # Sidebar Downloads
        st.sidebar.markdown("---")
        st.sidebar.download_button("📂 Download All (Excel)", output_excel.getvalue(), "Risk_Analysis_Full.xlsx")
        st.sidebar.download_button("📦 Download All (PDF)", bulk_buf.getvalue(), "Risk_Reports_Bulk.pdf")
