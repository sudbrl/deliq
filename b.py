import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile

# -------------------------------------------------
# 1. AUTHENTICATION (DTI STYLE)
# -------------------------------------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False

    if st.session_state.auth:
        return True

    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(180deg,#f8fafc,#eef2ff);
    }
    .login-wrap {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .login-card {
        background: white;
        width: 420px;
        padding: 2.8rem;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,.08);
        border: 1px solid #e5e7eb;
    }
    .login-title {
        font-size: 1.5rem;
        font-weight: 600;
        text-align: center;
        color: #111827;
    }
    .login-sub {
        font-size: .9rem;
        text-align: center;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-wrap'><div class='login-card'>", unsafe_allow_html=True)
    st.markdown("<div class='login-title'>Risk Intelligence</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-sub'>Secure Analytics Portal</div>", unsafe_allow_html=True)

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Sign in", use_container_width=True):
        if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.markdown("</div></div>", unsafe_allow_html=True)
    return False

# -------------------------------------------------
# 2. ANALYTICS
# -------------------------------------------------
def analyze_loan(row, months):
    dpd = row[months].astype(float)
    active = dpd.dropna().fillna(0)

    df = pd.DataFrame({
        "Month": months.astype(str),
        "DPD": dpd.fillna(0),
    })
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)

    max_d = active.max()
    metrics = pd.DataFrame([
        ["Loan Status", "Active" if active.index[-1] == months[-1] else "Settled", "Current"],
        ["Active Tenure", f"{len(active)} Months", "Exposure"],
        ["Delinquency Density", f"{(active>0).mean():.1%}", "Frequency"],
        ["Maximum DPD", f"{int(max_d)} Days", "Peak Risk"],
        ["Sticky Bucket", "90+" if max_d>=90 else "30-89" if max_d>=30 else "0-29", "Risk Tier"],
        ["Cumulative DPD", f"{int(active.sum())}", "Loss Volume"]
    ], columns=["Metric","Value","Importance"])

    return df, metrics

# -------------------------------------------------
# 3. METRIC GLOSSARY (UI ONLY)
# -------------------------------------------------
def metric_glossary():
    return pd.DataFrame([
        ["Delinquency Density","Payment failure frequency","Count(DPD>0)/Months"],
        ["Maximum DPD","Worst delinquency observed","Max(DPD)"],
        ["Sticky Bucket","Peak delinquency band","Regulatory buckets"],
        ["Rolling 3M Avg","Smoothed delinquency trend","Mean(last 3)"],
        ["Cumulative DPD","Lifetime delinquency volume","Sum(DPD)"]
    ], columns=["Metric","Definition","Logic"])

# -------------------------------------------------
# 4. PDF
# -------------------------------------------------
def create_chart(df):
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(df["Month"], df["DPD"], marker="o")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--")
    plt.xticks(rotation=45)
    plt.tight_layout()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    plt.savefig(tmp.name)
    plt.close()
    return tmp.name

def build_pdf(story, code, df, metrics, styles):
    story.append(Paragraph(f"Loan Performance Report – {code}", styles["Heading1"]))
    story.append(Spacer(1,12))

    t = Table([metrics.columns.tolist()] + metrics.values.tolist(),
              colWidths=[2*inch,2*inch,2.5*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),.5,colors.grey)
    ]))
    story.append(t)
    story.append(Spacer(1,20))
    story.append(Image(create_chart(df),6.5*inch,3.2*inch))
    story.append(PageBreak())

# -------------------------------------------------
# 5. APP
# -------------------------------------------------
if check_password():
    st.set_page_config("Risk Intel", layout="wide")

    with st.sidebar:
        st.title("🛡 Risk Portal")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
        file = st.file_uploader("Upload Delinquency File", ["xlsx"])

    if file:
        raw = pd.read_excel(file)
        codes = raw.iloc[:,0].unique()
        months = raw.columns[3:]

        excel_buf = BytesIO()
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:

            bulk_pdf = BytesIO()
            doc = SimpleDocTemplate(bulk_pdf, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            tabs = st.tabs([str(c) for c in codes])

            for tab, code in zip(tabs, codes):
                row = raw[raw.iloc[:,0]==code].iloc[0]
                df, metrics = analyze_loan(row, months)
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)

                with tab:
                    st.subheader(f"Account {code}")
                    st.dataframe(metrics, hide_index=True)

                    with st.expander("📘 Metric Explanation"):
                        st.dataframe(metric_glossary(), hide_index=True, use_container_width=True)

                    fig, ax = plt.subplots(figsize=(10,3))
                    ax.plot(df["Month"], df["DPD"], marker="o")
                    plt.xticks(rotation=45)
                    st.pyplot(fig)

                    sbuf = BytesIO()
                    sdoc = SimpleDocTemplate(sbuf, pagesize=letter)
                    sstory = []
                    build_pdf(sstory, code, df, metrics, styles)
                    sdoc.build(sstory)

                    st.download_button("📄 Download Report", sbuf.getvalue(), f"Report_{code}.pdf")

                build_pdf(story, code, df, metrics, styles)

            doc.build(story)

        st.sidebar.markdown("---")
        st.sidebar.download_button("📊 Download Excel", excel_buf.getvalue(), "Risk_Analysis.xlsx")
        st.sidebar.download_button("📦 Download Report (Bulk)", bulk_pdf.getvalue(), "Report_Bulk.pdf")
