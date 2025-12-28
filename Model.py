import streamlit as st
import json
import re
from google import genai
from PIL import Image
from pypdf import PdfReader
from pyzbar.pyzbar import decode
from datetime import datetime
import os
import pandas as pd

# --------------------------------------------------
# PAGE CONFIG (Only call once!)
# --------------------------------------------------
st.set_page_config(
    page_title="Smart Health & Kitchen",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
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
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
    .warning-box {
        background: linear-gradient(135deg, #ff6b6b 0%, #ffa500 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------
def extract_numeric(text):
    """Extracts the first numeric value from a string."""
    match = re.search(r"[-+]?\d*\.\d+|\d+", str(text))
    return float(match.group()) if match else None

def load_users():
    """Load users from JSON file."""
    if os.path.exists("users.json"):
        with open("users.json") as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file."""
    with open("users.json", "w") as f:
        json.dump(users, f)

def get_barcode_data(image):
    """Detects and decodes barcodes from a PIL image."""
    try:
        decoded_objects = decode(image)
        if decoded_objects:
            return decoded_objects[0].data.decode("utf-8")
    except Exception:
        return None
    return None

def clean_json_response(text):
    """Clean JSON from Gemini response."""
    clean = re.sub(r"```json|```", "", text).strip()
    return json.loads(clean)

# --------------------------------------------------
# LOGIN LOGIC
# --------------------------------------------------
users = load_users()

if 'username' not in st.session_state:
    col_login, col_spacer, col_info = st.columns([1, 0.5, 1])
    
    with col_login:
        st.markdown("## 🔐 Welcome")
        st.subheader("Login to Your Health Dashboard")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 Login", type="primary"):
                if username in users and users[username] == password:
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials.")
        
        with col_btn2:
            if st.button("📝 Sign Up"):
                if username and password and username not in users:
                    users[username] = password
                    save_users(users)
                    st.success("✅ User created! Please login.")
                elif username in users:
                    st.warning("⚠️ Username already exists.")
                else:
                    st.warning("⚠️ Please enter username and password.")
    
    with col_info:
        st.markdown("## 🧬 Features")
        st.markdown("""
        - 📄 **Medical Report Analysis** - Extract health markers from PDFs
        - 🥗 **Smart Fridge Scanner** - AI-powered recipe suggestions
        - 🔍 **Barcode Scanner** - Detect hidden additives in products
        - 📈 **Health Tracking** - Monitor your lab values over time
        """)
    
    st.stop()

# --------------------------------------------------
# GEMINI INITIALIZATION
# --------------------------------------------------
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-3-flash-preview" 

# --------------------------------------------------
# SESSION STATE INITIALIZATION
# --------------------------------------------------
session_keys = {
    "clinical_data": None,
    "clinical_history": [],
    "recipe_history": [],
    "product_scan_history": []
}

for key, default in session_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:
    st.markdown(f"### 👤 Welcome, **{st.session_state.username}**")
    
    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 🏥 Health Profile Status")
    
    if st.session_state.clinical_data:
        st.success("✅ Profile Active")
        
        # Show summary
        data = st.session_state.clinical_data
        if "conditions" in data and data["conditions"]:
            st.markdown("**Conditions:**")
            for cond in data["conditions"][:3]:
                st.markdown(f"- {cond}")
        
        if st.button("🗑️ Clear Profile"):
            st.session_state.clinical_data = None
            st.rerun()
    else:
        st.warning("⚠️ No Profile Loaded")
        st.caption("Upload a medical report to get started.")
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Reports", len(st.session_state.clinical_history))
    with col2:
        st.metric("Recipes", len(st.session_state.recipe_history))

# --------------------------------------------------
# MAIN APP HEADER
# --------------------------------------------------
st.markdown('<h1 class="main-header">🧬 Smart Health & Kitchen Dashboard</h1>', unsafe_allow_html=True)

# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 Medical Analyzer", 
    "🥗 Fridge Scanner", 
    "🔍 Label Scanner",
    "📈 History & Trends"
])

# ==================================================
# TAB 1: MEDICAL ANALYZER
# ==================================================
with tab1:
    st.markdown("## 🏥 Medical Report Analysis")
    st.markdown("Upload your lab reports to extract health markers and build your medical profile.")
    
    uploaded_file = st.file_uploader(
        "Upload Report (PDF/TXT)", 
        type=["txt", "pdf"],
        key="medical_uploader"
    )
    
    if uploaded_file:
        # Extract content
        if uploaded_file.type == "text/plain":
            content = uploaded_file.read().decode("utf-8")
        else:
            reader = PdfReader(uploaded_file)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
        
        # Preview
        with st.expander("📋 Preview Extracted Text"):
            st.text(content[:2000] + "..." if len(content) > 2000 else content)
        
        if st.button("🔍 Analyze & Extract Markers", type="primary", key="analyze_btn"):
            with st.spinner("🧠 AI is analyzing your report..."):
                prompt = """Extract clinical data from this medical report and return STRICT JSON ONLY.
                
Format:
{
    "conditions": ["list of diagnosed conditions"],
    "lab_markers": {"marker_name": "value with units"},
    "medications": ["list of medications"],
    "summary": "brief health summary"
}

Be thorough and extract ALL lab values present."""

                try:
                    response = client.models.generate_content(
                        model=MODEL_ID, 
                        contents=[prompt, content]
                    )
                    extracted_data = clean_json_response(response.text)
                    
                    st.session_state.clinical_data = extracted_data
                    st.session_state.clinical_history.append({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "filename": uploaded_file.name,
                        "data": extracted_data
                    })
                    
                    st.success("✅ Profile Updated Successfully!")
                    
                    # Display results in columns
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 🩺 Conditions")
                        for cond in extracted_data.get("conditions", []):
                            st.markdown(f"- {cond}")
                        
                        st.markdown("### 💊 Medications")
                        for med in extracted_data.get("medications", []):
                            st.markdown(f"- {med}")
                    
                    with col2:
                        st.markdown("### 🔬 Lab Markers")
                        markers = extracted_data.get("lab_markers", {})
                        for marker, value in markers.items():
                            st.markdown(f"**{marker}:** {value}")
                    
                    st.markdown("### 📝 Summary")
                    st.info(extracted_data.get("summary", "No summary available."))
                    
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")

# ==================================================
# TAB 2: FRIDGE SCANNER
# ==================================================
with tab2:
    st.markdown("## 🥗 Smart Kitchen & Micronutrient Gap Analysis")
    st.markdown("Scan your fridge or pantry to get personalized recipe suggestions based on your health profile.")
    
    if not st.session_state.clinical_data:
        st.warning("⚠️ No medical profile found. Recipes will use general health guidelines.")
    
    col_input, col_pref = st.columns([1, 1])
    
    with col_input:
        st.markdown("### 📸 Image Input")
        input_mode = st.radio(
            "Select Image Source:", 
            ["📤 Upload Photos", "📷 Laptop Camera"],
            horizontal=True
        )
        
        fridge_images = []
        
        if input_mode == "📷 Laptop Camera":
            cam_img = st.camera_input("Scan your fridge/pantry")
            if cam_img:
                fridge_images = [Image.open(cam_img)]
        else:
            files = st.file_uploader(
                "Upload pantry photos", 
                type=["jpg", "png", "jpeg"],
                accept_multiple_files=True,
                key="fridge_uploader"
            )
            if files:
                fridge_images = [Image.open(f) for f in files]
                
                # Show thumbnails
                cols = st.columns(min(len(fridge_images), 4))
                for i, img in enumerate(fridge_images[:4]):
                    with cols[i]:
                        st.image(img, use_container_width=True)
    
    with col_pref:
        st.markdown("### 🍽️ Preferences")
        cuisine = st.multiselect(
            "Preferred Cuisines", 
            ["Indian", "Italian", "Mexican", "Mediterranean", "Asian", "American"],
            default=["Indian"]
        )
        meal = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
        dietary = st.multiselect(
            "Dietary Restrictions",
            ["Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Low-Carb", "Keto"]
        )
    
    if fridge_images and st.button("🍽️ Analyze Gaps & Suggest Recipes", type="primary"):
        with st.spinner("🧠 Analyzing ingredients and calculating nutritional gaps..."):
            health_ctx = json.dumps(st.session_state.clinical_data or {"note": "General health guidelines"})
            dietary_str = ", ".join(dietary) if dietary else "None"
            cuisine_str = ", ".join(cuisine) if cuisine else "Any"
            
            prompt = f"""Analyze these kitchen/fridge images and provide personalized recommendations.

HEALTH PROFILE: {health_ctx}
DIETARY RESTRICTIONS: {dietary_str}
PREFERRED CUISINES: {cuisine_str}
MEAL TYPE: {meal}

Please provide:

## 1. 🥬 Detected Ingredients
List all visible ingredients in the images.

## 2. 🔍 Nutritional Gap Analysis
Based on the health profile, identify:
- What nutrients might be deficient
- What's missing from the fridge that the user NEEDS

## 3. 🛒 Smart Shopping Suggestions
List 3-5 items the user should buy to fill nutritional gaps.

## 4. 👨‍🍳 Personalized Recipes
Suggest 3 {meal} recipes that:
- Use the available ingredients
- Address nutritional gaps
- Respect dietary restrictions
- Match cuisine preferences

For each recipe include:
- **Name**
- **Ingredients** (mark which are available vs. need to buy)
- **Quick Instructions**
- **Health Benefits** (specific to user's conditions)
"""
            
            try:
                response = client.models.generate_content(
                    model=MODEL_ID, 
                    contents=[prompt] + fridge_images
                )
                
                st.markdown("---")
                st.markdown(response.text)
                
                st.session_state.recipe_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "meal": meal,
                    "content": response.text
                })
                
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")

# ==================================================
# TAB 3: BARCODE & LABEL SCANNER
# ==================================================
with tab3:
    st.markdown("## 🔍 Barcode & Label Deep Dive")
    st.markdown("Scan product labels to uncover hidden additives and find healthier alternatives.")
    
    col_scan, col_results = st.columns([1, 1])
    
    with col_scan:
        st.markdown("### 📸 Scan Product")
        
        scan_mode = st.radio(
            "Input Method:",
            ["📤 Upload Image", "📷 Camera"],
            horizontal=True,
            key="scan_mode"
        )
        
        product_image = None
        
        if scan_mode == "📷 Camera":
            cam_shot = st.camera_input("Point at product label or barcode")
            if cam_shot:
                product_image = Image.open(cam_shot)
        else:
            uploaded_product = st.file_uploader(
                "Upload product label/barcode image",
                type=["jpg", "png", "jpeg"],
                key="product_uploader"
            )
            if uploaded_product:
                product_image = Image.open(uploaded_product)
        
        if product_image:
            st.image(product_image, caption="Product Image", use_container_width=True)
            
            # Try to decode barcode
            barcode_id = get_barcode_data(product_image)
            if barcode_id:
                st.success(f"✅ Barcode Detected: `{barcode_id}`")
            else:
                st.info("ℹ️ No barcode detected - will analyze label visually")
    
    with col_results:
        if product_image:
            if st.button("🔬 Analyze Product", type="primary", key="analyze_product"):
                with st.spinner("🧠 Analyzing ingredients and additives..."):
                    barcode_id = get_barcode_data(product_image)
                    medical_context = st.session_state.clinical_data or {}
                    
                    prompt = f"""Analyze this food product image thoroughly.

BARCODE: {barcode_id if barcode_id else "Not detected - analyze via visual label"}
USER HEALTH PROFILE: {json.dumps(medical_context)}

Provide a comprehensive analysis:

## 1. 🏷️ Product Identification
- Product name and brand (if visible)
- Category and serving size

## 2. ⚠️ Hidden Additive Warning
Scan for and warn about:
- Hidden sugars (maltodextrin, dextrose, high fructose corn syrup, etc.)
- High sodium content
- Harmful additives (MSG, nitrates, nitrites, artificial colors, preservatives)
- Trans fats or partially hydrogenated oils

## 3. 🏥 Clinical Conflict Alert
Based on the user's health profile, specifically warn if:
- Any ingredient conflicts with their conditions
- Any additive could worsen their health markers
- Serving size would exceed recommended limits

## 4. 📊 Nutrition Score
Rate this product: ⭐ to ⭐⭐⭐⭐⭐
Explain the rating.

## 5. ✅ Healthier Alternatives
Suggest 3 specific, store-available alternatives that are:
- Lower in problematic ingredients
- Better suited to user's health profile
- Similar in taste/function
"""
                    
                    try:
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=[prompt, product_image]
                        )
                        
                        st.markdown("### 📋 Analysis Results")
                        st.markdown("---")
                        st.markdown(response.text)
                        
                        # Save to history
                        st.session_state.product_scan_history.append({
                            "timestamp": datetime.now().isoformat(),
                            "barcode": barcode_id,
                            "analysis": response.text
                        })
                        
                    except Exception as e:
                        st.error(f"❌ Analysis failed: {e}")
        else:
            st.markdown("### 📋 Analysis Results")
            st.info("👈 Upload or capture a product image to analyze")

# ==================================================
# TAB 4: HISTORY & TRENDS
# ==================================================
with tab4:
    st.markdown("## 📈 Progressive Health Tracking")
    
    # --------------------------------------------------
    # LAB MARKER TRENDS
    # --------------------------------------------------
    if st.session_state.clinical_history:
        st.markdown("### 📊 Lab Marker Trends")
        
        # Prepare data for charting
        all_markers = []
        for entry in st.session_state.clinical_history:
            date = entry["timestamp"]
            markers = entry["data"].get("lab_markers", {})
            for m_name, m_val in markers.items():
                num_val = extract_numeric(m_val)
                if num_val is not None:
                    all_markers.append({
                        "Date": date, 
                        "Marker": m_name.lower().strip(), 
                        "Value": num_val
                    })
        
        if all_markers:
            df = pd.DataFrame(all_markers)
            unique_markers = df["Marker"].unique()
            
            selected_marker = st.selectbox(
                "Select a marker to track over time:", 
                unique_markers
            )
            
            plot_df = df[df["Marker"] == selected_marker].sort_values("Date")
            
            col_chart, col_stats = st.columns([2, 1])
            
            with col_chart:
                st.subheader(f"📈 {selected_marker.title()} Over Time")
                st.line_chart(data=plot_df, x="Date", y="Value", height=300)
            
            with col_stats:
                st.subheader("📊 Statistics")
                if len(plot_df) > 1:
                    first_val = plot_df["Value"].iloc[0]
                    last_val = plot_df["Value"].iloc[-1]
                    diff = last_val - first_val
                    percent = (diff / first_val) * 100 if first_val != 0 else 0
                    
                    st.metric(
                        label="Current Value",
                        value=f"{last_val:.1f}",
                        delta=f"{percent:.1f}%"
                    )
                    st.metric(label="First Reading", value=f"{first_val:.1f}")
                    st.metric(label="Total Readings", value=len(plot_df))
                else:
                    st.info("Upload more reports to see trends")
        else:
            st.info("No numeric markers found in your reports yet.")
    else:
        st.info("📄 Upload medical reports in the Medical Analyzer tab to track your health over time.")
    
    st.markdown("---")
    
    # --------------------------------------------------
    # HISTORY SECTIONS
    # --------------------------------------------------
    col_h1, col_h2, col_h3 = st.columns(3)
    
    with col_h1:
        st.markdown("### 📄 Report History")
        if st.session_state.clinical_history:
            for record in reversed(st.session_state.clinical_history):
                with st.expander(f"📋 {record['timestamp']} - {record.get('filename', 'Report')}"):
                    st.json(record['data'])
        else:
            st.caption("No reports uploaded yet.")
    
    with col_h2:
        st.markdown("### 🥗 Recipe History")
        if st.session_state.recipe_history:
            for rec in reversed(st.session_state.recipe_history):
                with st.expander(f"🍽️ {rec.get('meal', 'Recipe')} - {rec['timestamp'][:10]}"):
                    st.markdown(rec.get('content', rec.get('recipes', '')))
        else:
            st.caption("No recipes generated yet.")
    
    with col_h3:
        st.markdown("### 🔍 Product Scans")
        if st.session_state.product_scan_history:
            for scan in reversed(st.session_state.product_scan_history):
                barcode_label = scan.get('barcode', 'Visual Scan') or 'Visual Scan'
                with st.expander(f"🏷️ {barcode_label} - {scan['timestamp'][:10]}"):
                    st.markdown(scan['analysis'])
        else:
            st.caption("No products scanned yet.")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    🧬 <strong>Smart Health & Kitchen Dashboard</strong> | 
    Powered by AI | 
    <em>Always consult a healthcare professional for medical advice.</em>
</div>
""", unsafe_allow_html=True)
