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
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# STYLING - Enterprise Theme
# -------------------------------------------------
def apply_custom_styling():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }

        /* Background and Glassmorphism */
        .stApp {
            background: radial-gradient(circle at top left, #1e293b, #0f172a);
        }

        /* Login Container */
        .auth-container {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            margin-top: 5vh;
        }

        /* Buttons */
        .stButton>button {
            width: 100%;
            border-radius: 12px;
            height: 3em;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            font-weight: 600;
            border: none;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.5);
        }

        /* Metric Cards */
        .metric-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 16px;
            text-align: center;
        }
        
        /* Hide default elements */
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    apply_custom_styling()

    # Centered Login UI
    _, col, _ = st.columns([1, 1.2, 1])
    
    with col:
        st.markdown("""
            <div class="auth-container">
                <h1 style='text-align: center; color: white; margin-bottom: 0;'>🛡️</h1>
                <h2 style='text-align: center; color: white; margin-top: 10px; font-weight: 700;'>Risk Portal</h2>
                <p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Enter credentials to access delinquency intel</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            user_input = st.text_input("Username", placeholder="admin", key="user_field")
            pass_input = st.text_input("Password", type="password", placeholder="••••••••", key="pass_field")
            
            if st.button("Sign In"):
                # Safety check for secrets
                if "passwords" in st.secrets:
                    if user_input in st.secrets["passwords"] and pass_input == st.secrets["passwords"][user_input]:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    # Fallback for local testing if secrets.toml is missing
                    if user_input == "admin" and pass_input == "admin123":
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Local Auth: Use admin/admin123 or configure st.secrets")
    return False

# -------------------------------------------------
# CORE LOGIC
# -------------------------------------------------
def analyze_loan(row, months):
    dpd = row[months].fillna(0).astype(float)
    active_indices = dpd[dpd.values >= 0].index # Basic check for active data
    
    df = pd.DataFrame({
        "Month": months.astype(str),
        "DPD": dpd.values,
        "Status": "Active" # Logic can be expanded based on balance
    })
    df["Rolling_3M"] = df["DPD"].rolling(3).mean().fillna(0)
    
    max_d = dpd.max()
    metrics = [
        ("Loan Status", "Active", "Current State"),
        ("Max DPD", f"{int(max_d)} Days", "Peak Risk"),
        ("Risk Tier", "High" if max_d > 90 else "Medium" if max_d > 30 else "Low", "Category")
    ]
    return df, pd.DataFrame(metrics, columns=["Metric", "Value", "Importance"])

# -------------------------------------------------
# MAIN APP FLOW
# -------------------------------------------------
if check_password():
    apply_custom_styling()
    
    # Sidebar
    with st.sidebar:
        st.title("🛡️ Risk Engine")
        uploaded_file = st.file_uploader("Upload Delinquency Excel", type=["xlsx"])
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

    if not uploaded_file:
        # Professional Landing Page
        st.markdown("""
            <div style='text-align: center; padding: 100px 20px;'>
                <h1 style='color: white; font-size: 3rem; font-weight: 800;'>Intelligence Beyond Data.</h1>
                <p style='color: #94a3b8; font-size: 1.2rem; max-width: 700px; margin: 0 auto;'>
                    Upload your portfolio data to generate automated risk assessments, 
                    peak delinquency tracking, and executive PDF reports.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.info("**1. Upload** Your Excel file containing DPD strings.")
        with c2: st.info("**2. Analyze** Real-time trends and rolling averages.")
        with c3: st.info("**3. Export** Professional PDFs for stakeholders.")

    else:
        try:
            raw_data = pd.read_excel(uploaded_file)
            # Basic validation: Expecting Code in col 0, Sanctioned in col 1, Balance in col 2
            codes = raw_data.iloc[:, 0].unique()
            months = raw_data.columns[3:]
            
            tabs = st.tabs([f"Account {c}" for c in codes])
            
            for tab, code in zip(tabs, codes):
                with tab:
                    row = raw_data[raw_data.iloc[:, 0] == code].iloc[0]
                    df, metrics_df = analyze_loan(row, months)
                    
                    st.subheader(f"Analysis for Account: {code}")
                    
                    # Display Metrics
                    cols = st.columns(len(metrics_df))
                    for i, m_row in metrics_df.iterrows():
                        cols[i].metric(m_row['Metric'], m_row['Value'])
                    
                    # Chart
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(df["Month"], df["DPD"], marker='o', label="DPD")
                    ax.plot(df["Month"], df["Rolling_3M"], linestyle='--', label="3M Avg")
                    plt.xticks(rotation=45)
                    plt.legend()
                    st.pyplot(fig)
                    
        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.info("Ensure your Excel follows the format: [Code, Sanctioned, Balance, Month1, Month2...]")
