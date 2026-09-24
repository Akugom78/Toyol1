# app.py
import sys
import os

# ==========================================
# CRITICAL: FIX PYTHON PATH FOR STREAMLIT
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ==========================================

# ==========================================
# FIX HUGGING FACE UNAUTHENTICATED WARNING
# We set the token in the environment BEFORE importing any AI libraries
# ==========================================
import streamlit as st

try:
    hf_token = st.secrets.get("HUGGINGFACE_TOKEN", os.getenv("HUGGINGFACE_TOKEN", ""))
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        os.environ["HUGGINGFACE_TOKEN"] = hf_token
except Exception:
    pass
# ==========================================

import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import vector_db
import rag_chain

# ==========================================
# 1. LOAD CONFIGURATION & AUTHENTICATOR
# ==========================================
# FIX: We use st.session_state instead of @st.cache_resource.
# This prevents the "widget in cache" warning AND the "DuplicateElementKey" crash.
if 'authenticator' not in st.session_state:
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.load(file, Loader=SafeLoader)
    
    st.session_state['authenticator'] = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

authenticator = st.session_state['authenticator']

# ==========================================
# 2. AUTHENTICATION UI
# ==========================================
authenticator.login(location='main')

if st.session_state.get("authentication_status"):
    name = st.session_state.get("name")
    username = st.session_state.get("username")
    
    # ==========================================
    # 3. MAIN APP UI
    # ==========================================
    st.set_page_config(page_title="ATC Knowledge Assistant", page_icon="📘", layout="wide")

    # Clean UI Custom CSS
    st.markdown("""
    <style>
        [data-testid="stDeployButton"] {display: none !important;}
        .stDeployButton {display: none !important;}
        footer {visibility: hidden !important;}
        #MainMenu {visibility: hidden !important;}
        .stApp {max-width: 1200px; margin: 0 auto;}
    </style>
    """, unsafe_allow_html=True)

    st.title("📘 ATC Knowledge Assistant")
    st.caption("Secure, context-aware AI assistance for ATC operations, grounded in official CAAM and ICAO documentation.")
    st.divider()

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {name}")
        st.markdown(f"**Username:** `{username}`")
        st.divider()
        
        # Bulletproof Logout Button
        if st.button("🚪 Logout", use_container_width=True):
            authenticator.logout('Logout', 'main')
            # Explicitly clear the authentication status from session state
            if "authentication_status" in st.session_state:
                del st.session_state["authentication_status"]
            if "name" in st.session_state:
                del st.session_state["name"]
            if "username" in st.session_state:
                del st.session_state["username"]
            st.rerun()
            
        st.divider()
        
        # Collapsible Manual List with Search
        unique_docs = vector_db.get_unique_documents()
        with st.expander(f"📚 Available Documents ({len(unique_docs)})", expanded=False):
            doc_search = st.text_input("🔍 Search manuals:", key="doc_search", placeholder="Type name...")
            if doc_search:
                filtered_docs = [doc for doc in unique_docs if doc_search.lower() in doc.lower()]
            else:
                filtered_docs = unique_docs
                
            if not filtered_docs:
                st.caption("No matching documents.")
            else:
                for doc in filtered_docs:
                    st.markdown(f" {doc}")
                    
        st.divider()
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # --- CHAT INITIALIZATION ---
    # Dynamic greeting based on user name
    dynamic_greeting = f"""Greetings, {name}! I am your Senior Air Traffic Control Professional. 

I can assist you with:
• **Q&A / Procedural Lookup**
• **Document Drafting** (e.g., NOTAMs, SOPs)
• **Regulatory Research**
• **Document Discrepancy Analysis**

How can I help you today?"""

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": dynamic_greeting}]

    # --- DISPLAY CHAT HISTORY ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- USER INPUT & STREAMING RESPONSE ---
    if query := st.chat_input("Ask a procedural question, request a document draft, or analyze a regulation..."):
        # 1. Add user message to history
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        # 2. Generate assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                with st.spinner("🔍 Searching ATC knowledge base..."):
                    context, sources = rag_chain.retrieve_context(query)
                
                # Stream the response, passing the entire chat history
                response_stream = rag_chain.stream_qwen_response(st.session_state.messages, context, sources)
                
                for chunk in response_stream:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                    
                message_placeholder.markdown(full_response)
                
                # Add source citation if context was found
                if sources:
                    unique_sources = list(set(sources))
                    st.caption(f"📚 Sources: {', '.join(unique_sources)}")
                    
            except Exception as e:
                error_msg = f"❌ Error querying the AI: {str(e)}"
                message_placeholder.markdown(error_msg)
                full_response = error_msg

        # 3. Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

elif st.session_state.get("authentication_status") is False:
    st.error('❌ Username or password is incorrect. Please try again.')
elif st.session_state.get("authentication_status") is None:
    st.warning('🔒 Please enter your username and password to access the ATC Knowledge Assistant.')