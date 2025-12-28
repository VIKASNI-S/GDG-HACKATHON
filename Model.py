
import streamlit as st
import json
import re
from google import genai
from PIL import Image

from pypdf import PdfReader
from datetime import datetime
import os
import pandas as pd

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Personal Health & Kitchen",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(120deg, #84fab0 0%, #8fd3f4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 1rem 0;
    }
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
    }
    .metric-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        font-weight: bold;
        border: none;
        transition: all 0.3s;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------
def extract_numeric(text):
    """Extracts the first numeric value from a string (e.g., '120 mg/dL' -> 120.0)."""
    match = re.search(r"[-+]?\d*\.\d+|\d+", str(text))
    return float(match.group()) if match else None

def load_users():
    if os.path.exists("users.json"):
        with open("users.json") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

# --------------------------------------------------
# LOGIN LOGIC
# --------------------------------------------------
users = load_users()
if 'username' not in st.session_state:
    st.subheader("User Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users and users[username] == password:
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid credentials.")
    if st.button("Sign Up"):
        if username and password and username not in users:
            users[username] = password
            save_users(users)
            st.success("User created!")
    st.stop()

# --------------------------------------------------
# GEMINI INITIALIZATION
# --------------------------------------------------
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-2.0-flash" # Updated to newest available stable

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
for key in ["clinical_data", "clinical_history", "ingredient_images", "recipe_history"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "history" in key or "images" in key else None

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 Welcome, {st.session_state.username}")
    if st.button("Logout"):
        del st.session_state.username
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 🏥 Health Profile Status")
    if st.session_state.clinical_data:
        st.success("✅ Profile Active")
        if st.button("🗑️ Clear Profile"):
            st.session_state.clinical_data = None
            st.rerun()
    else:
        st.warning("⚠️ No Profile Loaded")

# --------------------------------------------------
# MAIN APP TABS
# --------------------------------------------------
st.markdown('<h1 class="main-header">🧬 Smart Health & Recipe Dashboard</h1>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["📄 Medical Analyzer", "🥗 Fridge Scanner", "📈 Health Trends & History"])

# TAB 1: MEDICAL ANALYZER
with tab1:
    st.markdown("## 🏥 Medical Report Analysis")
    uploaded_file = st.file_uploader("Upload Report (PDF/TXT)", type=["txt", "pdf"])
    
    if uploaded_file:
        if uploaded_file.type == "text/plain":
            content = uploaded_file.read().decode("utf-8")
        else:
            reader = PdfReader(uploaded_file)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)

        
        if st.button("🔍 Analyze & Extract Markers", type="primary"):
            with st.spinner("Analyzing..."):
                prompt = "Extract clinical data and return STRICT JSON ONLY. Format: {'conditions': [], 'lab_markers': {'marker_name': 'value'}, 'medications': [], 'summary': ''}"
                response = client.models.generate_content(model=MODEL_ID, contents=[prompt, content])
                clean = re.sub(r"```json|```", "", response.text).strip()
                extracted_data = json.loads(clean)
                
                st.session_state.clinical_data = extracted_data
                st.session_state.clinical_history.append({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "filename": uploaded_file.name,
                    "data": extracted_data
                })
                st.success("Data added to history!")
                st.rerun()

# TAB 2: FRIDGE SCANNER
with tab2:
    st.markdown("## 🥗 Smart Kitchen Scanner")
    col1, col2 = st.columns(2)
    with col1:
        uploaded_images = st.file_uploader("Upload Pantry Photos", type=["jpg", "png"], accept_multiple_files=True)
    with col2:
        cuisine = st.multiselect("Cuisines", ["Indian", "Italian", "Mexican", "Mediterranean"])
        meal = st.selectbox("Meal", ["Breakfast", "Lunch", "Dinner"])

    if uploaded_images and st.button("🍽️ Generate Recipes", type="primary"):
        images = [Image.open(img) for img in uploaded_images]
        health_context = json.dumps(st.session_state.clinical_data or {"note": "General health guidelines"})
        
        recipe_prompt = f"Using visible ingredients and this health data: {health_context}, suggest 3 {meal} recipes. For each, list Name, Ingredients, and Medical Benefit."
        
        with st.spinner("Cooking up ideas..."):
            response = client.models.generate_content(model=MODEL_ID, contents=[recipe_prompt] + images)
            st.markdown(response.text)
            st.session_state.recipe_history.append({"timestamp": datetime.now().isoformat(), "recipes": response.text})

# TAB 3: HISTORY & TRENDS (THE NEW FEATURE)
with tab3:
    st.markdown("## 📈 Progressive Health Tracking")
    
    if len(st.session_state.clinical_history) >= 1:
        # Prepare Data for Charting
        all_markers = []
        for entry in st.session_state.clinical_history:
            date = entry["timestamp"]
            markers = entry["data"].get("lab_markers", {})
            for m_name, m_val in markers.items():
                num_val = extract_numeric(m_val)
                if num_val is not None:
                    all_markers.append({"Date": date, "Marker": m_name.lower(), "Value": num_val})
        
        if all_markers:
            df = pd.DataFrame(all_markers)
            unique_markers = df["Marker"].unique()
            
            selected_marker = st.selectbox("Select a marker to track over time:", unique_markers)
            
            plot_df = df[df["Marker"] == selected_marker].sort_values("Date")
            
            st.subheader(f"Trend for: {selected_marker.title()}")
            st.line_chart(data=plot_df, x="Date", y="Value")
            
            # Show improvement logic
            if len(plot_df) > 1:
                first_val = plot_df["Value"].iloc[0]
                last_val = plot_df["Value"].iloc[-1]
                diff = last_val - first_val
                percent = (diff / first_val) * 100
                color = "normal" if diff == 0 else ("inverse" if diff > 0 else "normal")
                st.metric(label=f"Total Change in {selected_marker}", value=f"{last_val}", delta=f"{percent:.1f}%")

    st.markdown("---")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        st.markdown("### 📄 Report History")
        for record in reversed(st.session_state.clinical_history):
            with st.expander(f"{record['timestamp']} - {record['filename']}"):
                st.json(record['data'])
    with col_h2:
        st.markdown("### 🥗 Recipe History")
        for rec in reversed(st.session_state.recipe_history):
            with st.expander(f"Recipe Plan - {rec['timestamp'][:10]}"):
                st.markdown(rec['recipes'])

# FOOTER
st.markdown("---")
st.caption("🧬 Smart Health Dashboard | Powered by Gemini 2.0 Flash | Always consult a doctor.")
