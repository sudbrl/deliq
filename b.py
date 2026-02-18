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

    st.title("🛡️ Risk Intelligence Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Sign In"):
        if username in st.secrets.get("passwords", {}) and password == st.secrets["passwords"][username]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid credentials")

    return False


# -------------------- SAFE STAT FUNCTIONS --------------------
def calc_skew(x):
    x = np.asarray(x, dtype=float)
    if len(x) < 3:
        return 0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 3) if s != 0 else 0


def calc_kurtosis(x):
    x = np.asarray(x, dtype=float)
    if len(x) < 4:
        return 0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 4) if s != 0 else 0


def calc_mode(x):
    s = pd.Series(x).dropna()
    if len(s) == 0:
        return 0
    modes = s.mode()
    if len(modes) == 1:
        return modes.iloc[0]
    return list(modes.values)


def calc_trend_slope(y):
    y = np.asarray(y, dtype=float)
    if len(y) < 2:
        return 0
    x = np.arange(len(y))
    return np.polyfit(x, y, 1)[0]


# -------------------- SEASONALITY --------------------
def calc_monthly_avg(dpd, months):
    month_data = {}
    for i, m in enumerate(months):
        try:
            month_num = int(str(m).split("-")[1])
        except:
            month_num = (i % 12) + 1
        month_data.setdefault(month_num, []).append(dpd[i])
    return {k: np.mean(v) for k, v in month_data.items()}


def calc_seasonality_index(dpd, months):
    monthly_avg = calc_monthly_avg(dpd, months)
    overall_avg = np.mean(list(monthly_avg.values())) if monthly_avg else 0
    return {k: (v / overall_avg * 100) if overall_avg > 0 else 100
            for k, v in monthly_avg.items()}


def calc_seasonal_strength(dpd, months):
    monthly_avg = calc_monthly_avg(dpd, months)
    if len(monthly_avg) < 2:
        return 0
    values = list(monthly_avg.values())
    return np.std(values) / np.mean(values) if np.mean(values) > 0 else 0


# -------------------- CURE METRICS --------------------
def calc_cure_metrics(dpd_series):
    dpd = dpd_series.values.astype(float)
    n = len(dpd)

    hard_cures = 0
    episodes = 0
    ttc_list = []
    sustained_cures = 0
    recurrences = 0

    i = 0
    while i < n:
        if dpd[i] > 0:
            episodes += 1
            start = i
            while i < n and dpd[i] > 0:
                i += 1
            if i < n and dpd[i] == 0:
                hard_cures += 1
                ttc_list.append(i - start)

                if i + 3 <= n and np.all(dpd[i:i+3] == 0):
                    sustained_cures += 1

                if i + 3 <= n and np.any(dpd[i:i+3] > 0):
                    recurrences += 1
        else:
            i += 1

    return {
        "Hard Cures": hard_cures,
        "Episodes": episodes,
        "Cure Rate": round(hard_cures / episodes, 3) if episodes > 0 else 0,
        "Avg TTC": round(np.mean(ttc_list), 2) if ttc_list else 0,
        "Sustained Cures (3M)": sustained_cures,
        "Recurrence Ratio (3M)": round(recurrences / hard_cures, 3) if hard_cures > 0 else 0
    }


# -------------------- METRICS ENGINE --------------------
def build_excel_metrics(dpd_series, months):

    dpd = np.nan_to_num(dpd_series.values.astype(float), nan=0.0)
    cure_metrics = calc_cure_metrics(pd.Series(dpd))

    seasonality_idx = calc_seasonality_index(dpd, months)
    seasonal_strength = calc_seasonal_strength(dpd, months)

    peak_month = max(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0
    trough_month = min(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0

    metrics = [

        ["Mean DPD", round(np.mean(dpd), 2), "Average delinquency"],
        ["Median DPD", round(np.median(dpd), 2), "50th percentile"],
        ["Mode DPD", calc_mode(dpd), "Most frequent value(s)"],
        ["Min DPD", int(np.min(dpd)), "Best month"],
        ["Max DPD", int(np.max(dpd)), "Worst month"],
        ["Std Deviation", round(np.std(dpd, ddof=1), 2), "Volatility"],
        ["Skewness", round(calc_skew(dpd), 2), "Right-tail risk"],
        ["Kurtosis", round(calc_kurtosis(dpd), 2), "Extreme clustering"],
        ["Delinquent Months", int((dpd > 0).sum()), "Months DPD > 0"],
        ["Proportion Delinquent", round((dpd > 0).mean(), 3), "Share delinquent"],
        ["Cumulative DPD", int(dpd.sum()), "Total exposure"],
        ["Trend Slope", round(calc_trend_slope(dpd), 3), "Monthly drift"],

        ["", "", ""],
        ["--- CURE DYNAMICS ---", "", ""],
        ["Hard Cures", cure_metrics["Hard Cures"], "DPD>0 → 0 transitions"],
        ["Delinquency Episodes", cure_metrics["Episodes"], "Contiguous delinquency runs"],
        ["Cure Rate", cure_metrics["Cure Rate"], "Cures / episodes"],
        ["Avg Time-to-Cure", cure_metrics["Avg TTC"], "Months to cure"],
        ["Sustained Cures (3M)", cure_metrics["Sustained Cures (3M)"], "3-month stability"],
        ["Recurrence Ratio (3M)", cure_metrics["Recurrence Ratio (3M)"], "Re-default within 3M"],

        ["", "", ""],
        ["--- SEASONALITY ---", "", ""],
        ["Seasonal Strength", round(seasonal_strength, 3), "Pattern dispersion"],
        ["Peak Month", peak_month, "Highest risk month"],
        ["Trough Month", trough_month, "Lowest risk month"]
    ]

    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])


# -------------------- ANALYSIS --------------------
def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)

    max_dpd = dpd.max()
    max_month = df.loc[df["DPD"].idxmax(), "Month"]

    return df, max_dpd, max_month


# -------------------- CHART --------------------
def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--")
    ax.plot(max_month, max_dpd, "r*", markersize=14)
    ax.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig


# -------------------- MAIN --------------------
if check_password():

    st.title("Credit Risk Analytics Dashboard")

    file = st.sidebar.file_uploader("Upload Portfolio Excel", type=["xlsx"])

    if file:
        raw = pd.read_excel(file)
        codes = raw.iloc[:, 0].unique()
        months = raw.columns[3:]

        excel_buf = BytesIO()

        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:

            tabs = st.tabs([f"Account {c}" for c in codes])

            for tab, code in zip(tabs, codes):
                row = raw[raw.iloc[:, 0] == code].iloc[0]
                df, max_dpd, max_month = analyze(row, months)

                df.to_excel(writer, f"DATA_{code}", index=False)
                build_excel_metrics(df["DPD"], months).to_excel(writer, f"METRICS_{code}", index=False)

                with tab:
                    st.pyplot(plot_chart(df, max_dpd, max_month))
                    st.dataframe(build_excel_metrics(df["DPD"], months), use_container_width=True)

        st.sidebar.download_button(
            "Download Excel Report",
            excel_buf.getvalue(),
            "Risk_Metrics_Report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
