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

    # ✅ FIXED: Removed extra padding/space at top
    st.markdown("""
    <style>
    section.main > div {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    .block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    .stApp {
        background: radial-gradient(circle at top, #eef2ff, #f8fafc);
    }
    .login-wrapper {
        height: 100vh;
        display:flex;
        align-items:center;
        justify-content:center;
        margin-top: -3rem;
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

# ✅ NEW: Seasonality calculation functions
def calc_monthly_avg(dpd, months):
    """Calculate average DPD by calendar month"""
    month_data = {}
    for i, m in enumerate(months):
        month_num = int(str(m).split('-')[1]) if '-' in str(m) else (i % 12) + 1
        if month_num not in month_data:
            month_data[month_num] = []
        month_data[month_num].append(dpd[i])
    return {k: np.mean(v) for k, v in month_data.items()}

def calc_seasonality_index(dpd, months):
    """Calculate seasonality index for each month"""
    monthly_avg = calc_monthly_avg(dpd, months)
    overall_avg = np.mean(list(monthly_avg.values()))
    return {k: (v / overall_avg * 100) if overall_avg > 0 else 100 
            for k, v in monthly_avg.items()}

def calc_seasonal_strength(dpd, months):
    """Measure strength of seasonality (0-1 scale)"""
    monthly_avg = calc_monthly_avg(dpd, months)
    if len(monthly_avg) < 2:
        return 0
    values = list(monthly_avg.values())
    return np.std(values) / np.mean(values) if np.mean(values) > 0 else 0

# -------------------- METRICS ENGINE --------------------
def build_excel_metrics(dpd_series, months):
    dpd = dpd_series.values.astype(float)
    
    # ✅ Calculate seasonality metrics
    seasonality_idx = calc_seasonality_index(dpd, months)
    seasonal_strength = calc_seasonal_strength(dpd, months)
    peak_month = max(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0
    trough_month = min(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0
    
    metrics = [
        ["Mean DPD", round(np.mean(dpd),2), "Average delinquency per month", "=AVERAGE(DPD_Range)"],
        ["Median DPD", int(np.median(dpd)), "50% months below", "=MEDIAN(DPD_Range)"],
        ["Mode DPD", int(calc_mode(dpd)), "Most frequent", "=MODE.SNGL(DPD_Range)"],
        ["Min DPD", int(np.min(dpd)), "Best month", "=MIN(DPD_Range)"],
        ["Max DPD", int(np.max(dpd)), "Worst month", "=MAX(DPD_Range)"],
        ["Range", int(np.ptp(dpd)), "Spread (Max-Min)", "=MAX(DPD_Range)-MIN(DPD_Range)"],
        ["Std Deviation", round(np.std(dpd,ddof=1),2), "Volatility measure", "=STDEV.S(DPD_Range)"],
        ["Skewness", round(calc_skew(dpd),2), "Right tail risk (>0=right skew)", "=(AVERAGE((DPD-AVERAGE(DPD))^3))/(STDEV.S(DPD)^3)"],
        ["Kurtosis", round(calc_kurtosis(dpd),2), "Extreme events (>3=fat tails)", "=(AVERAGE((DPD-AVERAGE(DPD))^4))/(STDEV.S(DPD)^4)"],
        ["Delinquent Months", int((dpd>0).sum()), "Frequency of delays", "=COUNTIF(DPD_Range,\">0\")"],
        ["Proportion Delinquent", round((dpd>0).mean(),2), "Share delinquent", "=COUNTIF(DPD_Range,\">0\")/COUNT(DPD_Range)"],
        ["Cumulative DPD", int(dpd.sum()), "Total life exposure", "=SUM(DPD_Range)"],
        ["Trend Slope (DPD/mo)", round(calc_trend_slope(dpd),2), "Monthly momentum", "=SLOPE(DPD_Range,SEQUENCE(COUNT(DPD_Range)))"],
        ["Autocorr Lag 1", round(np.corrcoef(dpd[:-1],dpd[1:])[0,1],2) if len(dpd)>1 else 0, "Month-to-month persistence", "=CORREL(B2:B13,B3:B14)"],
        ["Prob 90+ DPD", round((dpd>=90).mean(),3), "Severe delinquency risk", "=COUNTIF(DPD_Range,\">=90\")/COUNT(DPD_Range)"],
        ["Coeff of Variation", round(np.std(dpd)/np.mean(dpd),2) if np.mean(dpd)>0 else 0, "Relative volatility", "=STDEV.S(DPD_Range)/AVERAGE(DPD_Range)"],
        ["Sticky Bucket", "90+" if np.max(dpd)>=90 else "60+" if np.max(dpd)>=60 else "30+", "Historical severity class", "=IF(MAX(DPD_Range)>=90,\"90+\",IF(MAX(DPD_Range)>=60,\"60+\",\"30+\"))"],
        # ✅ NEW: Seasonality Indicators
        ["", "", "", ""],  # Separator
        ["--- SEASONALITY INDICATORS ---", "", "", ""],
        ["Seasonal Strength", round(seasonal_strength, 3), "0-1 scale: >0.3=strong pattern", "=STDEV(Monthly_Avg)/AVERAGE(Monthly_Avg)"],
        ["Peak Season Month", peak_month, "Month with highest avg DPD", "See SEASONALITY sheet"],
        ["Trough Season Month", trough_month, "Month with lowest avg DPD", "See SEASONALITY sheet"],
        ["Peak Index", round(seasonality_idx.get(peak_month, 100), 1) if seasonality_idx else 100, "Index: 100=average, >100=above", "=(Monthly_Avg/Overall_Avg)*100"],
        ["Trough Index", round(seasonality_idx.get(trough_month, 100), 1) if seasonality_idx else 100, "Index: 100=average, <100=below", "=(Monthly_Avg/Overall_Avg)*100"],
        ["Seasonal Amplitude", round(seasonality_idx.get(peak_month, 100) - seasonality_idx.get(trough_month, 100), 1) if seasonality_idx else 0, "Peak-Trough difference", "=Peak_Index-Trough_Index"],
    ]
    
    return pd.DataFrame(metrics, columns=["Metric","Value","Interpretation","Excel_Formula"])

def build_seasonality_sheet(dpd_series, months):
    """Create detailed seasonality breakdown by calendar month"""
    dpd = dpd_series.values.astype(float)
    monthly_avg = calc_monthly_avg(dpd, months)
    seasonality_idx = calc_seasonality_index(dpd, months)
    
    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    
    data = []
    for month_num in range(1, 13):
        avg_dpd = monthly_avg.get(month_num, 0)
        index = seasonality_idx.get(month_num, 100)
        interpretation = "Above average" if index > 110 else "Below average" if index < 90 else "Normal"
        
        data.append({
            'Month_Num': month_num,
            'Month_Name': month_names[month_num-1],
            'Avg_DPD': round(avg_dpd, 2),
            'Seasonality_Index': round(index, 1),
            'Interpretation': interpretation,
            'Formula_Avg': f'=AVERAGEIF(Month_Column,{month_num},DPD_Column)',
            'Formula_Index': f'=(Avg_DPD/AVERAGE(All_Months_Avg))*100'
        })
    
    return pd.DataFrame(data)

# -------------------- ANALYSIS --------------------
def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    
    max_dpd = dpd.max()
    max_month = df.loc[df["DPD"].idxmax(),"Month"]
    
    important_metrics = {
        "Mean DPD": round(np.mean(dpd),2),
        "Max DPD": int(max_dpd),
        "Cumulative DPD": int(dpd.sum()),
        "Trend Slope": round(calc_trend_slope(dpd),2),
        "Sticky Bucket": "90+" if max_dpd>=90 else "60+" if max_dpd>=60 else "30+"
    }
    
    return df, max_dpd, max_month, important_metrics

# -------------------- CHART --------------------
def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10,3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", label="3M Rolling Avg")
    ax.plot(max_month, max_dpd, "r*", markersize=14)
    ax.text(max_month, max_dpd+3, f"MAX {int(max_dpd)}", ha="center", color="red")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- PDF --------------------
def build_pdf(story, code, df, max_dpd, max_month, metrics):
    styles = getSampleStyleSheet()
    story.append(Paragraph(
        f"Loan Performance – {code}",
        ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, leading=18)))
    story.append(Spacer(1,12))
    
    # Important metrics table
    data = [["Metric","Value"]]+[[k,v] for k,v in metrics.items()]
    t = Table(data, colWidths=[3*inch,3*inch])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#1e3a8a")),
                           ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                           ('GRID',(0,0),(-1,-1),0.5,colors.grey),
                           ('FONTSIZE',(0,0),(-1,-1),10),
                           ('ALIGN',(0,0),(-1,-1),'CENTER')]))
    story.append(t)
    story.append(Spacer(1,12))
    
    # Chart
    fig_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plot_chart(df,max_dpd,max_month).savefig(fig_path,dpi=150,bbox_inches="tight")
    plt.close()
    story.append(Image(fig_path,6.5*inch,3.2*inch))
    story.append(PageBreak())

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
            tabs = st.tabs([str(c) for c in codes])
            
            for tab, code in zip(tabs, codes):
                row = raw[raw.iloc[:,0]==code].iloc[0]
                df, max_dpd, max_month, metrics = analyze(row, months)
                
                # ✅ Excel: Data + Metrics + Seasonality sheets
                df.to_excel(writer, f"DATA_{code}", index=False)
                build_excel_metrics(df["DPD"], months).to_excel(writer, f"METRICS_{code}", index=False)
                build_seasonality_sheet(df["DPD"], months).to_excel(writer, f"SEASONALITY_{code}", index=False)
                
                # Screen
                with tab:
                    st.subheader(f"Account {code}")
                    st.table(pd.DataFrame(metrics.items(), columns=["Metric","Value"]))
                    st.pyplot(plot_chart(df,max_dpd,max_month))
                
                # PDF
                build_pdf(story, code, df, max_dpd, max_month, metrics)
        
        doc.build(story)
        
        st.sidebar.download_button("📊 Download Excel", excel_buf.getvalue(), "Risk_Metrics.xlsx")
        st.sidebar.download_button("📦 Download PDF", pdf_buf.getvalue(), "Risk_Report.pdf")
