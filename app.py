# app.py
import sys
import os
import json
import re

# ==========================================
# CRITICAL: FIX PYTHON PATH FOR STREAMLIT
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ==========================================

# ==========================================
# FIX HUGGING FACE UNAUTHENTICATED WARNING
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
# COPY BUTTON HELPER FUNCTIONS
# ==========================================
def create_copy_button(text_to_copy, button_label="📋 Copy"):
    """Generates an HTML button with JS to copy text to clipboard."""
    safe_text = json.dumps(text_to_copy)[1:-1] 
    
    html = f"""
    <button style="font-size: 0.8em; padding: 4px 8px; border-radius: 4px; border: 1px solid #d1d5db; background-color: #f9fafb; color: #374151; cursor: pointer; margin: 5px 0; transition: all 0.2s;"
            onmouseover="this.style.backgroundColor='#e5e7eb'" onmouseout="this.style.backgroundColor='#f9fafb'"
            onclick="navigator.clipboard.writeText('{safe_text}').then(() => {{ let btn = this; btn.innerText = '✅ Copied!'; btn.style.backgroundColor = '#d1fae5'; btn.style.borderColor = '#10b981'; setTimeout(() => {{ btn.innerText = '{button_label}'; btn.style.backgroundColor = '#f9fafb'; btn.style.borderColor = '#d1d5db'; }}, 2000); }})">
        {button_label}
    </button>
    """
    return html

def inject_quote_copy_buttons(text):
    """Finds markdown blockquotes and injects a copy button after each one."""
    pattern = r'(>\s*\*.*?\*\s*\n\(Source:.*?\))'
    def replacer(match):
        quote_text = match.group(1)
        button_html = create_copy_button(quote_text, "📋 Copy Quote")
        return f"{quote_text}\n\n{button_html}"
    return re.sub(pattern, replacer, text, flags=re.DOTALL)

def extract_all_quotes(text):
    """Extracts all blockquotes into a single string."""
    pattern = r'(>\s*\*.*?\*\s*\n\(Source:.*?\))'
    quotes = re.findall(pattern, text, flags=re.DOTALL)
    return "\n\n---\n\n".join(quotes) if quotes else ""

def extract_corrected_draft(text):
    """Extracts the text after the Corrected Draft header."""
    match = re.search(r'### 📄 CORRECTED DRAFT.*?\n(.*?)(?=### |\Z)', text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text

def extract_audit_and_track_changes(text):
    """Extracts text up to the Corrected Draft header."""
    match = re.search(r'(.*?)(?=### 📄 CORRECTED DRAFT)', text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

# ==========================================
# 1. LOAD CONFIGURATION & AUTHENTICATOR
# ==========================================
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
        
        if st.button("🚪 Logout", use_container_width=True):
            authenticator.logout('Logout', 'main')
            for key in ["authentication_status", "name", "username", "messages", "current_user"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
            
        st.divider()
        
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
                    st.markdown(f"📄 {doc}")
                    
        st.divider()
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # --- CHAT INITIALIZATION ---
    # PROFESSIONAL OVERVIEW GREETING
    dynamic_greeting = f"""Greetings, {name}! I am your Senior Air Traffic Control Professional and Safety Auditor. 

I am ready to assist you with:
• **Q&A & Procedural Lookup**: Immediate, referenced answers grounded in official CAAM, ICAO, and Eurocontrol documentation.
• **Document Drafting & Auditing**: Generating, reviewing, and correcting SRA, HIRA, SOPs, and NOTAMs for strict regulatory compliance.
• **Regulatory Research & Discrepancy Analysis**: Cross-referencing standards to identify gaps, inconsistencies, or operational risks.

How may I assist your operations today?"""

    if st.session_state.get("current_user") != username:
        st.session_state.messages = [{"role": "assistant", "content": dynamic_greeting}]
        st.session_state.current_user = username

    # --- DISPLAY CHAT HISTORY ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                processed_text = inject_quote_copy_buttons(message["content"])
                st.markdown(processed_text, unsafe_allow_html=True)
            else:
                st.markdown(message["content"])

    # --- FILE UPLOADER (AUDITOR MODE) ---
    uploaded_file = st.file_uploader("📎 Attach a document for audit/review (PDF only)", type=["pdf"], key="doc_uploader")
    
    if uploaded_file is not None:
        st.session_state['uploaded_file'] = uploaded_file
        st.info(f"📄 **{uploaded_file.name}** attached. Type your prompt below to begin the audit.")

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
            uploaded_doc_text = None
            
            # Extract text from uploaded PDF if present
            if 'uploaded_file' in st.session_state and st.session_state['uploaded_file'] is not None:
                try:
                    import fitz # PyMuPDF
                    doc = fitz.open(stream=st.session_state['uploaded_file'].read(), filetype="pdf")
                    text_parts = []
                    for page in doc:
                        text_parts.append(page.get_text())
                    uploaded_doc_text = "\n\n--- PAGE BREAK ---\n\n".join(text_parts)
                    st.session_state['uploaded_file'] = None # Clear after processing
                except Exception as e:
                    uploaded_doc_text = f"Error reading PDF: {str(e)}"

            try:
                with st.spinner("🔍 Searching ATC knowledge base..." if not uploaded_doc_text else "🔍 Analyzing uploaded document..."):
                    context, sources = rag_chain.retrieve_context(query)
                
                response_stream = rag_chain.stream_qwen_response(st.session_state.messages, context, sources, uploaded_doc_text)
                
                for chunk in response_stream:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                    
                message_placeholder.markdown(full_response)
                
                # 3. Add Smart Copy Buttons
                st.divider()
                st.markdown(create_copy_button(full_response, "📋 Copy Full Response"), unsafe_allow_html=True)
                
                # Check if it's an Auditor Mode response (has 3 parts)
                if "### 📄 CORRECTED DRAFT" in full_response.upper() or "###  CORRECTED DRAFT (FINAL VERSION)" in full_response.upper():
                    corrected_draft = extract_corrected_draft(full_response)
                    audit_track = extract_audit_and_track_changes(full_response)
                    
                    if corrected_draft:
                        st.markdown(create_copy_button(corrected_draft, "📄 Copy Corrected Draft Only"), unsafe_allow_html=True)
                    if audit_track:
                        st.markdown(create_copy_button(audit_track, "📝 Copy Audit & Track Changes"), unsafe_allow_html=True)
                
                all_quotes = extract_all_quotes(full_response)
                if all_quotes:
                    st.markdown(create_copy_button(all_quotes, "📋 Copy All Quotes"), unsafe_allow_html=True)
                    
                if sources:
                    unique_sources = list(set(sources))
                    st.caption(f"📚 Sources: {', '.join(unique_sources)}")
                    
            except Exception as e:
                error_msg = f"❌ Error querying the AI: {str(e)}"
                message_placeholder.markdown(error_msg)
                full_response = error_msg

        # 4. Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

elif st.session_state.get("authentication_status") is False:
    st.error('❌ Username or password is incorrect. Please try again.')
elif st.session_state.get("authentication_status") is None:
    st.warning('🔒 Please enter your username and password to access the ATC Knowledge Assistant.')