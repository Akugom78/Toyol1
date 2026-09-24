import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from dotenv import load_dotenv
import os
import sys
import os

# ==========================================
# CRITICAL: FIX PYTHON PATH FOR STREAMLIT
# ==========================================
# This ensures Streamlit can always find our local modules (vector_db, rag_chain, etc.)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ==========================================

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
# ... rest of your imports

# ==========================================
# 1. PAGE CONFIG & INITIAL SETUP
# ==========================================
st.set_page_config(
    page_title="ATC Data Assistant", 
    page_icon="✈️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables (API keys)
load_dotenv()

# Load authentication configuration
# Ensure config.yaml is in the same directory as app.py
with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

# ==========================================
# 2. AUTHENTICATION (Updated Syntax for v0.3.x+)
# ==========================================
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Render the login widget (no longer returns a tuple in newer versions)
authenticator.login(location='main')

# Retrieve authentication status from session state
authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

# ==========================================
# 3. MAIN APPLICATION ROUTING
# ==========================================
if authentication_status:
    # --- LOGGED IN STATE ---
    authenticator.logout('Logout', 'sidebar')
    
    # Sidebar UI
    st.sidebar.title(f'Welcome, {name}')
    st.sidebar.write(f'Role: {"System Administrator" if username == "admin" else "ATC Controller"}')
    st.sidebar.markdown("---")
    st.sidebar.info("System Status: Online\nVector DB: Ready\nQwen API: Connected")

    # Main App Title
    st.title("✈️ ATC Data Assistance System")
    st.caption("Powered by Qwen LLM & Hugging Face Embeddings")

    # Main App Tabs
    tab_chat, tab_docs = st.tabs(["💬 RAG Chat Assistant", "📄 Document Generator"])

        # --- TAB 1: RAG CHAT INTERFACE ---
    with tab_chat:
        st.subheader("Ask questions about ATC Manuals, NOTAMs, and SOPs")
        
        # Import the RAG chain
        import rag_chain
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat messages from history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                # If it's an assistant message, show the sources it used
                if message["role"] == "assistant" and "sources" in message:
                    st.caption(f"📚 Sources: {', '.join(message['sources'])}")

        # React to user input
        if prompt := st.chat_input("Ask about ATC procedures, equipment status, etc..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Generate response using the RAG pipeline
            with st.chat_message("assistant"):
                with st.spinner("Searching ATC documents and querying Qwen..."):
                    # 1. Retrieve context from Vector DB
                    context, sources = rag_chain.retrieve_context(prompt)
                    
                    if not context.strip():
                        response_text = "I cannot find any relevant information in the current ATC Knowledge Base. Please ensure documents are synced."
                        st.markdown(response_text)
                    else:
                        # 2. Stream the response from Qwen
                        try:
                            response_stream = rag_chain.stream_qwen_response(prompt, context, sources)
                            # st.write_stream handles the typing effect perfectly
                            response_text = st.write_stream(response_stream) 
                        except Exception as e:
                            response_text = f"An error occurred while querying the AI: {str(e)}"
                            st.error(response_text)
            
            # Add assistant response to chat history (including sources for citation)
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_text,
                "sources": sources if context.strip() else []
            })

    # --- TAB 2: DOCUMENT GENERATOR ---
    with tab_docs:
        st.subheader("Generate Manuals, Shift Reports, and Briefings")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**1. Upload Source Documents**")
            uploaded_files = st.file_uploader(
                "Upload ATC PDFs (Manuals, NOTAMs, Logs)", 
                type="pdf", 
                accept_multiple_files=True
            )
            
            st.markdown("**2. Select Document Type**")
            doc_type = st.selectbox(
                "What do you want to generate?",
                ["Shift Handover Report", "Incident Investigation Manual", "Daily NOTAM Summary", "Custom Report"]
            )
            
            generate_btn = st.button("🚀 Generate Document", type="primary", use_container_width=True)

        with col2:
            st.markdown("**3. Generated Document Preview**")
            if generate_btn:
                with st.spinner("Retrieving context and generating document via Qwen..."):
                    # TODO: Replace with actual PDF generation logic
                    file_count = len(uploaded_files) if uploaded_files else 0
                    st.info(f"*(Placeholder)* Successfully generated a {doc_type} based on {file_count} uploaded files.")
                    st.download_button(
                        label="📥 Download PDF",
                        data=b"Fake PDF data for testing",
                        file_name=f"{doc_type.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.warning("Upload documents and click 'Generate Document' to see the preview here.")

        # --- ADMIN PANEL (Only visible to 'admin' user) ---
    if username == 'admin':
        st.markdown("---")
        st.header("⚙️ Administrator Panel")
        
        admin_tab1, admin_tab2 = st.tabs(["👤 User Management", "📜 Current Users"])
        
        # Import our custom auth manager
        import auth_manager 
        
        # --- TAB 1: ADD NEW USER ---
        with admin_tab1:
            st.subheader("Add a New ATC Controller")
            with st.form("add_user_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username *", placeholder="e.g., controller2")
                    new_name = st.text_input("Full Name *", placeholder="e.g., Ali Bin Abu")
                with col2:
                    new_email = st.text_input("Email *", placeholder="e.g., ali@atc.local")
                    new_password = st.text_input("Temporary Password *", type="password")
                
                submitted = st.form_submit_button("🚀 Create User", type="primary", use_container_width=True)
                
                if submitted:
                    if not new_username or not new_name or not new_email or not new_password:
                        st.error("Please fill in all fields.")
                    else:
                        success, message = auth_manager.add_user(new_username, new_name, new_email, new_password)
                        if success:
                            st.success(message)
                            st.info("⚠️ Note: The new user will need to refresh the page to log in.")
                        else:
                            st.error(message)

        # --- TAB 2: VIEW & DELETE USERS ---
        with admin_tab2:
            st.subheader("Registered Users")
            users = auth_manager.get_all_users()
            
            if not users:
                st.warning("No users found.")
            else:
                for user in users:
                    col_u1, col_u2, col_u3 = st.columns([2, 3, 1])
                    col_u1.text(f"👤 {user['username']}")
                    col_u2.text(f"{user['name']} ({user['email']})")
                    
                    # Disable delete button for the primary admin
                    is_admin = user['username'] == 'admin'
                    with col_u3:
                        if st.button("🗑️ Delete", key=f"del_{user['username']}", disabled=is_admin):
                            # We use a session state flag to handle the deletion on the next rerun
                            st.session_state['user_to_delete'] = user['username']
                            st.rerun()

            # Handle deletion logic (separated to prevent UI rendering issues)
            if 'user_to_delete' in st.session_state and st.session_state['user_to_delete']:
                user_to_del = st.session_state.pop('user_to_delete')
                success, msg = auth_manager.delete_user(user_to_del)
                if success:
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.error(msg)