import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
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

# -------------------- AUTHENTICATION --------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if st.session_state.auth:
        return True

    st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    [data-testid="stSidebar"], header, footer { visibility: hidden !important; }
    .main .block-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 0 !important; }
    .login-container { background: white; padding: 3.5rem; border-radius: 24px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.05); text-align: center; border: 1px solid #e2e8f0; width: 100%; max-width: 420px; }
    .login-header { font-size: 1.8rem; font-weight: 800; margin-bottom: 0.5rem; color: #0f172a; }
    .login-sub { color: #64748b; font-size: 0.95rem; margin-bottom: 2.5rem; }
    div[data-testid="stTextInput"] input { border-radius: 12px !important; border: 1px solid #e2e8f0 !important; padding: 0.75rem 1rem !important; background: #f8fafc !important; }
    div.stButton > button:first-child[kind="primary"] { width: 100%; border-radius: 12px; padding: 0.6rem; background: #0f172a; font-weight: 600; border: none; margin-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">Risk Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Enterprise Credit Risk Analytics</div>', unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
            pwd = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            if st.form_submit_button("Sign In", type="primary"):
                if user == "admin" and pwd == "admin":
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)
    return False

# -------------------- ANALYTICS ENGINE --------------------
def get_advanced_metrics(dpd_series):
    dpd = dpd_series.values.astype(float)
    nonzero = dpd[dpd > 0]
    
    # Time to Cure (Avg months to return to 0)
    cure_times = []
    current_streak = 0
    in_delinquency = False
    for val in dpd:
        if val > 0:
            in_delinquency = True
            current_streak += 1
        elif val == 0 and in_delinquency:
            cure_times.append(current_streak)
            current_streak = 0
            in_delinquency = False
    avg_cure = round(np.mean(cure_times), 1) if cure_times else 0

    # Peak-to-Trough Ratio
    max_dpd = np.max(dpd)
    min_nonzero = np.min(nonzero) if len(nonzero) > 0 else 0
    p2t_ratio = round(max_dpd / min_nonzero, 2) if min_nonzero > 0 else 0

    # Consecutive Miss Count
    max_misses = 0
    temp_misses = 0
    for val in dpd:
        if val > 0: temp_misses += 1
        else:
            max_misses = max(max_misses, temp_misses)
            temp_misses = 0
    max_misses = max(max_misses, temp_misses)

    # Recency (Clean months at end of series)
    recency = 0
    for i in range(len(dpd)-1, -1, -1):
        if dpd[i] > 0: break
        recency += 1

    # Bounce Rate (Transitions from 0 to >0)
    bounces = sum(1 for i in range(1, len(dpd)) if dpd[i-1] == 0 and dpd[i] > 0)
    bounce_rate = round((bounces / len(dpd)) * 100, 1)

    # Roll Rate (Probability DPD increases)
    rolls = sum(1 for i in range(1, len(dpd)) if dpd[i] > dpd[i-1] and dpd[i-1] > 0)
    roll_rate = round((rolls / len(nonzero) * 100), 1) if len(nonzero) > 0 else 0

    return {
        "Avg Time to Cure": f"{avg_cure} Mo",
        "Peak-to-Trough": p2t_ratio,
        "Max Consecutive Misses": max_misses,
        "Recency (Clean Mo)": recency,
        "Bounce Rate (%)": bounce_rate,
        "Roll-Forward Rate (%)": roll_rate
    }

def calc_trend_slope(y):
    x = np.arange(len(y))
    num = np.sum((x - x.mean()) * (y - y.mean()))
    den = np.sum((x - x.mean()) ** 2)
    return num / den if den != 0 else 0

def analyze(row, months):
    dpd = row[months].astype(float).fillna(0)
    df = pd.DataFrame({"Month": months.astype(str), "DPD": dpd})
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    adv = get_advanced_metrics(dpd)
    metrics = {
        "Mean DPD": round(np.mean(dpd), 2),
        "Max DPD": int(np.max(dpd)),
        "Cumulative DPD": int(np.sum(dpd)),
        "Trend Slope": round(calc_trend_slope(dpd), 2),
        **adv
    }
    return df, metrics

def plot_chart(df):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df["Month"], df["DPD"], marker="o", color="#3b82f6", label="DPD")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", color="#8b5cf6", label="3M Avg")
    ax.grid(True, alpha=0.1)
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- MAIN APP --------------------
if check_password():
    st.markdown("""
    <style>
    .hero-section { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); padding: 40px; border-radius: 20px; color: white; margin-bottom: 2rem; }
    .stat-card { background: white; padding: 20px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    div.stButton > button:first-child[kind="secondary"] { background-color: #fee2e2 !important; color: #dc2626 !important; border: 1px solid #fca5a5 !important; font-weight: 600; }
    div.stButton > button:first-child[kind="secondary"]:hover { background-color: #ef4444 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 🛡️ Risk Intelligence")
        st.markdown("---")
        file = st.file_uploader("📂 Upload Portfolio Excel", type=["xlsx"])
        st.markdown("---")
        if st.button("🚪 Logout System", use_container_width=True, type="secondary"):
            st.session_state.auth = False
            st.rerun()

    if not file:
        st.markdown('<div class="hero-section"><h1>Advanced Risk Analytics</h1><p>Upload portfolio data to calculate multi-dimensional credit indicators.</p></div>', unsafe_allow_html=True)
    else:
        try:
            raw = pd.read_excel(file)
            codes = raw.iloc[:, 0].unique()
            months = raw.columns[3:]
            excel_buf = BytesIO()

            # COMPREHENSIVE GLOSSARY SHEET DATA
            glossary_data = [
                ["Metric", "Definition", "Interpretation"],
                ["Mean DPD", "The arithmetic average of DPD across the entire time series.", "General level of delinquency over time."],
                ["Max DPD", "The single highest DPD value recorded in the history.", "Maximum exposure/loss potential reached."],
                ["Cumulative DPD", "The sum total of all DPD values recorded.", "Total aggregate volume of delinquency."],
                ["Trend Slope", "Linear regression slope of DPD over time.", "Positive (>0) means worsening; Negative (<0) means improving."],
                ["Avg Time to Cure", "The average number of months an account stays delinquent before returning to zero.", "Indicates recovery speed. Lower is better."],
                ["Peak-to-Trough", "Ratio of Max DPD to the lowest non-zero DPD observed.", "Measures severity/volatility of delinquency spikes."],
                ["Max Consecutive Misses", "The longest continuous streak of delinquent months.", "Indicator of 'sticky' delinquency or imminent default."],
                ["Recency (Clean Mo)", "Count of zero-DPD months immediately preceding the report date.", "Higher values indicate a stabilizing or recovered account."],
                ["Bounce Rate (%)", "Frequency of transitions from 'Current' to 'Delinquent' as a % of total months.", "High bounce indicates habitual lateness or cashflow instability."],
                ["Roll-Forward Rate (%)", "Probability that DPD will increase from the previous month given the account is already delinquent.", "High roll-rate indicates a 'downward spiral' toward default."]
            ]
            df_glossary = pd.DataFrame(glossary_data[1:], columns=glossary_data[0])

            with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
                # 1. Definitions / Glossary Sheet
                df_glossary.to_excel(writer, "Metric Definitions", index=False)
                
                tabs = st.tabs([f"Account {c}" for c in codes])
                for tab, code in zip(tabs, codes):
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, metrics = analyze(row, months)
                    
                    with tab:
                        cl, cr = st.columns([1, 2])
                        with cl:
                            st.subheader("Key Indicators")
                            for k, v in metrics.items(): st.metric(k, v)
                        with cr:
                            st.subheader("Delinquency Trend")
                            st.pyplot(plot_chart(df))
                        
                        full_metrics_df = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"])
                        st.dataframe(full_metrics_df, use_container_width=True, hide_index=True)

                    # Export Logic
                    df.to_excel(writer, f"Data_{code}", index=False)
                    full_metrics_df.to_excel(writer, f"Metrics_{code}", index=False)

            with st.sidebar:
                st.markdown("### 💾 Export Reports")
                st.download_button("📊 Download Portfolio Report", excel_buf.getvalue(), "Risk_Analysis_Full.xlsx", use_container_width=True)
                
        except Exception as e:
            st.error(f"Error processing file: {e}")
