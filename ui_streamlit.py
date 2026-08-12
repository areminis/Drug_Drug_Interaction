"""
ui_streamlit.py

Modern Streamlit web interface for the Oncology DDI Chatbot.
Beautiful design with excellent text visibility and user experience.
"""

import streamlit as st
from agents.pipeline import Pipeline


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="Oncology DDI Chatbot | AI-Powered Drug Interaction Analysis",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# CUSTOM CSS STYLING
# ============================================================================
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Global font */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main app background */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
    }
    
    /* Main content area */
    .block-container {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 3rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        margin: 1rem 0 0 0;
        font-size: 1.3rem;
        opacity: 0.95;
        font-weight: 400;
    }
    
    /* Feature cards */
    .feature-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.8rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        color: white;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    
    .feature-card h3 {
        color: white;
        margin-top: 0;
        font-weight: 700;
        font-size: 1.3rem;
    }
    
    .feature-card p {
        color: rgba(255,255,255,0.95);
        line-height: 1.6;
    }
    
    /* Alternate feature card colors */
    .feature-card:nth-child(odd) {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .feature-card:nth-child(even) {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    /* Chat messages - better visibility */
    .stChatMessage {
        background: white !important;
        border-radius: 15px !important;
        padding: 1.5rem !important;
        margin: 1rem 0 !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08) !important;
        border: 1px solid #e0e0e0 !important;
    }
    
    /* User message styling */
    [data-testid="stChatMessageContent"] {
        color: #2c3e50 !important;
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
    }
    
    /* Chat input styling */
    .stChatInput {
        border-radius: 15px !important;
        border: 2px solid #667eea !important;
        background: white !important;
    }
    
    .stChatInput input {
        color: #2c3e50 !important;
        font-size: 1.05rem !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%) !important;
        color: white;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Sidebar section headers */
    [data-testid="stSidebar"] h3 {
        color: white !important;
        font-weight: 700 !important;
        margin-top: 1.5rem !important;
    }
    
    /* Example question buttons */
    .stButton button {
        background: rgba(255,255,255,0.2) !important;
        color: white !important;
        border: 2px solid white !important;
        border-radius: 10px !important;
        padding: 0.8rem 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    
    .stButton button:hover {
        background: white !important;
        color: #667eea !important;
        transform: translateX(5px);
    }
    
    /* Info box in sidebar */
    .stAlert {
        background: rgba(255,255,255,0.15) !important;
        border: 2px solid rgba(255,255,255,0.3) !important;
        border-radius: 12px !important;
        color: white !important;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #666;
        padding: 2rem 1rem;
        margin-top: 3rem;
        border-top: 2px solid #e0e0e0;
        border-radius: 10px;
        background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%);
    }
    
    /* Markdown content in chat - ensure dark text */
    .stMarkdown {
        color: #2c3e50 !important;
    }
    
    .stMarkdown p, .stMarkdown li, .stMarkdown span {
        color: #2c3e50 !important;
    }
    
    /* Code blocks */
    .stMarkdown code {
        background: #f5f5f5 !important;
        color: #e91e63 !important;
        padding: 0.2rem 0.4rem !important;
        border-radius: 4px !important;
    }
    
    /* Horizontal rule */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# INITIALIZE PIPELINE
# ============================================================================
if "PIPELINE" not in st.session_state:
    st.session_state["PIPELINE"] = Pipeline()

PIPELINE = st.session_state["PIPELINE"]


# ============================================================================
# MAIN HEADER
# ============================================================================
st.markdown("""
<div class="main-header">
    <h1>🏥 Oncology DDI Chatbot</h1>
    <p>AI-Powered Drug-Drug Interaction Analysis with Advanced Insights</p>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# SIDEBAR - PROJECT INFO
# ============================================================================
with st.sidebar:
    st.markdown("### 🎯 About This Project")
    
    st.info("""
    **Intelligent Drug Interaction Analysis**
    
    This chatbot helps healthcare professionals analyze potential drug-drug interactions using advanced AI and medical knowledge graphs.
    
    **Powered by:**
    • Neo4j Knowledge Graphs
    • Large Language Models
    • Real Pharmaceutical Data
    """)
    
    st.markdown("---")
    
    # Features
    st.markdown("### ✨ Key Capabilities")
    
    st.markdown("""
    <div class="feature-card">
        <h3>🔍 Drug Interaction Detection</h3>
        <p>Instantly identify potential interactions between medications</p>
    </div>
    
    <div class="feature-card">
        <h3>⚗️ Ingredient-Level Analysis</h3>
        <p>Understand which specific ingredients cause interactions</p>
    </div>
    
    <div class="feature-card">
        <h3>✅ AI-Verified Insights</h3>
        <p>All recommendations validated against medical knowledge base</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Example questions section
    st.markdown("### 💡 Try These Questions")
    
    example_questions = [
        "Does Fluconazole interact with Warfarin?",
        "What happens if I take Warfarin with Ibuprofen?",
        "Is Cisplatin safe with Gentamicin?",
        "What is Paclitaxel used for?",
        "Can I take Digoxin with Furosemide?"
    ]
    
    for i, question in enumerate(example_questions):
        if st.button(question, key=f"example_{i}"):
            st.session_state["selected_example"] = question


# ============================================================================
# CHAT INTERFACE
# ============================================================================

# Initialize chat history with welcome message
if "history" not in st.session_state:
    st.session_state["history"] = []
    st.session_state["history"].append((
        "assistant",
        """👋 **Welcome to the Oncology DDI Chatbot!**

I'm here to help you analyze drug-drug interactions using advanced AI and medical knowledge graphs.

**What I can help with:**

🔍 **Check Drug Interactions** - Find out if two medications interact  
⚗️ **Ingredient Analysis** - See which specific ingredients cause issues  
💊 **Drug Information** - Learn what medications are used for  
✅ **Evidence-Based Insights** - All answers verified against medical data  

**Example Questions:**
- "Does Fluconazole interact with Warfarin?"
- "What is Paclitaxel used for?"
- "Can I combine Methotrexate and Ibuprofen?"

💬 **Type your question below or choose an example from the sidebar!**"""
    ))

# Handle example question selection
if "selected_example" in st.session_state:
    prompt = st.session_state["selected_example"]
    del st.session_state["selected_example"]
    
    st.session_state["history"].append(("user", prompt))
    
    with st.spinner("🔍 Analyzing drug interaction..."):
        answer = PIPELINE.answer(prompt)
    st.session_state["history"].append(("assistant", answer))
    st.rerun()

# Display chat history
for role, msg in st.session_state["history"]:
    with st.chat_message(role, avatar="🏥" if role == "assistant" else "👤"):
        st.markdown(msg.replace("\n", "\n\n"))

# Chat input
prompt = st.chat_input(
    "💬 Ask about drug interactions, uses, or safety concerns...",
    key="chat_input"
)

# Process user input
if prompt:
    st.session_state["history"].append(("user", prompt))
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="🏥"):
        with st.spinner("🔍 Analyzing drug interaction..."):
            answer = PIPELINE.answer(prompt)
        st.markdown(answer.replace("\n", "\n\n"))
    
    st.session_state["history"].append(("assistant", answer))


# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("""
<div class="footer">
    <h3>🏥 Oncology DDI Chatbot</h3>
    <p><strong>Advanced Drug Interaction Analysis for Healthcare Professionals</strong></p>
    <p style="margin-top: 1rem; font-size: 0.95rem;">
        🔬 Powered by AI & Medical Knowledge Graphs • ⚗️ Real Pharmaceutical Data • ✅ Evidence-Based Insights
    </p>
</div>
""", unsafe_allow_html=True)
