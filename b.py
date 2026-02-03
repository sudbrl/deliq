import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile


# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Risk Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -------------------- AUTH --------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False

    if st.session_state.auth:
        return True

    st.markdown("""<style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    header, footer { visibility: hidden !important; }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: white;
        padding: 3rem;
        border-radius: 20px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    }
    .stTextInput input { border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px; }
    .stButton button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; padding: 12px; font-weight: bold;
        border-radius: 8px; width: 100%;
    }
    [data-testid="stSidebar"] { display: none; }
    </style>""", unsafe_allow_html=True)

    st.write(""); st.write(""); st.write(""); st.write(""); st.write("")
    col1, col2, col3 = st.columns([1, 0.6, 1])

    with col2:
        username = st.text_input("Username", label_visibility="collapsed")
        password = st.text_input("Password", type="password", label_visibility="collapsed")

        if st.button("Sign In", use_container_width=True):
            if username in st.secrets.get("passwords", {}) and password == st.secrets["passwords"][username]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Invalid credentials")

    return False


# -------------------- SAFE STAT FUNCTIONS --------------------
def _clean(x):
    return pd.Series(x).dropna().astype(float)


def calc_skew(x):
    s = _clean(x)
    if len(s) < 2:
        return 0
    m = s.mean()
    sd = s.std(ddof=1)
    return np.mean(((s - m) / sd) ** 3) if sd != 0 else 0


def calc_kurtosis(x):
    s = _clean(x)
    if len(s) < 2:
        return 0
    m = s.mean()
    sd = s.std(ddof=1)
    return np.mean(((s - m) / sd) ** 4) if sd != 0 else 0


# FIXED (no artificial 0 dominance)
def calc_mode(x):
    s = _clean(x)
    if len(s) == 0:
        return np.nan
    modes = s.mode()
    return modes.max()   # choose highest bucket if tie


def calc_trend_slope(y):
    s = _clean(y)
    if len(s) < 2:
        return 0
    x = np.arange(len(s))
    return np.polyfit(x, s, 1)[0]


# -------------------- METRICS ENGINE --------------------
def build_excel_metrics(dpd_series, months):
    dpd = _clean(dpd_series)

    if len(dpd) == 0:
        dpd = pd.Series([0.0])

    metrics = [
        ["Mean DPD", round(dpd.mean(), 2), "Average delinquency per month"],
        ["Median DPD", round(dpd.median(), 2), "50% months below this value"],
        ["Mode DPD", calc_mode(dpd), "Most frequent DPD value"],
        ["Min DPD", int(dpd.min()), "Best performing month"],
        ["Max DPD", int(dpd.max()), "Worst performing month"],
        ["Range", int(dpd.max() - dpd.min()), "Max - Min spread"],
        ["Std Deviation", round(dpd.std(ddof=1), 2), "Payment volatility measure"],
        ["Skewness", round(calc_skew(dpd), 2), "Right tail risk"],
        ["Kurtosis", round(calc_kurtosis(dpd), 2), "Extreme event risk"],
        ["Delinquent Months", int((dpd > 0).sum()), "Months with delays"],
        ["Proportion Delinquent", round((dpd > 0).mean(), 2), "% delinquent"],
        ["Cumulative DPD", int(dpd.sum()), "Total exposure"],
        ["Trend Slope (DPD/mo)", round(calc_trend_slope(dpd), 2), "Monthly change rate"],
        ["Coeff of Variation", round(dpd.std()/dpd.mean(), 2) if dpd.mean() > 0 else 0, "Relative volatility"],
    ]

    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])


# -------------------- ANALYSIS (FIXED — removed fillna(0)) --------------------
def analyze(row, months):
    dpd = pd.to_numeric(row[months], errors="coerce")  # keep NaN

    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean()

    clean = _clean(dpd)

    max_dpd = clean.max() if len(clean) else 0
    max_month = df.loc[df["DPD"].idxmax(), "Month"] if len(clean) else None

    important_metrics = {
        "Mean DPD": round(clean.mean(), 2) if len(clean) else 0,
        "Max DPD": int(max_dpd),
        "Cumulative DPD": int(clean.sum()),
        "Trend Slope": round(calc_trend_slope(clean), 2),
        "Sticky Bucket": (
            "90+" if max_dpd >= 90 else
            "60+" if max_dpd >= 60 else
            "30+" if max_dpd >= 30 else
            "Current"
        )
    }

    return df, max_dpd, max_month, important_metrics


# -------------------- CHART (unchanged visuals) --------------------
def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", linewidth=2, markersize=6, label="DPD", color="#3b82f6")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", linewidth=1.5, label="3M Rolling Avg", color="#8b5cf6")

    if max_month is not None:
        ax.plot(max_month, max_dpd, "r*", markersize=16)

    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig


# -------------------- MAIN APP (unchanged) --------------------
if check_password():

    st.title("📊 Credit Risk Analytics Dashboard")

    file = st.file_uploader("Upload Portfolio Excel", type=["xlsx"])

    if file:
        raw = pd.read_excel(file)
        codes = raw.iloc[:, 0].unique()
        months = raw.columns[3:]

        excel_buf = BytesIO()

        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
            tabs = st.tabs([f"Account {c}" for c in codes])

            for tab, code in zip(tabs, codes):
                row = raw[raw.iloc[:, 0] == code].iloc[0]
                df, max_dpd, max_month, metrics = analyze(row, months)

                df.to_excel(writer, f"DATA_{code}", index=False)
                build_excel_metrics(df["DPD"], months).to_excel(writer, f"METRICS_{code}", index=False)

                with tab:
                    st.pyplot(plot_chart(df, max_dpd, max_month))
                    st.dataframe(build_excel_metrics(df["DPD"], months), use_container_width=True)

        st.download_button(
            "Download Excel Report",
            excel_buf.getvalue(),
            "Risk_Metrics_Report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
