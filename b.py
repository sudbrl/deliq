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
    """Handles professional login and fixes blank screen logout issue."""
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
                st.error("Invalid credentials")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

# -------------------------------------------------
# 2. PDF GLOSSARY & HELPERS
# -------------------------------------------------
def get_pdf_glossary():
    """Returns structured data for the Full Risk Metric Dictionary."""
    return [
        ["Metric", "Definition", "Formula / Logic", "Importance"],
        ["Delinquency Density", "Frequency of payment failure.", "Count(DPD > 0) / Total Months", "Identifies chronic defaulters."],
        ["Maximum DPD", "The highest risk point reached.", "Max(DPD)", "Determines capital provisioning."],
        ["Sticky Bucket", "Categorization based on peak DPD.", "NPA/Sub-Standard logic", "Regulatory risk classification."],
        ["Rolling 3M Avg", "Moving average of delinquency.", "Sum(Last 3 Months) / 3", "Smooths spikes to show trends."],
        ["Cumulative DPD", "Total days past due across life.", "Sum(All DPD)", "Measures total loss exposure."]
    ]

def add_glossary_page(story, styles):
    """Adds a dedicated, legible page for metric explanations."""
    story.append(PageBreak())
    title_style = ParagraphStyle('GlossaryTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=20, textColor=colors.HexColor('#1e3a8a'))
    story.append(Paragraph("Full Risk Metric Dictionary", title_style))
    
    data = [["Metric", "Definition", "Formula", "Importance"]] + get_pdf_glossary()
    table = Table(data, colWidths=[1.3*inch, 2.0*inch, 1.5*inch, 2.2*inch])
    
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

# -------------------------------------------------
# 3. CORE ANALYTICS
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
        ("Cumulative DPD", f"{int(active_dpd.sum())}", "Risk Volume")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Importance"])

# -------------------------------------------------
# 4. MAIN APP INTERFACE
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Risk Intel Portal", layout="wide")

    st.markdown("""
    <style>
        .stApp { background-color: #f8fafc; }
        .block-container { background-color: white; border-radius: 15px; padding: 2rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        .hero-section { text-align: center; padding: 4rem 2rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 20px; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("🛡️ Risk Portal")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        uploaded_file = st.file_uploader("Upload Delinquency Data (.xlsx)", type=["xlsx"])

    if not uploaded_file:
        st.markdown("""
            <div class="hero-section">
                <h1 style="color: #1e3a8a; font-size: 3rem; font-weight: 800;">Risk Intelligence Dashboard</h1>
                <p style="color: #475569; font-size: 1.25rem;">Automated Loan Delinquency Tracking & PDF Reporting</p>
                <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 3rem;">
                    <div style="background: white; padding: 2rem; border-radius: 15px; width: 250px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <h4 style="color: #3b82f6;">📊 Analytics</h4>
                        <p style="font-size: 0.9rem; color: #64748b;">Real-time DPD density and risk bucket calculations.</p>
                    </div>
                    <div style="background: white; padding: 2rem; border-radius: 15px; width: 250px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <h4 style="color: #3b82f6;">📥 Reporting</h4>
                        <p style="font-size: 0.9rem; color: #64748b;">Professional PDF exports with glossary & peak highlights.</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        raw_data = pd.read_excel(uploaded_file)
        codes = raw_data.iloc[:, 0].unique()
        months = raw_data.columns[3:]

        # Excel & Bulk PDF setup
        excel_out = BytesIO()
        bulk_buf = BytesIO()
        doc = SimpleDocTemplate(bulk_buf, pagesize=letter)
        bulk_story = []
        styles = getSampleStyleSheet()

        with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:
            tabs = st.tabs([str(c) for c in codes])
            for tab, code in zip(tabs, codes):
                row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                df, m_df = analyze_loan(row, months)
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)
                
                with tab:
                    st.header(f"Account: {code}")
                    c1, c2 = st.columns(2)
                    c1.metric("Sanctioned Limit", f"{row.iloc[1]:,.0f}")
                    c2.metric("Current Balance", f"{row.iloc[2]:,.0f}")

                    # Screen Chart with Max Data Labels
                    fig, ax = plt.subplots(figsize=(10, 3.5))
                    p_data = df[df["Status"] != "Not Disbursed"]
                    ax.plot(p_data["Month"], p_data["DPD"], marker="o", color="#3b82f6", label="DPD")
                    
                    if not p_data.empty and p_data["DPD"].max() > 0:
                        mx = p_data["DPD"].max()
                        mx_mon = p_data.loc[p_data["DPD"].idxmax(), "Month"]
                        ax.plot(mx_mon, mx, 'r*', markersize=15, label="Peak Point")
                        ax.text(mx_mon, mx + 5, f"MAX: {int(mx)}", ha='center', fontweight='bold', color='red')
                    
                    plt.xticks(rotation=45)
                    st.pyplot(fig)

                    # Individual PDF Generation
                    single_buf = BytesIO()
                    single_doc = SimpleDocTemplate(single_buf, pagesize=letter)
                    s_story = [Paragraph(f"Loan Risk Report: {code}", styles['Heading1']), Spacer(1, 12)]
                    
                    # Large Table in PDF
                    t_data = [["Metric", "Value", "Perspective"]] + m_df.values.tolist()
                    t = Table(t_data, colWidths=[2*inch, 1.5*inch, 3.5*inch])
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1e3a8a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.5,colors.grey)]))
                    s_story.append(t)
                    
                    add_glossary_page(s_story, styles)
                    single_doc.build(s_story)
                    st.download_button(f"📄 Download PDF {code}", single_buf.getvalue(), f"Report_{code}.pdf")

        # Sidebar Global Downloads
        st.sidebar.markdown("---")
        st.sidebar.download_button("📂 Download All (Excel)", excel_out.getvalue(), "Risk_Analysis.xlsx")
