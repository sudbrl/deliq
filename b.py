import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Rectangle
import os
import tempfile
from io import BytesIO

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

# -------------------- ANALYTICS HELPERS --------------------
def calc_skew(x):
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 3) if s != 0 else 0

def calc_kurtosis(x):
    m, s = np.mean(x), np.std(x, ddof=1)
    return np.mean(((x - m) / s) ** 4) if s != 0 else 0

def calc_trend_slope(y):
    x = np.arange(len(y))
    x_mean, y_mean = x.mean(), y.mean()
    num = np.sum((x - x_mean) * (y - y_mean))
    den = np.sum((x - x_mean) ** 2)
    return num / den if den != 0 else 0

# -------------------- INFOGRAPHIC CHART ENGINE --------------------
def generate_delinquency_chart_bytes(excel_file_path):
    """Generates the professional dark-themed PNG and returns it as bytes."""
    df = pd.read_excel(excel_file_path)
    month_columns = df.columns[3:].tolist()
    
    fig = plt.figure(figsize=(20, 11), dpi=150)
    fig.patch.set_facecolor('#2b2b2b')
    ax = fig.add_subplot(111)
    ax.set_facecolor('#1e1e1e')
    
    colors = ['#00d4ff', '#ff006e', '#06ffa5', '#ffbe0b', '#8b5cf6', '#ec4899']
    loan_info = []
    
    for idx, (_, row) in enumerate(df.iterrows()):
        loan_type = row.iloc[0] # Ac Type Desc
        balance = row.iloc[2]   # Balance
        dpd_values = row[month_columns].astype(float).fillna(0).tolist()
        month_positions = list(range(len(month_columns)))
        
        color = colors[idx % len(colors)]
        
        if dpd_values:
            for glow in [8, 6, 4, 2]:
                ax.plot(month_positions, dpd_values, color=color, linewidth=glow, alpha=0.15, zorder=1)
            
            ax.plot(month_positions, dpd_values, color=color, linewidth=3, label=str(loan_type), 
                    marker='o', markersize=5, markerfacecolor=color, markeredgecolor='#2b2b2b', 
                    markeredgewidth=2, zorder=3)
            
            max_dpd = max(dpd_values)
            max_idx = dpd_values.index(max_dpd)
            
            loan_info.append({'type': loan_type, 'balance': balance, 'max_dpd': int(max_dpd), 
                              'max_month': month_columns[max_idx], 'color': color})
            
            ax.plot(max_idx, max_dpd, 'o', color=color, markersize=12, markeredgecolor='white', markeredgewidth=3, zorder=6)
            ax.annotate(f'{int(max_dpd)} DAYS\n{month_columns[max_idx]}', xy=(max_idx, max_dpd),
                        xytext=(20, 20), textcoords='offset points', fontsize=10, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.8', facecolor='#2b2b2b', alpha=0.95, edgecolor=color, linewidth=3),
                        color=color, arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2', color=color, lw=3), zorder=8)

    ax.grid(True, alpha=0.15, linestyle='-', linewidth=1.5, color='#00d4ff')
    for spine in ax.spines.values(): spine.set_visible(False)
    
    ax.set_xlabel('LOAN PERIOD', fontsize=15, fontweight='bold', color='#00d4ff', labelpad=15)
    ax.set_ylabel('DAYS PAST DUE (DPD)', fontsize=15, fontweight='bold', color='#00d4ff', labelpad=15)
    fig.text(0.5, 0.96, 'LOAN DELINQUENCY INFOGRAPHIC', fontsize=24, fontweight='bold', color='white', ha='center')
    
    ax.set_xticks(range(len(month_columns)))
    ax.set_xticklabels(month_columns, rotation=45, ha='right', fontsize=9, color='#a8dadc', fontweight='bold')
    ax.tick_params(axis='both', colors='#a8dadc')

    # Portfolio Panel
    panel = Rectangle((0.77, 0.15), 0.21, 0.65, transform=fig.transFigure, facecolor='#0f0f0f', alpha=0.95, edgecolor='#00d4ff', linewidth=3, zorder=10)
    fig.add_artist(panel)
    fig.text(0.875, 0.77, 'PORTFOLIO STATUS', fontsize=14, fontweight='bold', color='white', ha='center', transform=fig.transFigure, zorder=11)
    
    y_off = 0.69
    for info in loan_info[:8]: # Limit display to first 8 for space
        fig.text(0.79, y_off, f"● {info['type']}", fontsize=9, fontweight='bold', color=info['color'], transform=fig.transFigure, zorder=11)
        fig.text(0.79, y_off-0.025, f"Balance: Rs.{info['balance']:,.0f} | Peak: {info['max_dpd']}d", fontsize=8, color='white', transform=fig.transFigure, zorder=11)
        y_off -= 0.06

    plt.subplots_adjust(left=0.06, right=0.75, top=0.89, bottom=0.15)
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, facecolor='#2b2b2b')
    plt.close()
    return buf.getvalue()

# -------------------- METRICS ENGINE --------------------
def build_excel_metrics(dpd_series, months):
    dpd = dpd_series.values.astype(float)
    metrics = [
        ["Mean DPD", round(np.mean(dpd), 2), "Average delinquency"],
        ["Max DPD", int(np.max(dpd)), "Worst performing month"],
        ["Std Deviation", round(np.std(dpd, ddof=1), 2), "Volatility"],
        ["Skewness", round(calc_skew(dpd), 2), "Right tail risk"],
        ["Trend Slope", round(calc_trend_slope(dpd), 2), "Monthly change rate"],
        ["Sticky Bucket", "90+" if np.max(dpd) >= 90 else "60+" if np.max(dpd) >= 60 else "30+" if np.max(dpd) >= 30 else "Current", "Worst bucket"]
    ]
    return pd.DataFrame(metrics, columns=["Metric", "Value", "Interpretation"])

def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    return df, dpd.max(), df.loc[df["DPD"].idxmax(), "Month"], {
        "Mean DPD": round(np.mean(dpd), 2), "Max DPD": int(dpd.max()), "Trend": round(calc_trend_slope(dpd), 2)
    }

def plot_simple_chart(df, max_dpd, max_month):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", linewidth=2, color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], "--", color="#8b5cf6", label="3M Avg")
    ax.set_ylabel("DPD")
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- MAIN APP --------------------
if check_password():
    st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e293b 0%, #334155 100%); color: white; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stDownloadButton button {
        width: 100%; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white !important; border: none; padding: 12px; border-radius: 8px;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background-color: rgba(255, 255, 255, 0.05); border: 1px dashed rgba(255, 255, 255, 0.3);
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background-color: rgba(30, 41, 59, 0.6) !important;
        border: 1px dashed rgba(255, 255, 255, 0.3) !important;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section button {
        background-color: rgba(59, 130, 246, 0.8) !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("# 🛡️ Risk Intelligence")
        st.markdown("---")
        st.markdown("### 📁 Data Input")
        file = st.file_uploader("Upload Portfolio Excel", type=["xlsx"])
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title("📊 Credit Risk Analytics Dashboard")
    
    if file:
        try:
            # 1. Read Data
            raw = pd.read_excel(file)
            codes = raw.iloc[:, 0].unique()
            months = raw.columns[3:]
            
            # 2. Process Infographic (PNG)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name
            
            with st.spinner("Generating High-Fidelity Infographic..."):
                infographic_png = generate_delinquency_chart_bytes(tmp_path)
            os.remove(tmp_path)

            # 3. UI Layout
            excel_buf = BytesIO()
            with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
                tabs = st.tabs([f"Account {c}" for c in codes])
                for tab, code in zip(tabs, codes):
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, max_v, max_m, metrics = analyze(row, months)
                    
                    df.to_excel(writer, f"DATA_{code}", index=False)
                    
                    with tab:
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.markdown("#### 📈 Key Metrics")
                            for k, v in metrics.items(): st.metric(k, v)
                        with col2:
                            st.pyplot(plot_simple_chart(df, max_v, max_m))
                        st.dataframe(build_excel_metrics(df["DPD"], months), use_container_width=True, hide_index=True)

            # 4. Downloads in Sidebar
            with st.sidebar:
                st.markdown("### 💾 Downloads")
                st.download_button("📊 Excel Report", excel_buf.getvalue(), "Risk_Metrics.xlsx", use_container_width=True)
                st.write("")
                st.download_button("🖼️ Infographic Chart (PNG)", infographic_png, "Delinquency_Infographic.png", "image/png", use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
    else:
        st.info("👆 Please upload an Excel file in the sidebar to begin analysis")
