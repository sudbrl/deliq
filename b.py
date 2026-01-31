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
    .stApp {
        background-color: #0f172a;
    }
    .login-container {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .login-box {
        background: #ffffff;
        width: 420px;
        padding: 3rem;
        border-radius: 14px;
        box-shadow: 0 30px 60px rgba(0,0,0,0.25);
    }
    .login-title {
        text-align: center;
        font-size: 1.6rem;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 0.25rem;
    }
    .login-subtitle {
        text-align: center;
        font-size: 0.9rem;
        color: #64748b;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-container'><div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<div class='login-title'>Risk Intelligence Platform</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-subtitle'>Secure Access</div>", unsafe_allow_html=True)

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.markdown("</div></div>", unsafe_allow_html=True)
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
    status = (
        ["Not Disbursed"] * start_pos +
        ["Active"] * (end_pos - start_pos + 1) +
        ["Settled"] * (len(months) - 1 - end_pos)
    )

    df = pd.DataFrame({
        "Month": months.astype(str),
        "DPD": dpd.fillna(0).astype(float),
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
# 3. METRIC EXPLANATION (SCREEN ONLY)
# -------------------------------------------------
def get_metric_glossary():
    return pd.DataFrame([
        ["Delinquency Density", "Frequency of payment failure", "Count(DPD>0)/Months", "Chronic risk detection"],
        ["Maximum DPD", "Highest delinquency observed", "Max(DPD)", "Capital provisioning"],
        ["Sticky Bucket", "Peak delinquency classification", "DPD Thresholds", "Regulatory risk tier"],
        ["Rolling 3M Avg", "Smoothed delinquency trend", "Mean(last 3)", "Volatility reduction"],
        ["Cumulative DPD", "Lifetime delinquency volume", "Sum(DPD)", "Loss exposure"]
    ], columns=["Metric", "Definition", "Formula", "Importance"])

# -------------------------------------------------
# 4. PDF CHART & REPORT
# -------------------------------------------------
def create_pdf_chart(df):
    plot_df = df[df["Status"] != "Not Disbursed"]
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", linewidth=2)
    ax.plot(plot_df.index, plot_df["Rolling_3M"], linestyle="--", alpha=0.6)
    ax.set_xticks(plot_df.index)
    ax.set_xticklabels(plot_df["Month"], rotation=45, fontsize=8)
    plt.tight_layout()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(tmp.name)
    plt.close(fig)
    return tmp.name

def build_pdf(story, code, df, metrics_df, styles):
    story.append(Paragraph(f"Loan Performance Report: {code}", styles["Heading1"]))
    story.append(Spacer(1, 12))

    table_data = [["Metric", "Value", "Risk Perspective"]] + metrics_df.values.tolist()
    table = Table(table_data, colWidths=[2*inch, 1.5*inch, 3*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8)
    ]))
    story.append(table)
    story.append(Spacer(1, 20))
    story.append(Image(create_pdf_chart(df), width=6.5*inch, height=3.2*inch))
    story.append(PageBreak())

# -------------------------------------------------
# 5. MAIN APPLICATION
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Risk Intel", layout="wide")

    with st.sidebar:
        st.title("🛡️ Risk Portal")
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        uploaded_file = st.file_uploader("Upload Delinquency File", type=["xlsx"])

    if uploaded_file:
        raw = pd.read_excel(uploaded_file)
        codes = raw.iloc[:, 0].unique()
        months = raw.columns[3:]

        bulk_buf = BytesIO()
        doc = SimpleDocTemplate(bulk_buf, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        tabs = st.tabs([str(c) for c in codes])
        for tab, code in zip(tabs, codes):
            row = raw[raw.iloc[:,0] == code].iloc[0]
            df, metrics_df = analyze_loan(row, months)

            with tab:
                st.subheader(f"Account: {code}")
                st.dataframe(metrics_df, hide_index=True)

                with st.expander("📘 Metric Explanation"):
                    st.dataframe(get_metric_glossary(), hide_index=True, use_container_width=True)

                fig, ax = plt.subplots(figsize=(10, 3))
                active = df[df["Status"] != "Not Disbursed"]
                ax.plot(active["Month"], active["DPD"], marker="o")
                plt.xticks(rotation=45)
                st.pyplot(fig)

                single_buf = BytesIO()
                single_doc = SimpleDocTemplate(single_buf, pagesize=letter)
                single_story = []
                build_pdf(single_story, code, df, metrics_df, styles)
                single_doc.build(single_story)

                st.download_button("📥 Download Report", single_buf.getvalue(), f"Report_{code}.pdf")

            build_pdf(story, code, df, metrics_df, styles)

        doc.build(story)
        st.sidebar.download_button("📦 Download Report (Bulk)", bulk_buf.getvalue(), "Report_Bulk.pdf")
