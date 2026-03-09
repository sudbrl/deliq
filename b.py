import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Rectangle
from io import BytesIO
import tempfile
import os

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
        color: white; border: none; padding: 12px; font-weight: bold; border-radius: 8px; width: 100%;
    }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    st.write("")
    st.write("")
    col1, col2, col3 = st.columns([1, 0.6, 1]) 

    with col2:
        st.markdown("<h1 style='text-align: center; color: #1e293b; margin-bottom: 0;'>🛡️ Risk Intel</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-top: 5px; margin-bottom: 30px;'>Enterprise Credit Analytics</p>", unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        
        if st.button("Sign In", use_container_width=True):
            if username in st.secrets.get("passwords", {}) and password == st.secrets["passwords"][username]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
        st.markdown("<div style='text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 20px;'>🔒 Secure Enterprise Access</div>", unsafe_allow_html=True)

    return False

# -------------------- HELPER FUNCTION TO FILTER VALID VALUES --------------------
def filter_valid_dpd(dpd_series):
    """Filter out #N/A and keep only numeric values (0 or more)"""
    # Convert to numeric, coercing errors to NaN
    numeric_series = pd.to_numeric(dpd_series, errors='coerce')
    # Filter out NaN values and return valid data
    valid_data = numeric_series[numeric_series.notna()]
    return valid_data

# -------------------- ORIGINAL STAT FUNCTIONS --------------------
def calc_skew(x):
    if len(x) == 0:
        return 0
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 3) if s != 0 else 0

def calc_kurtosis(x):
    if len(x) == 0:
        return 0
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 4) if s != 0 else 0

def calc_mode(x):
    if len(x) == 0:
        return 0
    mode_result = pd.Series(x).mode()
    return mode_result.iloc[0] if len(mode_result) > 0 else 0

def calc_trend_slope(y):
    if len(y) == 0:
        return 0
    x = np.arange(len(y))
    x_mean, y_mean = x.mean(), y.mean()
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)
    return num / den if den != 0 else 0

# -------------------- ORIGINAL SEASONALITY FUNCTIONS --------------------
def calc_monthly_avg(dpd, months):
    month_data = {}
    for i, m in enumerate(months):
        month_str = str(m)
        month_num = int(month_str.split('-')[1]) if '-' in month_str and month_str.split('-')[1].isdigit() else (i % 12) + 1
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

# -------------------- ORIGINAL METRICS ENGINE (FIXED) --------------------
def build_excel_metrics(dpd_series, months):
    # Filter valid DPD values
    valid_dpd = filter_valid_dpd(dpd_series)
    
    if len(valid_dpd) == 0:
        # Return empty metrics if no valid data
        return pd.DataFrame([["No valid data", "", ""]], columns=["Metric", "Value", "Interpretation"])
    
    dpd = valid_dpd.values.astype(float)
    
    # FIX: The index already contains month names directly, no need for lookup
    valid_months = valid_dpd.index.tolist()
    
    seasonality_idx = calc_seasonality_index(dpd, valid_months)
    seasonal_strength = calc_seasonal_strength(dpd, valid_months)
    peak_month = max(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0
    trough_month = min(seasonality_idx, key=seasonality_idx.get) if seasonality_idx else 0
    
    metrics = [
        ["Mean DPD", round(np.mean(dpd), 2), "Average delinquency per month"],
        ["Median DPD", int(np.median(dpd)), "50% months below this value"],
        ["Mode DPD", int(calc_mode(dpd)), "Most frequent DPD value"],
        ["Min DPD", int(np.min(dpd)), "Best performing month"],
        ["Max DPD", int(np.max(dpd)), "Worst performing month"],
        ["Range", int(np.ptp(dpd)), "Max - Min spread"],
        ["Std Deviation", round(np.std(dpd, ddof=1), 2), "Payment volatility measure"],
        ["Skewness", round(calc_skew(dpd), 2), "Right tail risk (>0 = outlier delays)"],
        ["Kurtosis", round(calc_kurtosis(dpd), 2), "Extreme event risk (>3 = fat tails)"],
        ["Delinquent Months", int((dpd > 0).sum()), "Number of months with delays"],
        ["Proportion Delinquent", round((dpd > 0).mean(), 2), "% of months delinquent"],
        ["Cumulative DPD", int(dpd.sum()), "Total lifetime exposure"],
        ["Trend Slope (DPD/mo)", round(calc_trend_slope(dpd), 2), "Monthly change rate"],
        ["Autocorr Lag 1", round(np.corrcoef(dpd[:-1], dpd[1:])[0, 1], 2) if len(dpd) > 1 else 0, "Month-to-month persistence"],
        ["Prob 90+ DPD", round((dpd >= 90).mean(), 3), "Severe delinquency probability"],
        ["Coeff of Variation", round(np.std(dpd) / np.mean(dpd), 2) if np.mean(dpd) > 0 else 0, "Relative volatility"],
        ["Sticky Bucket", "90+" if np.max(dpd) >= 90 else "60+" if np.max(dpd) >= 60 else "30+" if np.max(dpd) >= 30 else "Current", "Worst historical bucket"],
        ["", "", ""],
        ["--- SEASONALITY ---", "", ""],
        ["Seasonal Strength", round(seasonal_strength, 3), "Pattern strength (>0.3 = strong)"],
        ["Peak Season Month", peak_month, "Month with highest avg DPD"],
        ["Trough Season Month", trough_month, "Month with lowest avg DPD"],
        ["Peak Index", round(seasonality_idx.get(peak_month, 100), 1) if seasonality_idx else 100, "Peak vs average (100 = avg)"],
        ["Trough Index", round(seasonality_idx.get(trough_month, 100), 1) if seasonality_idx else 100, "Trough vs average (100 = avg)"],
        ["Seasonal Amplitude", round(seasonality_idx.get(peak_month, 100) - seasonality_idx.get(trough_month, 100), 1) if seasonality_idx else 0, "Peak - Trough difference"],
    ]
    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

# -------------------- INFOGRAPHIC CHART LOGIC (MODIFIED TO EXCLUDE #N/A) --------------------
def generate_delinquency_infographic(excel_file_path):
    df = pd.read_excel(excel_file_path)
    month_columns = df.columns[3:].tolist()
    
    fig = plt.figure(figsize=(20, 11), dpi=150)
    fig.patch.set_facecolor('#2b2b2b')
    ax = fig.add_subplot(111)
    ax.set_facecolor('#1e1e1e')
    
    colors = ['#00d4ff', '#ff006e', '#06ffa5', '#ffbe0b']
    loan_info = []
    
    for idx, (_, row) in enumerate(df.iterrows()):
        loan_type = row.iloc[0]
        balance = row.iloc[2]
        
        # Filter valid DPD values (exclude #N/A)
        dpd_raw = [row[m] for m in month_columns]
        valid_data = []
        valid_positions = []
        valid_months = []
        
        for i, (m, dpd_val) in enumerate(zip(month_columns, dpd_raw)):
            # Convert to numeric, skip if NaN or not numeric
            numeric_val = pd.to_numeric(dpd_val, errors='coerce')
            if pd.notna(numeric_val):
                valid_data.append(float(numeric_val))
                valid_positions.append(i)
                valid_months.append(m)
        
        if not valid_data:
            continue
        
        color = colors[idx % len(colors)]
        
        # Plot with glow effect
        for glow in [8, 6, 4, 2]:
            ax.plot(valid_positions, valid_data, color=color, linewidth=glow, alpha=0.15, zorder=1)
        
        ax.plot(valid_positions, valid_data, color=color, linewidth=3, label=loan_type, marker='o', 
                markersize=5, markerfacecolor=color, markeredgecolor='#2b2b2b', markeredgewidth=2, zorder=3)
        
        max_dpd = max(valid_data)
        max_idx_in_valid = valid_data.index(max_dpd)
        max_position = valid_positions[max_idx_in_valid]
        max_month_label = valid_months[max_idx_in_valid]
        
        loan_info.append({'type': loan_type, 'balance': balance, 'max_dpd': int(max_dpd), 'max_month': max_month_label, 'color': color})
        
        ax.plot(max_position, max_dpd, 'o', color=color, markersize=12, markeredgecolor='white', markeredgewidth=3, zorder=6)
        ax.annotate(f'{int(max_dpd)} DAYS\n{max_month_label}', xy=(max_position, max_dpd), xytext=(20, 20), textcoords='offset points',
                    fontsize=10, fontweight='bold', bbox=dict(boxstyle='round,pad=0.8', facecolor='#2b2b2b', alpha=0.95, edgecolor=color, linewidth=3),
                    color=color, arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2', color=color, lw=3), zorder=8)

    ax.grid(True, alpha=0.15, linestyle='-', linewidth=1.5, color='#00d4ff')
    for spine in ax.spines.values(): spine.set_visible(False)
    ax.set_xlabel('LOAN PERIOD', fontsize=15, fontweight='bold', color='#00d4ff', labelpad=15)
    ax.set_ylabel('DAYS PAST DUE (DPD)', fontsize=15, fontweight='bold', color='#00d4ff', labelpad=15)
    fig.text(0.5, 0.96, 'LOAN DELINQUENCY INFOGRAPHIC', fontsize=24, fontweight='bold', color='white', ha='center')
    ax.set_xticks(range(len(month_columns)))
    ax.set_xticklabels(month_columns, rotation=45, ha='right', fontsize=9, color='#a8dadc', fontweight='bold')
    ax.tick_params(axis='both', colors='#a8dadc')

    # Status Panel
    panel = Rectangle((0.77, 0.15), 0.21, 0.65, transform=fig.transFigure, facecolor='#0f0f0f', alpha=0.95, edgecolor='#00d4ff', linewidth=3, zorder=10)
    fig.add_artist(panel)
    fig.text(0.875, 0.77, 'PORTFOLIO STATUS', fontsize=14, fontweight='bold', color='white', ha='center', transform=fig.transFigure, zorder=11)
    
    y_off = 0.69
    for info in loan_info:
        fig.text(0.79, y_off, f"● {info['type']}", fontsize=10, fontweight='bold', color=info['color'], transform=fig.transFigure, zorder=11)
        y_off -= 0.03
        fig.text(0.79, y_off, f"BALANCE: Rs. {info['balance']:,.0f}", fontsize=8, color='#a8dadc', transform=fig.transFigure, zorder=11)
        y_off -= 0.025
        fig.text(0.79, y_off, f"PEAK: {info['max_dpd']} days", fontsize=9, fontweight='bold', color=info['color'], transform=fig.transFigure, zorder=11)
        y_off -= 0.05

    plt.subplots_adjust(left=0.06, right=0.75, top=0.89, bottom=0.15)
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, facecolor='#2b2b2b')
    plt.close()
    return buf.getvalue()

# -------------------- ORIGINAL ANALYSIS & SIMPLE CHART (MODIFIED TO EXCLUDE #N/A) --------------------
def analyze(row, months):
    # Filter valid DPD values
    dpd_raw = row[months]
    dpd_numeric = pd.to_numeric(dpd_raw, errors='coerce')
    
    # Create dataframe with only valid data points
    valid_mask = dpd_numeric.notna()
    valid_months = months[valid_mask]
    valid_dpd = dpd_numeric[valid_mask].astype(float)
    
    if len(valid_dpd) == 0:
        # Return empty results if no valid data
        df = pd.DataFrame({"Month": [], "DPD": [], "Rolling_3M": []})
        return df, 0, "", {"Mean DPD": 0, "Max DPD": 0, "Cumulative DPD": 0, "Trend Slope": 0, "Sticky Bucket": "No Data"}
    
    df = pd.DataFrame({"Month": valid_months.astype(str), "DPD": valid_dpd.values})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    
    max_dpd = valid_dpd.max()
    max_month = df.loc[df["DPD"].idxmax(), "Month"]
    
    metrics = {
        "Mean DPD": round(np.mean(valid_dpd), 2), 
        "Max DPD": int(max_dpd), 
        "Cumulative DPD": int(valid_dpd.sum()),
        "Trend Slope": round(calc_trend_slope(valid_dpd.values), 2), 
        "Sticky Bucket": "90+" if max_dpd >= 90 else "60+" if max_dpd >= 60 else "30+" if max_dpd >= 30 else "Current"
    }
    
    return df, max_dpd, max_month, metrics

def plot_chart(df, max_dpd, max_month):
    if len(df) == 0:
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.text(0.5, 0.5, "No valid data to display", ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        plt.tight_layout()
        return fig
    
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", linewidth=2, color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", linewidth=1.5, color="#8b5cf6", label="3M Rolling Avg")
    
    # Only plot max marker if max_dpd > 0
    if max_dpd > 0:
        ax.plot(max_month, max_dpd, "r*", markersize=16)
        ax.text(max_month, max_dpd + 5, f"MAX {int(max_dpd)}", ha="center", color="red", fontweight="bold")
    
    ax.set_ylabel("DPD")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- MAIN APP --------------------
if check_password():
    st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
        color: white;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: white !important;
    }

    /* DOWNLOAD BUTTONS AND LOGOUT BUTTON (Matched Blue Gradient) */
    [data-testid="stSidebar"] .stDownloadButton button, [data-testid="stSidebar"] .stButton button {
        width: 100%;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
        color: white !important;
        font-weight: 600;
        border: none;
        padding: 12px;
        border-radius: 8px;
    }
    
    [data-testid="stSidebar"] [data-testid="stFileUploader"] { 
        background-color: rgba(255, 255, 255, 0.05); 
        border: 1px dashed rgba(255, 255, 255, 0.3); 
        padding: 1rem; 
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button { 
        color: #1e293b !important; 
        background-color: white !important; 
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("# 🛡️ Risk Intelligence")
        st.markdown("---")
        file = st.file_uploader("Upload Portfolio Excel", type=["xlsx"])
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title("📊 Credit Risk Analytics Dashboard")
    
    if file:
        try:
            raw = pd.read_excel(file)
            codes = raw.iloc[:, 0].unique()
            months = raw.columns[3:]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name
            infographic_png = generate_delinquency_infographic(tmp_path)
            os.remove(tmp_path)

            excel_buf = BytesIO()
            with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
                tabs = st.tabs([f"Account {c}" for c in codes])
                for tab, code in zip(tabs, codes):
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, max_dpd, max_month, metrics = analyze(row, months)
                    
                    df.to_excel(writer, f"DATA_{code}", index=False)
                    
                    # Get valid DPD for metrics
                    dpd_series = pd.to_numeric(row[months], errors='coerce')
                    build_excel_metrics(dpd_series, months).to_excel(writer, f"METRICS_{code}", index=False)
                    
                    with tab:
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.markdown("#### 📈 Key Metrics")
                            for k, v in metrics.items(): st.metric(k, v)
                        with col2:
                            st.pyplot(plot_chart(df, max_dpd, max_month))
                        st.markdown("#### 📋 Complete Risk Metrics")
                        st.dataframe(build_excel_metrics(dpd_series, months), use_container_width=True, hide_index=True)

            with st.sidebar:
                st.markdown("### 💾 Downloads")
                st.download_button("📊 Excel Report", excel_buf.getvalue(), "Risk_Metrics_Report.xlsx", use_container_width=True)
                st.write("")
                st.download_button("🖼️ Infographic PNG", infographic_png, "Portfolio_Infographic.png", "image/png", use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    else:
        st.info("👆 Please upload an Excel file in the sidebar to begin analysis")
