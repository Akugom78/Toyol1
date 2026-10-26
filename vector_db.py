# vector_db.py
import os
import chromadb
import zipfile
import shutil
import streamlit as st

# ==========================================
# CONFIGURATION
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "chroma_db")
DB_ZIP = os.path.join(current_dir, "chroma_db.zip")
COLLECTION_NAME = "atc_knowledge"

# ==========================================
# AUTO-HEAL & UI DIAGNOSTIC LOGIC
# ==========================================
def initialize_database():
    """Ensures the database is extracted and populated. Shows errors in UI."""
    
    # 1. Check ZIP file size to confirm LFS worked
    if os.path.exists(DB_ZIP):
        zip_size = os.path.getsize(DB_ZIP)
        print(f"📦 [DEBUG] chroma_db.zip size: {zip_size} bytes")
        
        if zip_size < 1000000: 
            st.sidebar.error(f" CRITICAL LFS ERROR: ZIP is only {zip_size} bytes! Git LFS failed to upload the real file.")
            return False
    else:
        st.sidebar.error("🚨 CRITICAL: chroma_db.zip not found in repository!")
        return False

    # 2. Extract if folder is missing or empty
    if not os.path.exists(DB_PATH) or not os.listdir(DB_PATH):
        print(f"⚠️ [DEBUG] Database folder missing or empty. Extracting...")
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)
            
        # FIX: Create the target folder first!
        os.makedirs(DB_PATH, exist_ok=True)
            
        try:
            with zipfile.ZipFile(DB_ZIP, 'r') as zip_ref:
                # FIX: Extract DIRECTLY into the chroma_db folder!
                zip_ref.extractall(DB_PATH)
            print(f"✅ [DEBUG] Extraction successful into {DB_PATH}!")
            
            # Debug: List what we just extracted to confirm
            print(f"📂 [DEBUG] Extracted files: {os.listdir(DB_PATH)}")
        except Exception as e:
            st.sidebar.error(f"🚨 EXTRACTION FAILED: {e}")
            return False
                
    # 3. Re-initialize and check count
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    if collection.count() == 0:
        st.sidebar.error(" DATABASE EMPTY: Extracted successfully, but contains 0 chunks. Check build script.")
        return False
    else:
        print(f"✅ [DEBUG] Database loaded with {collection.count()} chunks.")
        return True

# ==========================================
# CORE FUNCTIONS
# ==========================================
def get_chroma_collection():
    """Initializes the ChromaDB client and returns the knowledge collection."""
    initialize_database()
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)

def get_unique_documents():
    """Fetches unique document source names from the database metadata."""
    try:
        collection = get_chroma_collection()
        total_docs = collection.count()
        
        if total_docs == 0:
            return []

        results = collection.get(include=['metadatas'])
        metadatas = results['metadatas']
        
        unique_sources = set()
        for meta in metadatas:
            if meta and 'source' in meta:
                unique_sources.add(meta['source'])
                
        sorted_sources = sorted(list(unique_sources))
        return sorted_sources
        
    except Exception as e:
        print(f"❌ [DEBUG] Error fetching unique documents: {e}")
        return []