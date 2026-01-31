import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import tempfile

# Must be the first Streamlit command
st.set_page_config(
    page_title="Risk Analytics Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# STYLING - Clean Professional Theme
# -------------------------------------------------
def apply_custom_styling():
    st.markdown("""
        <style>
        /* Import Professional Font */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
        
        * {
            font-family: 'Poppins', sans-serif;
        }
        
        /* Main App Background */
        .stApp {
            background: linear-gradient(to bottom, #0f0c29, #302b63, #24243e);
        }
        
        /* Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Login Page Container */
        .login-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
        }
        
        .login-box {
            background: rgba(255, 255, 255, 0.95);
            padding: 3rem 2.5rem;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            max-width: 450px;
            width: 100%;
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .login-icon {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        
        .login-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.5rem;
        }
        
        .login-subtitle {
            font-size: 0.95rem;
            color: #666;
            font-weight: 400;
        }
        
        /* Metric Cards */
        .metric-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 15px;
            color: white;
            box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
            transition: transform 0.3s ease;
        }
        
        .metric-box:hover {
            transform: translateY(-5px);
        }
        
        .metric-label {
            font-size: 0.85rem;
            opacity: 0.9;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
        }
        
        .metric-context {
            font-size: 0.8rem;
            opacity: 0.8;
            margin-top: 0.3rem;
        }
        
        /* Risk Badges */
        .badge-low {
            background: #10b981;
            color: white;
            padding: 0.5rem 1.2rem;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
        }
        
        .badge-medium {
            background: #f59e0b;
            color: white;
            padding: 0.5rem 1.2rem;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
        }
        
        .badge-high {
            background: #ef4444;
            color: white;
            padding: 0.5rem 1.2rem;
            border-radius: 20px;
            font-weight: 600;
            display: inline-block;
        }
        
        /* Status Badge */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
        }
        
        .status-active {
            background: rgba(16, 185, 129, 0.1);
            color: #059669;
            border: 2px solid #10b981;
        }
        
        .status-settled {
            background: rgba(100, 116, 139, 0.1);
            color: #475569;
            border: 2px solid #64748b;
        }
        
        /* Header Card */
        .header-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            margin-bottom: 2rem;
        }
        
        .header-title {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .header-subtitle {
            font-size: 1rem;
            opacity: 0.9;
        }
        
        /* Info Panel */
        .info-box {
            background: rgba(255, 255, 255, 0.05);
            border-left: 4px solid #667eea;
            padding: 1.5rem;
            border-radius: 8px;
            color: white;
            margin: 1rem 0;
        }
        
        .info-title {
            font-weight: 600;
            color: #a78bfa;
            margin-bottom: 0.8rem;
            font-size: 1rem;
        }
        
        .info-item {
            margin-bottom: 0.8rem;
            font-size: 0.9rem;
            line-height: 1.6;
        }
        
        .info-item strong {
            color: #c4b5fd;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        }
        
        [data-testid="stSidebar"] * {
            color: #e5e7eb !important;
        }
        
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #f3f4f6 !important;
        }
        
        /* Button Styling */
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.7rem 2rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        
        .stDownloadButton > button {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.5rem;
            border-radius: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            color: #9ca3af;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 500;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        
        /* Input Fields */
        .stTextInput > div > div > input {
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            padding: 0.8rem 1rem;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Landing Page */
        .landing-container {
            background: rgba(255, 255, 255, 0.95);
            padding: 3rem 2rem;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        
        .landing-title {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-top: 3rem;
        }
        
        .feature-card {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            padding: 2rem;
            border-radius: 15px;
            border: 2px solid rgba(102, 126, 234, 0.2);
        }
        
        .feature-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .feature-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.5rem;
        }
        
        .feature-desc {
            font-size: 0.9rem;
            color: #666;
            line-height: 1.6;
        }
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------
def check_password():
    """Returns True if user is authenticated"""
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if st.session_state.authenticated:
        return True
    
    # Apply styling
    apply_custom_styling()
    
    # Hide sidebar on login
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)
    
    # Login Form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div class='login-box'>
                <div class='login-header'>
                    <div class='login-icon'>🛡️</div>
                    <h1 class='login-title'>Risk Analytics Platform</h1>
                    <p class='login-subtitle'>Delinquency Intelligence & Risk Assessment</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter username", key="login_user")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            if st.button("🔐 Sign In", use_container_width=True):
                if username in st.secrets["passwords"] and password == st.secrets["passwords"][username]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='text-align: center; color: #999; font-size: 0.85rem;'>
                🔒 Secured with enterprise-grade encryption
            </div>
        """, unsafe_allow_html=True)
    
    return False

# -------------------------------------------------
# ANALYTICS ENGINE
# -------------------------------------------------
def analyze_loan(row, months):
    """Analyze loan delinquency data"""
    dpd = row[months].astype(object)
    first_idx = dpd.first_valid_index()
    
    if first_idx is None:
        return pd.DataFrame(), pd.DataFrame()
    
    last_idx = dpd.last_valid_index()
    start_pos = months.get_loc(first_idx)
    end_pos = months.get_loc(last_idx)
    
    active_dpd = dpd.iloc[start_pos:end_pos+1].fillna(0).astype(float)
    status = ["Not Disbursed"]*start_pos + ["Active"]*(end_pos - start_pos + 1) + ["Settled"]*(len(months) - 1 - end_pos)
    
    df = pd.DataFrame({
        "Month": months.astype(str),
        "DPD": dpd.fillna(0).astype(float).values,
        "Status": status
    })
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    
    max_d = active_dpd.max()
    
    metrics = [
        ("Loan Status", "Settled" if end_pos < len(months)-1 else "Active", "Current State"),
        ("Active Tenure", f"{len(active_dpd)} Months", "Loan Age"),
        ("Delinquency Density", f"{(active_dpd > 0).sum()/len(active_dpd):.1%}", "Frequency"),
        ("Maximum DPD", f"{int(max_d)} Days", "Peak Risk"),
        ("Sticky Bucket", "90+" if max_d >= 90 else "30-89" if max_d >= 30 else "0-29", "Risk Tier"),
        ("Total Cumulative DPD", f"{int(active_dpd.sum())}", "Risk Volume")
    ]
    
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Importance"])

# -------------------------------------------------
# PDF GENERATION
# -------------------------------------------------
def create_pdf_chart(df):
    """Create chart for PDF"""
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.set_facecolor('#ffffff')
    
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#667eea", linewidth=2, label="DPD")
    ax.plot(plot_df.index, plot_df["Rolling_3M"], "--", color="#764ba2", alpha=0.6, label="3M Avg")
    
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        peak_idx = plot_df["DPD"].idxmax()
        peak_val = plot_df["DPD"].max()
        ax.scatter(peak_idx, peak_val, color='red', s=100, edgecolors='black', zorder=5)
        ax.annotate(f'PEAK: {int(peak_val)}', (peak_idx, peak_val), 
                   xytext=(5, 5), textcoords='offset points', fontweight='bold', color='red')
    
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45, fontsize=8)
    ax.legend()
    plt.tight_layout()
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp.name, bbox_inches='tight')
    plt.close(fig)
    return tmp.name

def build_pdf(story, code, row, df, metrics_df, styles):
    """Build PDF report"""
    story.append(Paragraph(f"Loan Performance Report: {code}", styles['Heading1']))
    story.append(Spacer(1, 15))
    
    m_data = [["Metric", "Value", "Risk Perspective"]] + metrics_df.values.tolist()
    mt = Table(m_data, colWidths=[2*inch, 1.5*inch, 3*inch])
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(mt)
    story.append(Spacer(1, 25))
    story.append(Image(create_pdf_chart(df), width=6.5*inch, height=3.2*inch))
    story.append(PageBreak())

# -------------------------------------------------
# METRIC DISPLAY
# -------------------------------------------------
def display_metrics(metrics_df, sanctioned, balance):
    """Display metrics in cards"""
    
    # Financial Overview
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div class='metric-box'>
                <div class='metric-label'>💰 SANCTIONED AMOUNT</div>
                <div class='metric-value'>Rs. {sanctioned:,.0f}</div>
                <div class='metric-context'>Original loan amount</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class='metric-box'>
                <div class='metric-label'>📊 OUTSTANDING BALANCE</div>
                <div class='metric-value'>Rs. {balance:,.0f}</div>
                <div class='metric-context'>{(balance/sanctioned*100):.1f}% of principal</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Risk Metrics
    cols = st.columns(3)
    
    for idx, (_, row) in enumerate(metrics_df.iterrows()):
        metric_name = row['Metric']
        metric_value = row['Value']
        metric_context = row['Importance']
        
        icons = {
            "Loan Status": "📋",
            "Active Tenure": "⏱️",
            "Delinquency Density": "📉",
            "Maximum DPD": "🎯",
            "Sticky Bucket": "🏷️",
            "Total Cumulative DPD": "📈"
        }
        
        icon = icons.get(metric_name, "📊")
        
        with cols[idx % 3]:
            if metric_name == "Sticky Bucket":
                if "90+" in metric_value:
                    badge_class = "badge-high"
                elif "30-89" in metric_value:
                    badge_class = "badge-medium"
                else:
                    badge_class = "badge-low"
                
                st.markdown(f"""
                    <div class='metric-box'>
                        <div class='metric-label'>{icon} {metric_name.upper()}</div>
                        <div class='{badge_class}'>{metric_value}</div>
                        <div class='metric-context'>{metric_context}</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class='metric-box'>
                        <div class='metric-label'>{icon} {metric_name.upper()}</div>
                        <div class='metric-value'>{metric_value}</div>
                        <div class='metric-context'>{metric_context}</div>
                    </div>
                """, unsafe_allow_html=True)

# -------------------------------------------------
# MAIN APPLICATION
# -------------------------------------------------
if not check_password():
    st.stop()

# Apply styling for authenticated users
apply_custom_styling()

# Sidebar
with st.sidebar:
    st.markdown("<h2 style='color: #f3f4f6; text-align: center;'>🛡️ Risk Portal</h2>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("📁 Upload Excel File", type=["xlsx"])
    
    if uploaded_file:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<h3 style='color: #f3f4f6;'>📖 Metrics Guide</h3>", unsafe_allow_html=True)
        
        with st.expander("View Definitions", expanded=False):
            st.markdown("""
                <div class='info-box'>
                    <div class='info-item'><strong>Delinquency Density:</strong> Payment failure frequency (Count DPD>0 / Total Months)</div>
                    <div class='info-item'><strong>Maximum DPD:</strong> Highest days past due reached</div>
                    <div class='info-item'><strong>Sticky Bucket:</strong> Risk tier (90+/30-89/0-29)</div>
                    <div class='info-item'><strong>Rolling 3M Avg:</strong> Trend smoothing indicator</div>
                    <div class='info-item'><strong>Cumulative DPD:</strong> Total loss exposure</div>
                </div>
            """, unsafe_allow_html=True)

# Main Content
if not uploaded_file:
    # Landing Page
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        st.markdown("""
            <div class='landing-container'>
                <div style='font-size: 4rem; margin-bottom: 1rem;'>🛡️</div>
                <h1 class='landing-title'>Risk Analytics Platform</h1>
                <p style='color: #666; font-size: 1.1rem; margin-bottom: 2rem;'>
                    Advanced delinquency analysis with automated PDF reporting
                </p>
                
                <div class='feature-grid'>
                    <div class='feature-card'>
                        <div class='feature-icon'>📊</div>
                        <div class='feature-title'>Analytics Engine</div>
                        <div class='feature-desc'>DPD density, sticky buckets, and trend analysis</div>
                    </div>
                    <div class='feature-card'>
                        <div class='feature-icon'>📋</div>
                        <div class='feature-title'>PDF Reports</div>
                        <div class='feature-desc'>Professional reports with peak highlighting</div>
                    </div>
                    <div class='feature-card'>
                        <div class='feature-icon'>🔒</div>
                        <div class='feature-title'>Secure Access</div>
                        <div class='feature-desc'>Enterprise-grade authentication</div>
                    </div>
                </div>
                
                <div style='margin-top: 3rem; padding: 1.5rem; background: rgba(102, 126, 234, 0.1); border-radius: 10px;'>
                    <p style='color: #667eea; font-weight: 600;'>
                        ⬆️ Upload your Excel file using the sidebar to begin analysis
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
else:
    # Process Data
    raw_data = pd.read_excel(uploaded_file)
    codes = raw_data.iloc[:, 0].unique()
    months = raw_data.columns[3:]
    
    # Prepare Excel Output
    output_excel = BytesIO()
    with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
        
        # Prepare Bulk PDF
        bulk_buf = BytesIO()
        doc = SimpleDocTemplate(bulk_buf, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Create Tabs
        tabs = st.tabs([f"📄 {str(c)}" for c in codes])
        
        for tab, code in zip(tabs, codes):
            row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
            df, metrics_df = analyze_loan(row, months)
            
            # Save to Excel
            df.to_excel(writer, sheet_name=str(code)[:31], index=False)
            
            with tab:
                # Header
                loan_status = metrics_df[metrics_df['Metric'] == 'Loan Status']['Value'].iloc[0]
                status_class = "status-active" if loan_status == "Active" else "status-settled"
                
                st.markdown(f"""
                    <div class='header-card'>
                        <div class='header-title'>Account: {code}</div>
                        <div class='header-subtitle'>Comprehensive delinquency assessment</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Status Badge
                st.markdown(f"""
                    <div class='{status_class} status-badge'>
                        <span style='width: 8px; height: 8px; border-radius: 50%; background: currentColor;'></span>
                        {loan_status}
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Display Metrics
                display_metrics(metrics_df, row.iloc[1], row.iloc[2])
                
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                # Chart
                st.markdown("<h3 style='color: white;'>📈 Delinquency Trend</h3>", unsafe_allow_html=True)
                
                fig, ax = plt.subplots(figsize=(12, 4.5))
                ax.set_facecolor('#1a1a2e')
                fig.patch.set_facecolor('#1a1a2e')
                
                active_plot = df[df["Status"] != "Not Disbursed"]
                ax.plot(active_plot["Month"], active_plot["DPD"], 
                       marker="o", color="#667eea", linewidth=2.5, markersize=6, label="DPD")
                ax.plot(active_plot["Month"], active_plot["Rolling_3M"], 
                       linestyle="--", color="#10b981", linewidth=2, alpha=0.7, label="3M Rolling Avg")
                
                if not active_plot.empty and active_plot["DPD"].max() > 0:
                    p_val = active_plot["DPD"].max()
                    p_mon = active_plot.loc[active_plot["DPD"].idxmax(), "Month"]
                    ax.plot(p_mon, p_val, marker='*', color='#ef4444', markersize=20, 
                           markeredgecolor='white', markeredgewidth=1.5, label="Peak")
                    ax.text(p_mon, p_val + (p_val * 0.1), f"PEAK: {int(p_val)} days", 
                           ha='center', color='#ef4444', fontweight='bold', fontsize=11)
                
                ax.set_xlabel("Month", fontsize=11, fontweight='500', color='white')
                ax.set_ylabel("Days Past Due", fontsize=11, fontweight='500', color='white')
                ax.tick_params(colors='white')
                ax.grid(True, alpha=0.2, linestyle='--', color='white')
                ax.legend(loc='best', frameon=True)
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                st.pyplot(fig)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Download PDF
                single_buf = BytesIO()
                single_doc = SimpleDocTemplate(single_buf, pagesize=letter)
                single_story = []
                build_pdf(single_story, code, row, df, metrics_df, styles)
                single_doc.build(single_story)
                
                st.download_button(
                    f"📥 Download PDF Report",
                    single_buf.getvalue(),
                    f"Report_{code}.pdf",
                    use_container_width=True
                )
                
                # Add to bulk PDF
                build_pdf(story, code, row, df, metrics_df, styles)
        
        # Finalize bulk PDF
        doc.build(story)
    
    # Sidebar Downloads
    st.sidebar.markdown("---")
    st.sidebar.markdown("<h3 style='color: #f3f4f6;'>💾 Bulk Export</h3>", unsafe_allow_html=True)
    st.sidebar.download_button(
        "📂 Download All (Excel)",
        output_excel.getvalue(),
        "Portfolio_Analysis.xlsx",
        use_container_width=True
    )
    st.sidebar.download_button(
        "📦 Download All (PDF)",
        bulk_buf.getvalue(),
        "Risk_Reports_Complete.pdf",
        use_container_width=True
    )
