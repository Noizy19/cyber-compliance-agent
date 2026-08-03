import os
import streamlit as st
from dotenv import load_dotenv
import rag_engine

# Load environment variables
load_dotenv()

# Streamlit Page Config
st.set_page_config(
    page_title="Cyber Compliance Agentic Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern Styling
st.markdown("""
<style>
    /* Main Background & Fonts */
    .main {
        background-color: #0e1117;
    }
    
    /* Title Header Styling */
    .main-title {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5 0%, #06B6D4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #9CA3AF;
        margin-bottom: 1.8rem;
    }
    
    /* Metric Card Styling */
    .metric-card {
        background-color: #1F2937;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
    .metric-val {
        font-size: 1.4rem;
        font-weight: bold;
        color: #38BDF8;
    }
    .metric-lbl {
        font-size: 0.8rem;
        color: #9CA3AF;
        text-transform: uppercase;
    }
    
    /* Agent Badges */
    .badge-agent1 {
        background-color: #1E1B4B;
        color: #818CF8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #4338CA;
    }
    .badge-agent2 {
        background-color: #064E3B;
        color: #34D399;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #059669;
    }
    
    /* Result Box Styling */
    .result-box {
        background-color: #111827;
        border-left: 4px solid #10B981;
        padding: 20px;
        border-radius: 6px;
        margin-top: 15px;
    }
    .critique-box {
        background-color: #1E1B4B;
        border-left: 4px solid #818CF8;
        padding: 16px;
        border-radius: 6px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Application Title
st.markdown('<div class="main-title">🛡️ Cyber Compliance Agentic Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Multi-Agent RAG Pipeline powered by <b>Groq (llama-3.1-8b-instant)</b> & <b>OpenRouter (llama-3.3-70b-instruct)</b> over ChromaDB Vector Store</div>',
    unsafe_allow_html=True
)

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/shield.png", width=70)
    st.header("⚙️ Agent Credentials & System")
    
    # Env / Input fallback for Groq API Key
    default_groq = os.getenv("GROQ_API_KEY", "")
    groq_api_key = st.text_input(
        "Groq API Key (Agent 1)",
        value=default_groq,
        type="password",
        help="Used for Agent 1: Router & Fast Retrieval (llama-3.1-8b-instant)"
    )
    
    # Env / Input fallback for OpenRouter API Key
    default_openrouter = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_api_key = st.text_input(
        "OpenRouter API Key (Agent 2)",
        value=default_openrouter,
        type="password",
        help="Used for Agent 2: Advisor & Reflection Critic (meta-llama/llama-3.3-70b-instruct)"
    )
    
    st.divider()
    
    # Index Status & Rebuild Option
    st.subheader("📦 Vector Database")
    if st.button("🔄 Rebuild Policy Vector Store", use_container_width=True):
        with st.spinner("Ingesting policy files and rebuilding Chroma index..."):
            vs, n_docs, n_chunks = rag_engine.build_vectorstore(force_rebuild=True)
            st.success(f"Successfully indexed {n_docs} policies ({n_chunks} text chunks)!")
    
    st.divider()
    
    # Architecture Info Box
    st.markdown("### 🤖 Agent Architecture")
    st.markdown("""
    **Agent 1 (Retriever / Router)**
    - Model: `Groq llama-3.1-8b-instant`
    - Role: Intent analysis, semantic search, context ranking
    
    **Agent 2 (Advisor / Critic)**
    - Model: `OpenRouter llama-3.3-70b-instruct`
    - Role: Policy advice draft & 4-Point self-critique reflection
    """)

# System Metrics Header
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.markdown('<div class="metric-card"><div class="metric-val">20</div><div class="metric-lbl">Active Policies</div></div>', unsafe_allow_html=True)
with col_m2:
    st.markdown('<div class="metric-card"><div class="metric-val">ChromaDB</div><div class="metric-lbl">Vector Store</div></div>', unsafe_allow_html=True)
with col_m3:
    st.markdown('<div class="metric-card"><div class="metric-val">all-MiniLM-L6</div><div class="metric-lbl">Embedding Model</div></div>', unsafe_allow_html=True)
with col_m4:
    st.markdown('<div class="metric-card"><div class="metric-val">2 Agents</div><div class="metric-lbl">Reflection Architecture</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Initialize session state for query if not present
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

# Sample Query Presets
st.markdown("##### 💡 Sample Compliance Queries:")
col1, col2, col3, col4 = st.columns(4)

if col1.button("🔒 MFA & Password Rules", use_container_width=True):
    st.session_state.user_query = "What are the password complexity and MFA requirements under ISO 27001?"
if col2.button("🚨 Incident Response SLAs", use_container_width=True):
    st.session_state.user_query = "What is the mandatory timeline for reporting a severe data breach?"
if col3.button("☁️ Cloud & Zero Trust", use_container_width=True):
    st.session_state.user_query = "What are the required controls for Zero Trust cloud access?"
if col4.button("📊 Data Retention & DLP", use_container_width=True):
    st.session_state.user_query = "How long must security audit logs be retained according to NIST framework?"

# Text Input field bound to session state
user_input = st.text_area(
    "Enter Cybersecurity Compliance Query:",
    value=st.session_state.user_query,
    key="user_query_input",
    height=100,
    placeholder="e.g., What are the mandatory encryption standards for data at rest and data in transit?"
)

run_button = st.button("🚀 Analyze Compliance & Execute Pipeline", type="primary", use_container_width=True)

# Execution Pipeline
if run_button:
    final_query = user_input.strip() or st.session_state.user_query.strip()
    if not final_query:
        st.warning("Please enter a compliance query or select a preset option above.")
    else:
        st.divider()
        
        # Pipeline Progress UI
        with st.status("⚙️ Executing Agentic Compliance Pipeline...", expanded=True) as status:
            st.write("🔍 **Step 1**: Initializing local ChromaDB vector store and querying MiniLM embeddings...")
            
            # Run the agent pipeline
            results = rag_engine.run_compliance_pipeline(
                query=final_query,
                groq_api_key=groq_api_key,
                openrouter_api_key=openrouter_api_key
            )
            
            st.write("🤖 **Step 2 (Agent 1: Router/Retriever)**: Groq `llama-3.1-8b-instant` analyzed query intent and fetched top 4 policy passages.")
            st.write("✍️ **Step 3 (Agent 2: Advisor)**: OpenRouter `meta-llama/llama-3.3-70b-instruct` generated initial compliance draft.")
            st.write("🔬 **Step 4 (Agent 2: Reflection Critic)**: OpenRouter `llama-3.3-70b` performed 4-Point Self-Critique audit & produced refined compliance response.")
            status.update(label="✅ Compliance Pipeline Completed Successfully!", state="complete", expanded=False)

        # Output Display Tabs / Columns
        st.markdown("## 📜 Executive Compliance Report")
        
        # Final Advice Card
        st.markdown('<span class="badge-agent2">Agent 2 Final Output (Refined & Critiqued)</span>', unsafe_allow_html=True)
        st.markdown('<div class="result-box">', unsafe_allow_html=True)
        st.markdown(results["final_advice"])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Expanders for Stage Breakdown & Transparency
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            with st.expander("🔍 Agent 1: Router Analysis & Retrieval Strategy", expanded=False):
                st.markdown('<span class="badge-agent1">Groq llama-3.1-8b-instant</span>', unsafe_allow_html=True)
                st.markdown(results["query_analysis"])
                
            with st.expander("📄 Agent 2: Initial Draft Advice (Pre-Critique)", expanded=False):
                st.markdown(results["draft_advice"])

        with col_exp2:
            with st.expander("🔬 Agent 2: Self-Critique & 4-Point Reflection Audit", expanded=True):
                st.markdown('<div class="critique-box">', unsafe_allow_html=True)
                st.markdown(results["critique"])
                st.markdown('</div>', unsafe_allow_html=True)

        # RAG Source Context Expander
        with st.expander("📚 Retrieved RAG Policy Context (ChromaDB Top Hits)", expanded=False):
            st.markdown(f"**Found {len(results['retrieved_docs'])} relevant policy chunks:**")
            for doc_item in results["retrieved_docs"]:
                st.markdown(f"### 📍 Document Rank #{doc_item['rank']}: `{doc_item['source']}`")
                st.markdown(f"- **Policy ID**: `{doc_item['policy_id']}`")
                st.markdown(f"- **Title**: `{doc_item['title']}`")
                st.markdown(f"- **Similarity Distance Score**: `{doc_item['similarity_score']}`")
                st.code(doc_item["content"], language="text")
                st.divider()

# Footer
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #6B7280; font-size: 0.85rem;">Cybersecurity Compliance Agentic Assistant | Built with Python, Streamlit, ChromaDB, Groq & OpenRouter</div>',
    unsafe_allow_html=True
)
