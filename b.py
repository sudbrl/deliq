import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile

# -------------------------------------------------
# PROFESSIONAL STYLING
# -------------------------------------------------
def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }
        
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
        }
        
        /* Login Page Styling */
        .login-container {
            background: rgba(255, 255, 255, 0.98);
            padding: 3.5rem 3rem;
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(148, 163, 184, 0.2);
        }
        
        .login-header {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        
        .login-title {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #0f172a 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .login-subtitle {
            color: #64748b;
            font-size: 0.95rem;
            font-weight: 400;
        }
        
        .security-badge {
            display: inline-block;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 1rem;
            box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3);
        }
        
        /* Metric Cards */
        .metric-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            padding: 1.8rem;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            height: 100%;
        }
        
        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
        }
        
        .metric-label {
            font-size: 0.85rem;
            color: #64748b;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }
        
        .metric-value {
            font-size: 2.2rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.3rem;
        }
        
        .metric-context {
            font-size: 0.8rem;
            color: #94a3b8;
            font-weight: 400;
        }
        
        .metric-icon {
            font-size: 2rem;
            margin-bottom: 0.8rem;
            opacity: 0.8;
        }
        
        /* Risk Badges */
        .risk-badge-low {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 0.4rem 1.2rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1.1rem;
            display: inline-block;
            box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.4);
        }
        
        .risk-badge-medium {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            padding: 0.4rem 1.2rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1.1rem;
            display: inline-block;
            box-shadow: 0 4px 6px -1px rgba(245, 158, 11, 0.4);
        }
        
        .risk-badge-high {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            padding: 0.4rem 1.2rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 1.1rem;
            display: inline-block;
            box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.4);
        }
        
        /* Info Panel */
        .info-panel {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 4px solid #3b82f6;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 2rem 0;
        }
        
        .info-title {
            font-weight: 600;
            color: #1e40af;
            font-size: 1.1rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .metric-definition {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 0.8rem;
            border: 1px solid #bfdbfe;
        }
        
        .metric-def-name {
            font-weight: 600;
            color: #1e40af;
            font-size: 0.95rem;
            margin-bottom: 0.3rem;
        }
        
        .metric-def-text {
            color: #475569;
            font-size: 0.85rem;
            line-height: 1.5;
        }
        
        /* Header Enhancement */
        .main-header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            border: 1px solid rgba(148, 163, 184, 0.2);
        }
        
        .account-title {
            color: white;
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .account-subtitle {
            color: #94a3b8;
            font-size: 0.95rem;
        }
        
        /* Sidebar Enhancements */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        }
        
        [data-testid="stSidebar"] .stMarkdown {
            color: #e2e8f0;
        }
        
        /* Button Enhancements */
        .stButton > button {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            padding: 0.6rem 1.5rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.4);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.5);
        }
        
        /* Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: rgba(255, 255, 255, 0.05);
            padding: 0.5rem;
            border-radius: 12px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 8px;
            color: #cbd5e1;
            font-weight: 500;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
        }
        
        /* Status Indicator */
        .status-active {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            color: #059669;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        
        .status-settled {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(100, 116, 139, 0.1);
            color: #475569;
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
        }
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# 1. AUTHENTICATION & SESSION
# -------------------------------------------------
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    inject_custom_css()
    
    # Centered login layout
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
            <div class='login-container'>
                <div class='login-header'>
                    <div style='font-size: 3.5rem; margin-bottom: 1rem;'>🛡️</div>
                    <h1 class='login-title'>Risk Intelligence Platform</h1>
                    <p class='login-subtitle'>Enterprise-Grade Delinquency Analytics System</p>
                    <div class='security-badge'>🔒 Secure Access Required</div>
                </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        u = st.text_input("Username", placeholder="Enter your username", label_visibility="collapsed", key="username_input")
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        p = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed", key="password_input")
        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        
        if st.button("🔐 Secure Login", use_container_width=True):
            if u in st.secrets["passwords"] and p == st.secrets["passwords"][u]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Invalid credentials. Please try again.")
        
        st.markdown("""
                <div style='text-align: center; margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0;'>
                    <p style='color: #94a3b8; font-size: 0.8rem;'>Protected by industry-standard encryption</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    return False

# -------------------------------------------------
# 2. ANALYTICS ENGINE
# -------------------------------------------------
def analyze_loan(row, months):
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
# 3. METRIC DEFINITIONS COMPONENT
# -------------------------------------------------
def display_metric_glossary():
    st.markdown("""
        <div class='info-panel'>
            <div class='info-title'>
                📖 Risk Metrics Glossary
            </div>
    """, unsafe_allow_html=True)
    
    metrics_info = [
        {
            "name": "Delinquency Density",
            "definition": "Frequency of payment failure across active loan tenure.",
            "formula": "Count(DPD > 0) / Total Active Months",
            "importance": "Identifies chronic defaulters vs one-time delays."
        },
        {
            "name": "Maximum DPD",
            "definition": "The highest number of days past due ever reached.",
            "formula": "Max(All DPD Values)",
            "importance": "Determines capital provisioning requirements."
        },
        {
            "name": "Sticky Bucket",
            "definition": "Risk categorization based on peak delinquency level.",
            "formula": "90+ (NPA) | 30-89 (Sub-Standard) | 0-29 (Standard)",
            "importance": "Regulatory classification for risk-weighted assets."
        },
        {
            "name": "Rolling 3-Month Average",
            "definition": "Moving average of delinquency to smooth volatility.",
            "formula": "Sum(Last 3 Months DPD) / 3",
            "importance": "Reveals underlying trends beyond monthly spikes."
        },
        {
            "name": "Cumulative DPD",
            "definition": "Total days past due accumulated over loan lifecycle.",
            "formula": "Sum(All DPD Values)",
            "importance": "Measures total exposure to credit loss."
        },
        {
            "name": "Active Tenure",
            "definition": "Number of months from disbursement to settlement/current.",
            "formula": "Count(Months with Balance > 0)",
            "importance": "Loan maturity indicator for vintage analysis."
        }
    ]
    
    for metric in metrics_info:
        st.markdown(f"""
            <div class='metric-definition'>
                <div class='metric-def-name'>{metric['name']}</div>
                <div class='metric-def-text'><strong>Definition:</strong> {metric['definition']}</div>
                <div class='metric-def-text'><strong>Formula:</strong> {metric['formula']}</div>
                <div class='metric-def-text'><strong>Why It Matters:</strong> {metric['importance']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------
# 4. ENHANCED METRIC DISPLAY
# -------------------------------------------------
def display_fancy_metrics(metrics_df, loan_status, sanctioned, balance):
    # Status Badge
    if loan_status == "Active":
        status_html = f"""
            <div class='status-active'>
                <span class='status-dot'></span>
                Active Loan
            </div>
        """
    else:
        status_html = f"""
            <div class='status-settled'>
                <span class='status-dot'></span>
                Settled
            </div>
        """
    
    st.markdown(status_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Financial Overview
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-icon'>💰</div>
                <div class='metric-label'>Sanctioned Amount</div>
                <div class='metric-value'>₹{sanctioned:,.0f}</div>
                <div class='metric-context'>Original loan amount</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-icon'>📊</div>
                <div class='metric-label'>Outstanding Balance</div>
                <div class='metric-value'>₹{balance:,.0f}</div>
                <div class='metric-context'>{(balance/sanctioned*100):.1f}% of principal</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # Risk Metrics Grid
    cols = st.columns(3)
    
    for idx, (_, row) in enumerate(metrics_df.iterrows()):
        metric_name = row['Metric']
        metric_value = row['Value']
        metric_context = row['Importance']
        
        # Icon selection
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
            # Special styling for Sticky Bucket
            if metric_name == "Sticky Bucket":
                if "90+" in metric_value:
                    badge_class = "risk-badge-high"
                elif "30-89" in metric_value:
                    badge_class = "risk-badge-medium"
                else:
                    badge_class = "risk-badge-low"
                
                st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-icon'>{icon}</div>
                        <div class='metric-label'>{metric_name}</div>
                        <div class='{badge_class}'>{metric_value}</div>
                        <div class='metric-context'>{metric_context}</div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-icon'>{icon}</div>
                        <div class='metric-label'>{metric_name}</div>
                        <div class='metric-value'>{metric_value}</div>
                        <div class='metric-context'>{metric_context}</div>
                    </div>
                """, unsafe_allow_html=True)

# -------------------------------------------------
# 5. PDF GENERATION (NO GLOSSARY)
# -------------------------------------------------
def create_pdf_chart(df):
    plot_df = df[df["Status"] != "Not Disbursed"].reset_index()
    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
    ax.set_facecolor('#ffffff')
    
    ax.plot(plot_df.index, plot_df["DPD"], marker="o", color="#1e3a8a", linewidth=2, label="DPD")
    ax.plot(plot_df.index, plot_df["Rolling_3M"], "--", color="#3b82f6", alpha=0.6, label="3M Avg")
    
    if not plot_df.empty and plot_df["DPD"].max() > 0:
        peak_idx = plot_df["DPD"].idxmax()
        peak_val = plot_df["DPD"].max()
        ax.scatter(peak_idx, peak_val, color='red', s=100, edgecolors='black', zorder=5)
        ax.annotate(f'PEAK: {int(peak_val)}', (peak_idx, peak_val), xytext=(5, 5), textcoords='offset points', fontweight='bold', color='red')

    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(plot_df["Month"], rotation=45, fontsize=8)
    ax.legend()
    plt.tight_layout()
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp.name, bbox_inches='tight')
    plt.close(fig)
    return tmp.name

def build_pdf(story, code, row, df, metrics_df, styles):
    story.append(Paragraph(f"Loan Performance Report: {code}", styles['Heading1']))
    story.append(Spacer(1, 15))

    # Metrics Table
    m_data = [["Metric", "Value", "Risk Perspective"]] + metrics_df.values.tolist()
    mt = Table(m_data, colWidths=[2*inch, 1.5*inch, 3*inch])
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(mt)
    story.append(Spacer(1, 25))

    # Chart
    story.append(Image(create_pdf_chart(df), width=6.5*inch, height=3.2*inch))
    story.append(PageBreak())

# -------------------------------------------------
# 6. MAIN INTERFACE
# -------------------------------------------------
if check_password():
    st.set_page_config(page_title="Risk Intelligence Platform", layout="wide", page_icon="🛡️")
    inject_custom_css()

    with st.sidebar:
        st.markdown("<h2 style='color: #e2e8f0; margin-bottom: 2rem;'>🛡️ Risk Portal</h2>", unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("📁 Upload Delinquency File", type=["xlsx"])
        
        if uploaded_file:
            st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<h3 style='color: #e2e8f0;'>📚 Resources</h3>", unsafe_allow_html=True)
            
            with st.expander("📖 View Metrics Guide", expanded=False):
                st.markdown("""
                <div style='color: #cbd5e1; font-size: 0.85rem;'>
                    <p><strong>Delinquency Density:</strong> Payment failure frequency</p>
                    <p><strong>Maximum DPD:</strong> Highest risk point reached</p>
                    <p><strong>Sticky Bucket:</strong> Regulatory risk category</p>
                    <p><strong>Rolling 3M Avg:</strong> Trend smoothing indicator</p>
                    <p><strong>Cumulative DPD:</strong> Total loss exposure</p>
                </div>
                """, unsafe_allow_html=True)

    if not uploaded_file:
        # LANDING PAGE
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,252,0.95) 100%); 
                        padding: 4rem; border-radius: 24px; text-align: center; 
                        border: 1px solid rgba(148, 163, 184, 0.2);
                        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);">
                <div style='font-size: 4rem; margin-bottom: 1rem;'>🛡️</div>
                <h1 style="color: #0f172a; font-size: 3rem; font-weight: 700; margin-bottom: 1rem;">
                    Risk Intelligence Platform
                </h1>
                <p style="color: #64748b; font-size: 1.2rem; margin-bottom: 3rem; max-width: 700px; margin-left: auto; margin-right: auto;">
                    Enterprise-grade delinquency analytics with automated PDF reporting and regulatory compliance metrics
                </p>
                
                <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 4rem; flex-wrap: wrap;">
                    <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); 
                                padding: 2.5rem; border-radius: 20px; width: 300px; 
                                border: 2px solid #bfdbfe;
                                box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.1);">
                        <div style='font-size: 2.5rem; margin-bottom: 1rem;'>📊</div>
                        <h3 style="color: #1e40af; margin-bottom: 1rem; font-size: 1.3rem;">Advanced Analytics</h3>
                        <p style="color: #64748b; font-size: 0.95rem; line-height: 1.6;">
                            DPD density, delinquency episodes, sticky bucket classification, and trend analysis
                        </p>
                    </div>
                    
                    <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); 
                                padding: 2.5rem; border-radius: 20px; width: 300px; 
                                border: 2px solid #bbf7d0;
                                box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.1);">
                        <div style='font-size: 2.5rem; margin-bottom: 1rem;'>📋</div>
                        <h3 style="color: #166534; margin-bottom: 1rem; font-size: 1.3rem;">PDF Reporting</h3>
                        <p style="color: #64748b; font-size: 0.95rem; line-height: 1.6;">
                            Professional reports with peak highlighting and comprehensive risk assessment
                        </p>
                    </div>
                    
                    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                                padding: 2.5rem; border-radius: 20px; width: 300px; 
                                border: 2px solid #fcd34d;
                                box-shadow: 0 10px 15px -3px rgba(245, 158, 11, 0.1);">
                        <div style='font-size: 2.5rem; margin-bottom: 1rem;'>🔒</div>
                        <h3 style="color: #92400e; margin-bottom: 1rem; font-size: 1.3rem;">Secure Access</h3>
                        <p style="color: #64748b; font-size: 0.95rem; line-height: 1.6;">
                            Role-based authentication with encrypted data handling and audit trails
                        </p>
                    </div>
                </div>
                
                <div style='margin-top: 5rem; padding-top: 2rem; border-top: 1px solid #e2e8f0;'>
                    <p style='color: #94a3b8; font-size: 0.9rem; font-style: italic;'>
                        ⬆️ Upload an Excel file via the sidebar to begin portfolio analysis
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        raw_data = pd.read_excel(uploaded_file)
        codes = raw_data.iloc[:, 0].unique()
        months = raw_data.columns[3:]

        # Excel Writer for multi-sheet download
        output_excel = BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            tabs = st.tabs([f"📄 {str(c)}" for c in codes])
            
            # Prepare Bulk PDF
            bulk_buf = BytesIO()
            doc = SimpleDocTemplate(bulk_buf, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            for tab, code in zip(tabs, codes):
                row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                df, metrics_df = analyze_loan(row, months)
                df.to_excel(writer, sheet_name=str(code)[:31], index=False)
                
                with tab:
                    # Header
                    st.markdown(f"""
                        <div class='main-header'>
                            <div class='account-title'>Account Analysis: {code}</div>
                            <div class='account-subtitle'>Comprehensive delinquency report with risk indicators</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Fancy Metrics Display
                    loan_status = metrics_df[metrics_df['Metric'] == 'Loan Status']['Value'].iloc[0]
                    display_fancy_metrics(metrics_df, loan_status, row.iloc[1], row.iloc[2])
                    
                    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
                    
                    # Chart Section
                    st.markdown("### 📈 Delinquency Trend Analysis")
                    fig, ax = plt.subplots(figsize=(12, 4.5))
                    ax.set_facecolor('#f8fafc')
                    fig.patch.set_facecolor('#ffffff')
                    
                    active_plot = df[df["Status"] != "Not Disbursed"]
                    ax.plot(active_plot["Month"], active_plot["DPD"], marker="o", 
                           color="#3b82f6", linewidth=2.5, markersize=6, label="DPD")
                    ax.plot(active_plot["Month"], active_plot["Rolling_3M"], 
                           linestyle="--", color="#10b981", linewidth=2, alpha=0.7, label="3-Month Rolling Avg")
                    
                    if not active_plot.empty and active_plot["DPD"].max() > 0:
                        p_val = active_plot["DPD"].max()
                        p_mon = active_plot.loc[active_plot["DPD"].idxmax(), "Month"]
                        ax.plot(p_mon, p_val, marker='*', color='red', markersize=20, 
                               markeredgecolor='darkred', markeredgewidth=1.5, label="Peak DPD")
                        ax.text(p_mon, p_val + (p_val * 0.1), f"PEAK: {int(p_val)} days", 
                               ha='center', color='red', fontweight='bold', fontsize=11,
                               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                                        edgecolor='red', linewidth=1.5))
                    
                    ax.set_xlabel("Month", fontsize=11, fontweight='500')
                    ax.set_ylabel("Days Past Due", fontsize=11, fontweight='500')
                    ax.grid(True, alpha=0.2, linestyle='--')
                    ax.legend(loc='best', frameon=True, shadow=True)
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    st.pyplot(fig)

                    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
                    
                    # Individual PDF Download
                    single_buf = BytesIO()
                    single_doc = SimpleDocTemplate(single_buf, pagesize=letter)
                    single_story = []
                    build_pdf(single_story, code, row, df, metrics_df, styles)
                    single_doc.build(single_story)
                    
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        st.download_button(
                            f"📥 Download PDF Report", 
                            single_buf.getvalue(), 
                            f"Risk_Report_{code}.pdf",
                            use_container_width=True
                        )

                    # Logic for Bulk PDF construction
                    build_pdf(story, code, row, df, metrics_df, styles)

            # Finalize Bulk PDF
            doc.build(story)

        # Sidebar Downloads
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3 style='color: #e2e8f0;'>💾 Bulk Downloads</h3>", unsafe_allow_html=True)
        st.sidebar.download_button(
            "📂 Excel (All Accounts)", 
            output_excel.getvalue(), 
            "Portfolio_Analysis.xlsx",
            use_container_width=True
        )
        st.sidebar.download_button(
            "📦 PDF (All Reports)", 
            bulk_buf.getvalue(), 
            "Risk_Reports_Complete.pdf",
            use_container_width=True
        )
        
        # Add Glossary at Bottom
        st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)
        with st.expander("📖 View Complete Risk Metrics Glossary", expanded=False):
            display_metric_glossary()
