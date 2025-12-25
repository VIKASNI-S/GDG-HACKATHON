import streamlit as st
import json
import re
from google import genai
from PIL import Image
import PyPDF2
from datetime import datetime

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Personal Health & Kitchen",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
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
    .recipe-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
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
        padding: 0.5rem 1rem;
        font-weight: bold;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# GEMINI INITIALIZATION
# --------------------------------------------------
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-3-flash-preview"

# --------------------------------------------------
# SESSION STATE INITIALIZATION
# --------------------------------------------------
if "clinical_data" not in st.session_state:
    st.session_state.clinical_data = None
if "clinical_history" not in st.session_state:
    st.session_state.clinical_history = []
if "ingredient_images" not in st.session_state:
    st.session_state.ingredient_images = []
if "recipe_history" not in st.session_state:
    st.session_state.recipe_history = []

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
with st.sidebar:
    st.markdown("### 🏥 Health Profile Status")
    
    if st.session_state.clinical_data:
        st.success("✅ Medical Profile Active")
        
        data = st.session_state.clinical_data
        
        if data.get("conditions"):
            st.markdown("**📋 Conditions:**")
            for cond in data["conditions"]:
                st.markdown(f"- {cond}")
        
        if data.get("medications"):
            st.markdown("**💊 Medications:**")
            for med in data["medications"]:
                st.markdown(f"- {med}")
        
        st.markdown("---")
        if st.button("🗑️ Clear Medical Profile"):
            st.session_state.clinical_data = None
            st.rerun()
    else:
        st.warning("⚠️ No Medical Profile Loaded")
        st.info("Upload a medical report in the Medical Analyzer tab to personalize your recipes.")
    
    st.markdown("---")
    st.markdown("### 📊 Statistics")
    st.metric("Reports Analyzed", len(st.session_state.clinical_history))
    st.metric("Recipes Generated", len(st.session_state.recipe_history))
    st.metric("Images Uploaded", len(st.session_state.ingredient_images))

# --------------------------------------------------
# MAIN APP
# --------------------------------------------------
st.markdown('<h1 class="main-header">🧬 Smart Health & Recipe Dashboard</h1>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📄 Medical Analyzer", "🥗 Fridge Scanner", "📚 History"])

# ==================================================
# TAB 1: MEDICAL ANALYZER (ENHANCED)
# ==================================================
with tab1:
    st.markdown("## 🏥 Medical Report Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Upload Your Clinical Report")
        uploaded_file = st.file_uploader(
            "Supported formats: TXT, PDF",
            type=["txt", "pdf"],
            help="Upload your latest medical report for personalized recipe recommendations"
        )
        
        if uploaded_file:
            st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size} bytes)")
            
            # Extract content
            if uploaded_file.type == "text/plain":
                content = uploaded_file.read().decode("utf-8")
            else:
                reader = PyPDF2.PdfReader(uploaded_file)
                content = "\n".join(page.extract_text() or "" for page in reader.pages)
            
            with st.expander("📖 View Raw Content"):
                st.text_area("Document Content", content, height=200)
            
            if st.button("🔍 Analyze & Extract Health Data", type="primary"):
                with st.spinner("🧠 AI is analyzing your clinical markers..."):
                    prompt = """
Extract clinical data and return STRICT JSON ONLY (no markdown, no extra text).

Required format:
{
  "conditions": ["list of medical conditions"],
  "lab_markers": {"marker_name": "value with unit"},
  "medications": ["list of medications"],
  "allergies": ["list of allergies or food restrictions"],
  "dietary_restrictions": ["specific dietary needs"],
  "summary": "brief health summary"
}
"""
                    
                    try:
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=[prompt, content]
                        )
                        
                        # Clean and parse
                        clean = re.sub(r"```json|```", "", response.text).strip()
                        extracted_data = json.loads(clean)
                        
                        # Store in session
                        st.session_state.clinical_data = extracted_data
                        st.session_state.clinical_history.append({
                            "timestamp": datetime.now().isoformat(),
                            "filename": uploaded_file.name,
                            "data": extracted_data
                        })
                        
                        st.success("✅ Health data extracted and saved!")
                        st.balloons()
                        st.rerun()
                        
                    except json.JSONDecodeError:
                        st.error("❌ Could not parse the AI response as JSON")
                        st.code(response.text)
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.markdown("### 💡 Quick Tips")
        st.markdown("""
        <div class="info-card">
        <h4>📝 For Best Results:</h4>
        <ul>
            <li>Upload complete lab reports</li>
            <li>Include medication lists</li>
            <li>Mention any allergies</li>
            <li>Update regularly</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Display current profile
    if st.session_state.clinical_data:
        st.markdown("---")
        st.markdown("### 📋 Current Medical Profile")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            conditions = st.session_state.clinical_data.get("conditions", [])
            st.markdown(f'<div class="metric-box"><h3>{len(conditions)}</h3><p>Conditions</p></div>', unsafe_allow_html=True)
        
        with col2:
            meds = st.session_state.clinical_data.get("medications", [])
            st.markdown(f'<div class="metric-box"><h3>{len(meds)}</h3><p>Medications</p></div>', unsafe_allow_html=True)
        
        with col3:
            markers = st.session_state.clinical_data.get("lab_markers", {})
            st.markdown(f'<div class="metric-box"><h3>{len(markers)}</h3><p>Lab Markers</p></div>', unsafe_allow_html=True)
        
        with st.expander("🔍 View Full Profile Details"):
            st.json(st.session_state.clinical_data)

# ==================================================
# TAB 2: FRIDGE SCANNER (ENHANCED WITH MULTIPLE IMAGES)
# ==================================================
with tab2:
    st.markdown("## 🥗 Smart Kitchen Scanner")
    
    # Health profile status
    if st.session_state.clinical_data:
        st.success("✅ Medical profile active – recipes will be personalized!")
    else:
        st.warning("⚠️ No medical profile found. Recipes will use general healthy guidelines.")
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📸 Upload Ingredient Photos")
        
        # Multiple file uploader
        uploaded_images = st.file_uploader(
            "Upload one or more photos of your ingredients",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="Take photos of your fridge, pantry, or ingredients"
        )
        
        if uploaded_images:
            st.info(f"📷 **{len(uploaded_images)} image(s) uploaded**")
            
            # Display thumbnails
            cols = st.columns(min(len(uploaded_images), 4))
            for idx, img_file in enumerate(uploaded_images):
                with cols[idx % 4]:
                    img = Image.open(img_file)
                    st.image(img, caption=img_file.name, use_container_width=True)
        
        # Alternative: Camera input
        st.markdown("#### Or Use Camera")
        camera_photo = st.camera_input("📸 Take a photo")
        
        if camera_photo:
            st.image(camera_photo, caption="Camera Capture", use_container_width=True)
    
    with col2:
        st.markdown("### ⚙️ Recipe Preferences")
        
        cuisine_type = st.multiselect(
            "Preferred Cuisines",
            ["Italian", "Indian", "Chinese", "Mexican", "Mediterranean", "Japanese", "Thai", "American"],
            help="Select your preferred cuisine styles"
        )
        
        meal_type = st.selectbox(
            "Meal Type",
            ["Dinner", "Lunch", "Breakfast", "Snack", "Dessert"]
        )
        
        num_recipes = st.slider(
            "Number of Recipes",
            min_value=3,
            max_value=15,
            value=10,
            help="How many recipe suggestions do you want?"
        )
        
        cooking_time = st.select_slider(
            "Max Cooking Time",
            options=["15 min", "30 min", "45 min", "1 hour", "1+ hours"],
            value="45 min"
        )
    
    st.markdown("---")
    
    # Generate recipes button
    images_to_process = []
    
    if uploaded_images:
        images_to_process.extend([Image.open(img) for img in uploaded_images])
    if camera_photo:
        images_to_process.append(Image.open(camera_photo))
    
    if images_to_process and st.button("🍽️ Generate Personalized Recipes", type="primary"):
        with st.spinner("👨‍🍳 Chef Gemini is crafting your personalized recipes..."):
            
            health_context = json.dumps(
                st.session_state.clinical_data or {"note": "No medical profile - using general healthy guidelines"},
                indent=2
            )
            
            cuisine_filter = f"\nPreferred cuisines: {', '.join(cuisine_type)}" if cuisine_type else ""
            
            recipe_prompt = f"""
You are a professional medical nutritionist and chef with expertise in personalized meal planning.

TASK:
1. Carefully identify ALL ingredients visible in the provided images
2. Consider the medical profile below to avoid contraindications
3. Suggest {num_recipes} HEALTHY {meal_type.lower()} recipes that can be made with these ingredients
4. Each recipe should take no more than {cooking_time} to prepare{cuisine_filter}

MEDICAL PROFILE:
{health_context}

For EACH recipe, provide:
- **Recipe Name** (creative and appetizing)
- **Ingredients List** (from the images)
- **Medical Benefits** (how it supports their health conditions)
- **Preparation Time**
- **Cooking Instructions** (step-by-step, clear)
- **Chef's Tip** (pro technique or substitution)
- **Nutritional Highlights** (key nutrients)

Format each recipe clearly with headers and bullet points for easy reading.
"""
            
            try:
                # Prepare content list
                content_parts = [recipe_prompt] + images_to_process
                
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=content_parts
                )
                
                # Store in history
                st.session_state.recipe_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "num_images": len(images_to_process),
                    "recipes": response.text
                })
                
                st.markdown("---")
                st.markdown("## 🍳 Your Personalized Recipes")
                st.markdown(response.text)
                
                # Download option
                st.download_button(
                    label="📥 Download Recipes",
                    data=response.text,
                    file_name=f"recipes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ Error generating recipes: {str(e)}")
    
    elif not images_to_process:
        st.info("👆 Please upload ingredient photos or take a picture to get started!")

# ==================================================
# TAB 3: HISTORY
# ==================================================
with tab3:
    st.markdown("## 📚 Your Health & Recipe History")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏥 Medical Reports History")
        if st.session_state.clinical_history:
            for idx, record in enumerate(reversed(st.session_state.clinical_history)):
                with st.expander(f"📄 {record['filename']} - {record['timestamp'][:10]}"):
                    st.json(record['data'])
                    if st.button(f"📋 Load This Profile", key=f"load_{idx}"):
                        st.session_state.clinical_data = record['data']
                        st.success("✅ Profile loaded!")
                        st.rerun()
        else:
            st.info("No medical reports analyzed yet.")
    
    with col2:
        st.markdown("### 🍽️ Recipe History")
        if st.session_state.recipe_history:
            for idx, record in enumerate(reversed(st.session_state.recipe_history)):
                with st.expander(f"🥗 {record['timestamp'][:10]} - {record['num_images']} images"):
                    st.markdown(record['recipes'])
        else:
            st.info("No recipes generated yet.")
    
    st.markdown("---")
    if st.button("🗑️ Clear All History", type="secondary"):
        if st.checkbox("⚠️ Are you sure? This cannot be undone."):
            st.session_state.clinical_history = []
            st.session_state.recipe_history = []
            st.session_state.ingredient_images = []
            st.success("✅ History cleared!")
            st.rerun()

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>🧬 Smart Health & Recipe Dashboard | Powered by Gemini AI</p>
    <p style='font-size: 0.8rem;'>⚠️ This tool is for informational purposes only. Always consult healthcare professionals for medical advice.</p>
</div>
""", unsafe_allow_html=True)
