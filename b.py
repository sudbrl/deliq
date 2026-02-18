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

    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    header, footer { visibility: hidden !important; }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: white; padding: 3rem; border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    }
    .stTextInput input { border: 1px solid #e2e8f0; padding: 10px; border-radius: 8px; }
    .stButton button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; padding: 12px; font-weight: bold; border-radius: 8px; width: 100%; transition: all 0.3s ease;
    }
    .stButton button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    st.write("")
    st.write("")
    st.write("")
    st.write("")
    st.write("")

    col1, col2, col3 = st.columns([1, 0.6, 1]) 

    with col2:
        st.markdown("<h1 style='text-align: center; color: #1e293b; margin-bottom: 0;'>🛡️ Risk Intel</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-top: 5px; margin-bottom: 30px;'>Enterprise Credit Analytics</p>", unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        
        st.write("") 
        
        if st.button("Sign In", use_container_width=True):
            if username in st.secrets.get("passwords", {}) and password == st.secrets["passwords"][username]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
        
        st.markdown("<div style='text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 20px;'>🔒 Secure Enterprise Access</div>", unsafe_allow_html=True)

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
    mode_result = pd.Series(x).mode()
    return mode_result.iloc[0] if len(mode_result) > 0 else 0

def calc_trend_slope(y):
    x = np.arange(len(y))
    x_mean = x.mean()
    y_mean = y.mean()
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)
    return num / den if den != 0 else 0

# -------------------- CURE DYNAMICS LOGIC --------------------
def calc_cure_metrics(dpd):
    dpd = np.array(dpd)
    n = len(dpd)
    hard_cures = 0
    episodes = 0
    ttc_list = []
    sustained_cures = 0
    recurrences = 0
    in_episode = False
    start_idx = -1
    
    for i in range(n):
        if dpd[i] > 0 and not in_episode:
            in_episode = True
            episodes += 1
            start_idx = i
        
        if in_episode and dpd[i] == 0:
            hard_cures += 1
            ttc_list.append(i - start_idx)
            in_episode = False
            # Lookahead for sustained/recurrence (3 month window)
            if i + 3 < n:
                if np.all(dpd[i+1:i+4] == 0): sustained_cures += 1
                if np.any(dpd[i+1:i+4] > 0): recurrences += 1
    
    return {
        "Hard Cures": hard_cures,
        "Episodes": episodes,
        "Cure Rate": round(hard_cures / episodes, 2) if episodes > 0 else 0,
        "Avg TTC": round(np.mean(ttc_list), 1) if ttc_list else 0,
        "Sustained Cures (3M)": sustained_cures,
        "Recurrence Ratio (3M)": round(recurrences / hard_cures, 2) if hard_cures > 0 else 0
    }

# -------------------- SEASONALITY FUNCTIONS --------------------
def calc_monthly_avg(dpd, months):
    month_data = {}
    for i, m in enumerate(months):
        month_str = str(m)
        month_num = int(month_str.split('-')[1]) if '-' in month_str else (i % 12) + 1
        if month_num not in month_data: month_data[month_num] = []
        month_data[month_num].append(dpd[i])
    return {k: np.mean(v) for k, v in month_data.items()}

def calc_seasonality_index(dpd, months):
    monthly_avg = calc_monthly_avg(dpd, months)
    overall_avg = np.mean(list(monthly_avg.values()))
    return {k: (v / overall_avg * 100) if overall_avg > 0 else 100 for k, v in monthly_avg.items()}

def calc_seasonal_strength(dpd, months):
    monthly_avg = calc_monthly_avg(dpd, months)
    if len(monthly_avg) < 2: return 0
    values = list(monthly_avg.values())
    return np.std(values) / np.mean(values) if np.mean(values) > 0 else 0

# -------------------- METRICS ENGINE --------------------
def build_excel_metrics(dpd_series, months):
    dpd = dpd_series.values.astype(float)
    seasonality_idx = calc_seasonality_index(dpd, months)
    seasonal_strength = calc_seasonal_strength(dpd, months)
    peak_month = max(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0
    trough_month = min(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0
    
    # Calculate Cures
    cure_metrics = calc_cure_metrics(dpd)
    
    metrics = [
        ["Mean DPD", round(np.mean(dpd), 2), "Average delinquency per month"],
        ["Median DPD", int(np.median(dpd)), "50% months below this value"],
        ["Max DPD", int(np.max(dpd)), "Worst performing month"],
        ["Std Deviation", round(np.std(dpd, ddof=1), 2), "Payment volatility measure"],
        ["Skewness", round(calc_skew(dpd), 2), "Right tail risk (>0 = outlier delays)"],
        ["Kurtosis", round(calc_kurtosis(dpd), 2), "Extreme event risk (>3 = fat tails)"],
        ["Cumulative DPD", int(dpd.sum()), "Total lifetime exposure"],
        ["Trend Slope (DPD/mo)", round(calc_trend_slope(dpd), 2), "Monthly change rate"],
        ["Autocorr Lag 1", round(np.corrcoef(dpd[:-1], dpd[1:])[0, 1], 2) if len(dpd) > 1 else 0, "Month-to-month persistence"],
        ["Sticky Bucket", "90+" if np.max(dpd) >= 90 else "60+" if np.max(dpd) >= 60 else "30+" if np.max(dpd) >= 30 else "Current", "Worst historical bucket"],
        ["", "", ""],
        # ---------------- CURE DYNAMICS ----------------
        ["--- CURE DYNAMICS ---", "", ""],
        ["Hard Cures", cure_metrics["Hard Cures"], "DPD>0 → DPD=0 transitions"],
        ["Delinquency Episodes", cure_metrics["Episodes"], "Contiguous DPD>0 sequences"],
        ["Cure Rate", cure_metrics["Cure Rate"], "Cures / episodes"],
        ["Avg Time-to-Cure", cure_metrics["Avg TTC"], "Months from start of episode to cure"],
        ["Sustained Cures (3M)", cure_metrics["Sustained Cures (3M)"], "3 consecutive zero months post cure"],
        ["Recurrence Ratio (3M)", cure_metrics["Recurrence Ratio (3M)"], "Re-default within 3 months"],
        ["", "", ""],
        ["--- SEASONALITY ---", "", ""],
        ["Seasonal Strength", round(seasonal_strength, 3), "Pattern strength (>0.3 = strong)"],
        ["Peak Season Month", peak_month, "Month with highest avg DPD"],
        ["Trough Season Month", trough_month, "Month with lowest avg DPD"],
        ["Peak Index", round(seasonality_idx.get(peak_month, 100), 1) if seasonality_idx else 100, "Peak vs average (100 = avg)"],
        ["Seasonal Amplitude", round(seasonality_idx.get(peak_month, 100) - seasonality_idx.get(trough_month, 100), 1) if seasonality_idx else 0, "Peak - Trough difference"],
    ]
    
    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

def build_seasonality_sheet(dpd_series, months):
    dpd = dpd_series.values.astype(float)
    monthly_avg = calc_monthly_avg(dpd, months)
    seasonality_idx = calc_seasonality_index(dpd, months)
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    data = []
    for month_num in range(1, 13):
        data.append({
            'Month_Num': month_num, 'Month_Name': month_names[month_num - 1],
            'Avg_DPD': round(monthly_avg.get(month_num, 0), 2),
            'Seasonality_Index': round(seasonality_idx.get(month_num, 100), 1)
        })
    return pd.DataFrame(data)

# -------------------- ANALYSIS --------------------
def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    max_dpd = dpd.max()
    max_month = df.loc[df["DPD"].idxmax(), "Month"]
    important_metrics = {
        "Mean DPD": round(np.mean(dpd), 2),
        "Max DPD": int(max_dpd),
        "Cumulative DPD": int(dpd.sum()),
        "Trend Slope": round(calc_trend_slope(dpd), 2),
        "Sticky Bucket": "90+" if max_dpd >= 90 else "60+" if max_dpd >= 60 else "30+" if max_dpd >= 30 else "Current"
    }
    return df, max_dpd, max_month, important_metrics

# -------------------- CHART --------------------
def plot_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", linewidth=2, label="DPD", color="#3b82f6")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", label="3M Rolling Avg", color="#8b5cf6")
    ax.plot(max_month, max_dpd, "r*", markersize=16)
    ax.set_ylabel("Days Past Due (DPD)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- PDF --------------------
def build_pdf(story, code, df, max_dpd, max_month, metrics):
    styles = getSampleStyleSheet()
    story.append(Paragraph(f"Loan Performance Report – Account {code}", ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16)))
    story.append(Spacer(1, 12))
    data = [["Metric", "Value"]] + [[k, v] for k, v in metrics.items()]
    t = Table(data, colWidths=[3*inch, 3*inch])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    story.append(t); story.append(Spacer(1, 12))
    fig_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plot_chart(df, max_dpd, max_month).savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(); story.append(Image(fig_path, 6.5*inch, 3.2*inch)); story.append(PageBreak())

# -------------------- MAIN APP --------------------
if check_password():
    st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    h1, h2, h3 { color: #1e293b; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px; padding: 12px 24px; }
    .stTabs [aria-selected="true"] { background-color: #3b82f6; color: white; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e293b 0%, #334155 100%); color: white; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stDownloadButton button {
        width: 100%; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); border: none; padding: 12px; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("# 🛡️ Risk Intelligence")
        file = st.file_uploader("Upload Portfolio Excel", type=["xlsx"])
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear(); st.rerun()

    st.title("📊 Credit Risk Analytics Dashboard")
    
    if file:
        try:
            raw = pd.read_excel(file)
            codes, months = raw.iloc[:, 0].unique(), raw.columns[3:]
            excel_buf, pdf_buf = BytesIO(), BytesIO()
            doc, story = SimpleDocTemplate(pdf_buf, pagesize=letter), []
            
            with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
                tabs = st.tabs([f"Account {c}" for c in codes])
                for tab, code in zip(tabs, codes):
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, max_dpd, max_month, metrics = analyze(row, months)
                    
                    # Excel Report Construction
                    df.to_excel(writer, f"DATA_{code}", index=False)
                    build_excel_metrics(df["DPD"], months).to_excel(writer, f"METRICS_{code}", index=False)
                    build_seasonality_sheet(df["DPD"], months).to_excel(writer, f"SEASON_{code}", index=False)
                    
                    with tab:
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            for k, v in metrics.items(): st.metric(k, v)
                        with col2: st.pyplot(plot_chart(df, max_dpd, max_month))
                        st.dataframe(build_excel_metrics(df["DPD"], months), use_container_width=True, hide_index=True)
                    build_pdf(story, code, df, max_dpd, max_month, metrics)
                
                # Definitions Sheet
                def_df = pd.DataFrame([
                    ["Hard Cures", "DPD > 0 → 0", "Account returns to 0 DPD from delinquency"],
                    ["Delinquency", "Contiguous DPD > 0", "Consecutive months with payments missed"],
                    ["Cure Rate", "Cures / Episodes", "Ratio of successful recoveries to delinquent events"],
                    ["Avg Time-to-Cure", "Months to reach 0 DPD", "Average duration to resolve a delinquency"],
                    ["Sustained Cure", "3-month stay at 0 DPD", "Verification of stable payment behavior"],
                    ["Recurrence", "Re-default after cure", "Account returns to >0 DPD after being cured"]
                ], columns=["Metric", "Logic", "Description"])
                def_df.to_excel(writer, "Definitions", index=False)

            doc.build(story)
            with st.sidebar:
                st.download_button("📊 Excel Report", excel_buf.getvalue(), "Risk_Report.xlsx")
                st.download_button("📄 PDF Report", pdf_buf.getvalue(), "Risk_Analysis.pdf")
        
        except Exception as e: st.error(f"❌ Error: {str(e)}")
    else: st.info("👆 Please upload an Excel file to begin")
