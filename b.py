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

    # ✅ PROFESSIONAL LOGIN UI
    st.markdown("""
    <style>
    /* Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Hide Navbar/Footer */
    header, footer { visibility: hidden !important; }
    
    /* Login Card Container Styling */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {
        background-color: white;
        padding: 3rem;
        border-radius: 20px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    }
    
    /* Input Fields Styling */
    .stTextInput input {
        border: 1px solid #e2e8f0;
        padding: 10px;
        border-radius: 8px;
    }
    
    /* Button Styling */
    .stButton button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px;
        font-weight: bold;
        border-radius: 8px;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }

    /* Hide Sidebar on Login */
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

    # Vertical Spacer
    st.write("")
    st.write("")
    st.write("")
    st.write("")
    st.write("")

    # Columns to center horizontally
    col1, col2, col3 = st.columns([1, 0.6, 1]) 

    with col2:
        # Header inside the card
        st.markdown("<h1 style='text-align: center; color: #1e293b; margin-bottom: 0;'>🛡️ Risk Intel</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-top: 5px; margin-bottom: 30px;'>Enterprise Credit Analytics</p>", unsafe_allow_html=True)
        
        # Inputs
        username = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        
        st.write("") # Gap
        
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

# -------------------- SEASONALITY FUNCTIONS --------------------
def calc_monthly_avg(dpd, months):
    """Calculate average DPD by calendar month"""
    month_data = {}
    for i, m in enumerate(months):
        month_str = str(m)
        if '-' in month_str:
            try:
                month_num = int(month_str.split('-')[1])
            except:
                month_num = (i % 12) + 1
        else:
            month_num = (i % 12) + 1
        
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
    
    # Calculate seasonality metrics
    seasonality_idx = calc_seasonality_index(dpd, months)
    seasonal_strength = calc_seasonal_strength(dpd, months)
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

def build_seasonality_sheet(dpd_series, months):
    """Create detailed seasonality breakdown by calendar month"""
    dpd = dpd_series.values.astype(float)
    monthly_avg = calc_monthly_avg(dpd, months)
    seasonality_idx = calc_seasonality_index(dpd, months)
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    data = []
    for month_num in range(1, 13):
        avg_dpd = monthly_avg.get(month_num, 0)
        index = seasonality_idx.get(month_num, 100)
        
        if index > 110:
            interpretation = "Above average risk"
        elif index < 90:
            interpretation = "Below average risk"
        else:
            interpretation = "Normal risk level"
        
        data.append({
            'Month_Num': month_num,
            'Month_Name': month_names[month_num - 1],
            'Avg_DPD': round(avg_dpd, 2),
            'Seasonality_Index': round(index, 1),
            'Interpretation': interpretation
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
    ax.plot(df["Month"], df["DPD"], marker="o", linewidth=2, markersize=6, label="DPD", color="#3b82f6")
    ax.plot(df["Month"], df["Rolling_3M"], linestyle="--", linewidth=1.5, label="3M Rolling Avg", color="#8b5cf6")
    ax.plot(max_month, max_dpd, "r*", markersize=16)
    ax.text(max_month, max_dpd + 5, f"MAX {int(max_dpd)}", ha="center", color="red", fontweight="bold")
    ax.set_ylabel("Days Past Due (DPD)")
    ax.set_xlabel("Month")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# -------------------- PDF --------------------
def build_pdf(story, code, df, max_dpd, max_month, metrics):
    styles = getSampleStyleSheet()
    story.append(Paragraph(
        f"Loan Performance Report – Account {code}",
        ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=16, leading=18)))
    story.append(Spacer(1, 12))
    
    # Important metrics table
    data = [["Metric", "Value"]] + [[k, v] for k, v in metrics.items()]
    t = Table(data, colWidths=[3 * inch, 3 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    
    # Chart
    fig_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    plot_chart(df, max_dpd, max_month).savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()
    story.append(Image(fig_path, 6.5 * inch, 3.2 * inch))
    story.append(PageBreak())

# -------------------- MAIN APP --------------------
if check_password():
    
    # Apply professional styling with SIDEBAR VISIBILITY FIXES
    st.markdown("""
    <style>
    /* Professional app styling */
    .main {
        background-color: #f8fafc;
    }
    
    h1, h2, h3 {
        color: #1e293b;
        font-weight: 700;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6;
        color: white;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
        color: white;
    }
    
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: white !important;
    }
    
    /* Download buttons (keep gradient) */
    [data-testid="stSidebar"] .stDownloadButton button {
        width: 100%;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white !important;
        font-weight: 600;
        border: none;
        padding: 12px;
        border-radius: 8px;
    }
    
    /* --- FIX: File Uploader --- */
    /* Make the container transparent/dashed so it blends with dark sidebar */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px dashed rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        padding: 1rem;
    }
    /* Ensure the internal text is white */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: #cbd5e1 !important;
    }
    /* Ensure the internal 'Browse files' button has dark text so it shows on white button */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        color: #1e293b !important; 
        background-color: white !important;
        border: none;
    }

    /* --- FIX: Logout Button --- */
    /* Make logout button outlined/transparent to work on dark sidebar */
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.5);
        color: white !important;
        padding: 8px;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255, 255, 255, 0.1);
        border-color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # -------------------- SIDEBAR --------------------
    with st.sidebar:
        st.markdown("# 🛡️ Risk Intelligence")
        st.markdown("### Enterprise Analytics Platform")
        st.markdown("---")

        # 1. FILE UPLOAD
        st.markdown("### 📁 Data Input")
        file = st.file_uploader("Upload Portfolio Excel", type=["xlsx"], help="Upload Excel file with DPD data")
        
        st.markdown("---")
        
        # 2. STATUS
        st.markdown("### 📊 System Status")
        st.success("✅ System Online")
        st.info("📅 " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"))

        # 3. LOGOUT (Bottom)
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    # -------------------- MAIN CONTENT --------------------
    st.title("📊 Credit Risk Analytics Dashboard")
    st.markdown("View comprehensive risk metrics, seasonality patterns, and trend analysis for your portfolio.")
    
    if file:
        try:
            raw = pd.read_excel(file)
            codes = raw.iloc[:, 0].unique()
            months = raw.columns[3:]
            
            st.success(f"✅ File loaded successfully! Processing {len(codes)} accounts...")
            
            excel_buf = BytesIO()
            pdf_buf = BytesIO()
            doc = SimpleDocTemplate(pdf_buf, pagesize=letter)
            story = []
            
            # Generate Excel and PDF
            with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
                tabs = st.tabs([f"Account {c}" for c in codes])
                
                for tab, code in zip(tabs, codes):
                    row = raw[raw.iloc[:, 0] == code].iloc[0]
                    df, max_dpd, max_month, metrics = analyze(row, months)
                    
                    # Excel sheets (REMOVED SEASONALITY SHEET)
                    df.to_excel(writer, f"DATA_{code}", index=False)
                    build_excel_metrics(df["DPD"], months).to_excel(writer, f"METRICS_{code}", index=False)
                    
                    # Display in app
                    with tab:
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            st.markdown("#### 📈 Key Metrics")
                            for key, val in metrics.items():
                                st.metric(key, val)
                        
                        with col2:
                            st.markdown("#### 📊 DPD Trend Analysis")
                            st.pyplot(plot_chart(df, max_dpd, max_month))
                        
                        # Full metrics table
                        st.markdown("#### 📋 Complete Risk Metrics")
                        st.dataframe(
                            build_excel_metrics(df["DPD"], months),
                            use_container_width=True,
                            hide_index=True
                        )
                    
                    # PDF
                    build_pdf(story, code, df, max_dpd, max_month, metrics)
            
            doc.build(story)
            
            # -------------------- DOWNLOADS --------------------
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 💾 Downloads")
                
                st.download_button(
                    "📊 Excel Report",
                    excel_buf.getvalue(),
                    "Risk_Metrics_Report.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                st.write("") # small gap
                
                st.download_button(
                    "📄 PDF Report",
                    pdf_buf.getvalue(),
                    "Risk_Analysis_Report.pdf",
                    "application/pdf",
                    use_container_width=True
                )
        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("💡 Please ensure your Excel file has the correct format with account codes in column 1 and DPD data starting from column 4.")
    
    else:
        # Welcome message when no file uploaded
        st.info("👆 Please upload an Excel file in the sidebar to begin analysis")
        
        with st.expander("📖 How to use this platform", expanded=True):
            st.markdown("""
            **Step 1:** Upload your portfolio Excel file using the sidebar.
            - Column 1: Account codes
            - Columns 4+: Monthly DPD values
            
            **Step 2:** Review analytics for each account in separate tabs
            - Key metrics overview
            - Visual trend analysis
            - Complete risk assessment
            
            **Step 3:** Download comprehensive reports (Sidebar)
            - Excel: Detailed metrics + seasonality analysis
            - PDF: Executive summary report
            """)
