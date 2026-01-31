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

# -------------------- AUTH --------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if st.session_state.auth:
        return True

    # removed extra space/padding at top
    st.markdown("""
    <style>
    section.main > div:first-child { padding-top: 0rem !important; }
    .block-container { padding-top: 0rem !important; }
    header {visibility: hidden;}
    .stApp {
        background: radial-gradient(circle at top, #eef2ff, #f8fafc);
    }
    .login-wrapper {
        height:100vh;
        display:flex;
        align-items:center;
        justify-content:center;
        margin:0;
    }
    .login-card {
        background:white;
        width:420px;
        padding:1.5rem;
        border-radius:16px;
        box-shadow:0 20px 45px rgba(0,0,0,.12);
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


# -------------------- SAFE STAT FUNCTIONS --------------------
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

def calc_trend_slope(y):
    x = np.arange(len(y))
    x_mean = x.mean()
    y_mean = y.mean()
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)
    return num / den if den != 0 else 0


# -------------------- SEASONALITY ENGINE --------------------
def build_seasonality(df):
    s = df["DPD"].values
    mean_val = np.mean(s)

    df_seas = df.copy()
    df_seas["MoM_Change"] = df_seas["DPD"].diff().fillna(0)
    df_seas["MA_3"] = df_seas["DPD"].rolling(3).mean().fillna(0)
    df_seas["MA_6"] = df_seas["DPD"].rolling(6).mean().fillna(0)
    df_seas["Season_Index"] = df_seas["DPD"] / mean_val if mean_val != 0 else 0

    if len(s) >= 12:
        lag12 = np.corrcoef(s[:-12], s[12:])[0, 1]
    else:
        lag12 = 0

    amplitude = df_seas["Season_Index"].max() - df_seas["Season_Index"].min()
    coef_season = df_seas["Season_Index"].std()

    summary = pd.DataFrame([
        ["Lag 12 Autocorr", round(lag12, 3), "Annual seasonality strength (>0.5 strong)"],
        ["Seasonal Amplitude", round(amplitude, 3), "Peak minus trough index"],
        ["Seasonal Coefficient", round(coef_season, 3), "Volatility of seasonal pattern"],
        ["Peak Month", df_seas.loc[df_seas["Season_Index"].idxmax(), "Month"], "Highest relative risk"],
        ["Trough Month", df_seas.loc[df_seas["Season_Index"].idxmin(), "Month"], "Lowest relative risk"]
    ], columns=["Metric", "Value", "Interpretation"])

    return df_seas, summary


def build_formula_examples():
    rows = [
        ["Purpose", "Excel Formula Example", "Interpretation"],
        ["Mean", "=AVERAGE(B2:B13)", "Baseline delinquency"],
        ["Season Index", "=B2/$B$14", ">1 worse month, <1 better"],
        ["3M Moving Avg", "=AVERAGE(B2:B4)", "Short smoothing"],
        ["6M Moving Avg", "=AVERAGE(B2:B7)", "Medium smoothing"],
        ["MoM Change", "=B3-B2", "Acceleration/slowdown"],
        ["Lag12 Corr", "=CORREL(B2:B13,B14:B25)", "Annual seasonality strength"],
        ["Amplitude", "=MAX(C2:C13)-MIN(C2:C13)", "Size of seasonal swing"]
    ]
    return pd.DataFrame(rows)


# -------------------- METRICS ENGINE --------------------
def build_excel_metrics(dpd_series):
    dpd = dpd_series.values.astype(float)

    metrics = [
        ["Mean DPD", round(np.mean(dpd),2), "Average delinquency"],
        ["Median DPD", int(np.median(dpd)), "Middle value"],
        ["Std Deviation", round(np.std(dpd,ddof=1),2), "Volatility"],
        ["Skewness", round(calc_skew(dpd),2), "Right tail risk"],
        ["Trend Slope", round(calc_trend_slope(dpd),2), "Up/down momentum"],
        ["Autocorr Lag 1",
         round(np.corrcoef(dpd[:-1],dpd[1:])[0,1],2) if len(dpd)>1 else 0,
         "Short-term persistence"]
    ]

    return pd.DataFrame(metrics, columns=["Metric","Value","Interpretation"])


# -------------------- ANALYSIS --------------------
def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)

    max_dpd = dpd.max()
    max_month = df.loc[df["DPD"].idxmax(),"Month"]

    metrics = {
        "Mean DPD": round(np.mean(dpd),2),
        "Max DPD": int(max_dpd),
        "Trend Slope": round(calc_trend_slope(dpd),2)
    }

    return df, max_dpd, max_month, metrics


# -------------------- CHART --------------------
def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10,3.5))
    ax.plot(df["Month"], df["DPD"], marker="o")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--")
    ax.plot(max_month, max_dpd, "r*", markersize=14)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig


# -------------------- APP --------------------
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
        doc = SimpleDocTemplate(pdf_buf, pagesize=letter)
        story = []

        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:

            build_formula_examples().to_excel(writer, "FORMULAS_EXAMPLE", index=False)

            tabs = st.tabs([str(c) for c in codes])

            for tab, code in zip(tabs, codes):

                row = raw[raw.iloc[:,0]==code].iloc[0]

                df, max_dpd, max_month, metrics = analyze(row, months)

                # seasonality
                seas_df, seas_summary = build_seasonality(df)

                df.to_excel(writer, f"DATA_{code}", index=False)
                build_excel_metrics(df["DPD"]).to_excel(writer, f"METRICS_{code}", index=False)
                seas_df.to_excel(writer, f"SEASONALITY_{code}", index=False)
                seas_summary.to_excel(writer, f"SEASONAL_SUMMARY_{code}", index=False)

                with tab:
                    st.subheader(f"Account {code}")
                    st.table(pd.DataFrame(metrics.items(), columns=["Metric","Value"]))
                    st.pyplot(plot_chart(df,max_dpd,max_month))

        st.sidebar.download_button("📊 Download Excel", excel_buf.getvalue(), "Risk_Metrics.xlsx")
        st.sidebar.download_button("📦 Download PDF", pdf_buf.getvalue(), "Risk_Report.pdf")
