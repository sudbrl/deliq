import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile

# -------------------------------------------------
# 1. AUTHENTICATION – TRUE CENTER (NO TOP GAP)
# -------------------------------------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if st.session_state.auth:
        return True

    st.markdown("""
    <style>
    /* Remove Streamlit top padding */
    section.main > div {
        padding-top: 0rem;
    }

    .stApp {
        background: radial-gradient(circle at top, #eef2ff, #f8fafc);
    }
    .login-wrapper {
        height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .login-card {
        background: white;
        width: 420px;
        padding: 3rem 2.8rem;
        border-radius: 16px;
        box-shadow: 0 20px 45px rgba(0,0,0,0.12);
        border: 1px solid #e5e7eb;
        text-align: center;
    }
    .logo { font-size: 3.2rem; margin-bottom: .5rem; }
    .title { font-size: 1.6rem; font-weight: 600; color: #111827; }
    .sub { font-size: .9rem; color: #6b7280; margin-bottom: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-wrapper'><div class='login-card'>", unsafe_allow_html=True)
    st.markdown("<div class='logo'>🛡️</div>", unsafe_allow_html=True)
    st.markdown("<div class='title'>Risk Intelligence</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub'>Secure Analytics Portal</div>", unsafe_allow_html=True)

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
# 2. ANALYTICS (UNCHANGED)
# -------------------------------------------------
def analyze_loan(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)

    max_dpd = dpd.max()
    max_month = df.loc[df["DPD"].idxmax(), "Month"]

    metrics = pd.DataFrame([
        ["Loan Status", "Active" if dpd.iloc[-1] > 0 else "Settled"],
        ["Active Tenure (Months)", len(dpd)],
        ["Delinquency Density", f"{(dpd>0).mean():.1%}"],
        ["Max DPD", int(max_dpd)],
        ["Max DPD Month", max_month],
        ["Months Ever Delinquent", int((dpd>0).sum())],
        ["Severe DPD Rate (60+)", f"{(dpd>=60).mean():.1%}"],
        ["Average DPD", f"{dpd.mean():.1f}"],
        ["Cumulative DPD", int(dpd.sum())]
    ], columns=["Metric", "Value"])

    return df, metrics, max_dpd, max_month

# -------------------------------------------------
# 3. CHART (UNCHANGED)
# -------------------------------------------------
def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--")
    ax.plot(max_month, max_dpd, "r*", markersize=14)
    ax.text(max_month, max_dpd + 3, f"MAX {int(max_dpd)}",
            ha="center", color="red", fontweight="bold")
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def create_pdf_chart(df, max_dpd, max_month):
    fig = plot_chart(df, max_dpd, max_month)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(tmp.name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return tmp.name

# -------------------------------------------------
# 4. PDF (FIXED TEXT STRETCHING)
# -------------------------------------------------
def build_pdf(story, code, df, metrics, max_dpd, max_month, styles):
    story.append(Paragraph(
        f"Loan Performance Report – {code}",
        ParagraphStyle(
            name="Title",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18
        )
    ))
    story.append(Spacer(1, 12))

    table = Table(
        [metrics.columns.tolist()] + metrics.values.tolist(),
        colWidths=[3*inch, 3*inch]
    )
    table.setStyle(TableStyle([
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),10),
        ("LEADING",(0,0),(-1,-1),12),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e3a8a")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 18))

    story.append(Image(create_pdf_chart(df, max_dpd, max_month),
                       6.5*inch, 3.2*inch))
    story.append(PageBreak())

# -------------------------------------------------
# 5. APP (UNCHANGED)
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
        codes = raw.iloc[:, 0].unique()
        months = raw.columns[3:]

        excel_buf = BytesIO()
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
            bulk_pdf = BytesIO()
            doc = SimpleDocTemplate(bulk_pdf, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            tabs = st.tabs([str(c) for c in codes])
            for tab, code in zip(tabs, codes):
                row = raw[raw.iloc[:, 0] == code].iloc[0]
                df, metrics, max_dpd, max_month = analyze_loan(row, months)
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)

                with tab:
                    st.subheader(f"Account {code}")
                    st.dataframe(metrics, hide_index=True)
                    st.pyplot(plot_chart(df, max_dpd, max_month))

                    sbuf = BytesIO()
                    sdoc = SimpleDocTemplate(sbuf, pagesize=letter)
                    sstory = []
                    build_pdf(sstory, code, df, metrics, max_dpd, max_month, styles)
                    sdoc.build(sstory)
                    st.download_button("📄 Download Report",
                                       sbuf.getvalue(),
                                       f"Report_{code}.pdf")

                build_pdf(story, code, df, metrics, max_dpd, max_month, styles)

            doc.build(story)

        st.sidebar.markdown("---")
        st.sidebar.download_button("📊 Download Excel",
                                   excel_buf.getvalue(),
                                   "Risk_Analysis.xlsx")
        st.sidebar.download_button("📦 Download Report (Bulk)",
                                   bulk_pdf.getvalue(),
                                   "Report_Bulk.pdf")
