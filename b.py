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
# 1. AUTHENTICATION SYSTEM (Refined)
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
        st.markdown("<h2 style='text-align:center; color:#1e3a8a;'>Portal Access</h2>", unsafe_allow_html=True)
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Secure Login", use_container_width=True):
            if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Invalid Credentials")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

# -------------------------------------------------
# 2. PDF GENERATION LOGIC (Enhanced Explanations)
# -------------------------------------------------
def get_pdf_glossary():
    """Returns a comprehensive, easy-to-read metric explanation list."""
    return [
        ["Metric", "Description", "Formula / Logic", "Risk Importance"],
        ["Loan Status", "Current state of the credit account.", "Active vs Settled", "Identifies if exposure is ongoing."],
        ["Disbursement", "The month the loan was first issued.", "First valid DPD record", "Establishes loan vintage."],
        ["Active Period", "Total duration the loan has been live.", "Months from start to date", "Used for aging analysis."],
        ["Delinquency Density", "Frequency of payment misses.", "(Delinquent Months / Total Months)", "Shows chronic vs. accidental default."],
        ["LTD Cumulative DPD", "Sum of all days past due since inception.", "Sum(DPD_i)", "Quantifies total delinquency volume."],
        ["Average DPD", "The typical delay in repayment.", "Mean(DPD)", "Smooths out temporary spikes."],
        ["Maximum DPD", "The highest single DPD point reached.", "Max(DPD)", "Critical for regulatory provisioning."],
        ["Current DPD", "Most recent reported delinquency status.", "Latest DPD entry", "Urgency indicator for collections."],
        ["Episodes", "Count of distinct delinquency cycles.", "Count(Active -> Cured)", "Identifies 'Broken Promise' behavior."],
        ["Sticky Bucket", "High-level risk tiering based on peak.", "0-29 / 30-89 / 90+", "Matches standard Basel III risk buckets."]
    ]

def add_glossary_to_pdf(story, styles):
    story.append(PageBreak())
    title_style = ParagraphStyle('GlossaryTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=20, textColor=colors.HexColor('#1e3a8a'))
    story.append(Paragraph("Risk Metric Glossary & Definitions", title_style))
    
    data = get_pdf_glossary()
    # Adjusting widths for readability - avoiding "compact" feel
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

# -------------------------------------------------
# 3. DASHBOARD MAIN CODE
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Risk Intel Portal", layout="wide")

    # Sidebar Logout
    with st.sidebar:
        st.markdown("### 🛠️ User Controls")
        if st.button("Logout", type="primary"):
            st.session_state.clear()
            st.rerun()
        uploaded_file = st.file_uploader("Upload Delinquency Data (.xlsx)", type=["xlsx"])

    if not uploaded_file:
        # REDESIGNED LANDING PAGE
        st.markdown("""
            <div style="background-color: white; padding: 50px; border-radius: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;">
                <h1 style="color: #1e3a8a; font-size: 3rem; margin-bottom: 10px;">Risk Intelligence Portal</h1>
                <p style="color: #64748b; font-size: 1.2rem;">Advanced Analytics & Automated Delinquency Reporting</p>
                <hr style="width: 50px; border: 2px solid #3b82f6; margin: 30px auto;">
                <div style="display: flex; justify-content: space-around; margin-top: 50px;">
                    <div style="width: 30%;">
                        <h3 style="color: #1e3a8a;">📊 Real-time Analysis</h3>
                        <p style="color: #94a3b8;">Instantly calculate DPD density, episodes, and rolling averages across loan life-cycles.</p>
                    </div>
                    <div style="width: 30%;">
                        <h3 style="color: #1e3a8a;">📄 Professional Reports</h3>
                        <p style="color: #94a3b8;">Generate investor-grade PDF reports with automated charting and peak DPD highlights.</p>
                    </div>
                    <div style="width: 30%;">
                        <h3 style="color: #1e3a8a;">📉 Risk Tiering</h3>
                        <p style="color: #94a3b8;">Automatically categorize loans into sticky buckets and identify chronic delinquency trends.</p>
                    </div>
                </div>
                <div style="margin-top: 60px; padding: 20px; border: 1px dashed #cbd5e1; border-radius: 10px;">
                    <p style="color: #64748b;">To begin, please <b>Upload an Excel File</b> using the sidebar.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # (Processing logic from your original file continues here...)
        # Note: When calling generate_pdf, ensure add_glossary_to_pdf(story, styles) is called.
        st.success("File Loaded Successfully. Analysis Ready.")
