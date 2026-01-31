import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import tempfile
from sklearn.linear_model import LinearRegression

# -------------------------------------------------
# AUTH
# -------------------------------------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if st.session_state.auth:
        return True

    st.markdown("""
    <style>
    section.main > div { padding-top: 0rem; }
    .stApp { background: radial-gradient(circle at top, #eef2ff, #f8fafc); }
    .login-wrapper {
        height: 100vh; display:flex; align-items:center; justify-content:center;
    }
    .login-card {
        background:white; width:420px; padding:3rem;
        border-radius:16px; box-shadow:0 20px 45px rgba(0,0,0,.12);
        text-align:center;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-wrapper'><div class='login-card'>", unsafe_allow_html=True)
    st.markdown("### 🛡️ Risk Intelligence Portal")
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
# SAFE STAT FUNCTIONS (NO SCIPY)
# -------------------------------------------------
def calc_skew(x):
    m = np.mean(x)
    s = np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 3) if s != 0 else 0

def calc_kurtosis(x):
    m = np.mean(x)
    s = np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 4) if s != 0 else 0

def calc_mode(x):
    return pd.Series(x).mode().iloc[0]

# -------------------------------------------------
# METRICS ENGINE (EXCEL)
# -------------------------------------------------
def build_excel_metrics(dpd_series):
    dpd = dpd_series.values.astype(float)
    t = np.arange(len(dpd)).reshape(-1, 1)

    lr = LinearRegression().fit(t, dpd)
    slope = lr.coef_[0]

    metrics = [
        ["Mean DPD", round(np.mean(dpd),2), "Average delinquency per month"],
        ["Median DPD", int(np.median(dpd)), "50% months below"],
        ["Mode DPD", int(calc_mode(dpd)), "Most frequent"],
        ["Min DPD", int(np.min(dpd)), "Best month"],
        ["Max DPD", int(np.max(dpd)), "Worst month"],
        ["Range", int(np.ptp(dpd)), "Spread"],
        ["Std Deviation", round(np.std(dpd,ddof=1),2), "Volatility"],
        ["Skewness", round(calc_skew(dpd),2), "Right tail risk"],
        ["Kurtosis", round(calc_kurtosis(dpd),2), "Extreme events"],

        ["Delinquent Months", int((dpd>0).sum()), "Frequency"],
        ["Proportion Delinquent", round((dpd>0).mean(),2), "Share delinquent"],

        ["Cumulative DPD", int(dpd.sum()), "Life exposure"],
        ["Trend Slope", round(slope,2), "Momentum"],
        ["Autocorr Lag 1",
         round(np.corrcoef(dpd[:-1],dpd[1:])[0,1],2) if len(dpd)>1 else 0,
         "Persistence"],

        ["Prob 90+ DPD", round((dpd>=90).mean(),3), "Extreme risk"],
        ["Coeff of Variation",
         round(np.std(dpd)/np.mean(dpd),2) if np.mean(dpd)>0 else 0,
         "Relative volatility"],
        ["Sticky Bucket",
         "90+" if np.max(dpd)>=90 else "60+" if np.max(dpd)>=60 else "30+",
         "Historical severity"]
    ]

    return pd.DataFrame(metrics, columns=["Metric","Value","Interpretation"])

# -------------------------------------------------
# ANALYSIS
# -------------------------------------------------
def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    max_dpd = dpd.max()
    max_month = df.loc[df["DPD"].idxmax(),"Month"]
    return df, max_dpd, max_month

# -------------------------------------------------
# CHART
# -------------------------------------------------
def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10,3.5))
    ax.plot(df["Month"], df["DPD"], marker="o")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--")
    ax.plot(max_month, max_dpd, "r*", markersize=14)
    ax.text(max_month, max_dpd+3, f"MAX {int(max_dpd)}",
            ha="center", color="red")
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------------------------------------
# PDF
# -------------------------------------------------
def build_pdf(story, code, df, max_dpd, max_month):
    styles = getSampleStyleSheet()
    story.append(Paragraph(
        f"Loan Performance – {code}",
        ParagraphStyle("t", fontName="Helvetica-Bold",
                       fontSize=16, leading=18)))
    story.append(Spacer(1,12))

    fig_path = tempfile.NamedTemporaryFile(
        delete=False, suffix=".png").name
    plot_chart(df,max_dpd,max_month).savefig(
        fig_path, dpi=150, bbox_inches="tight")
    plt.close()

    story.append(Image(fig_path,6.5*inch,3.2*inch))
    story.append(PageBreak())

# -------------------------------------------------
# APP
# -------------------------------------------------
if check_password():
    st.set_page_config("Risk Portal", layout="wide")

    with st.sidebar:
        st.title("🛡 Risk Portal")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
        file = st.file_uploader("Upload Excel",["xlsx"])

    if file:
        raw = pd.read_excel(file)
        codes = raw.iloc[:,0].unique()
        months = raw.columns[3:]

        excel_buf = BytesIO()
        pdf_buf = BytesIO()
        doc = SimpleDocTemplate(pdf_buf,pagesize=letter)
        story = []

        with pd.ExcelWriter(excel_buf,engine="xlsxwriter") as writer:
            tabs = st.tabs([str(c) for c in codes])
            for tab, code in zip(tabs,codes):
                row = raw[raw.iloc[:,0]==code].iloc[0]
                df, max_dpd, max_month = analyze(row,months)

                df.to_excel(writer,f"DATA_{code}",index=False)
                build_excel_metrics(df["DPD"]).to_excel(
                    writer,f"METRICS_{code}",index=False)

                with tab:
                    st.subheader(f"Account {code}")
                    st.pyplot(plot_chart(df,max_dpd,max_month))

                build_pdf(story,code,df,max_dpd,max_month)

            doc.build(story)

        st.sidebar.download_button(
            "📊 Download Excel",
            excel_buf.getvalue(),
            "Risk_Metrics.xlsx")

        st.sidebar.download_button(
            "📦 Download PDF",
            pdf_buf.getvalue(),
            "Risk_Report.pdf")
