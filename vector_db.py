# vector_db.py
import os
import chromadb
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
# AUTO-HEAL LOGIC
# ==========================================
def initialize_database():
    # 1. Check if DB is already healthy
    if os.path.exists(DB_PATH):
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            coll = client.get_or_create_collection(name=COLLECTION_NAME)
            if coll.count() > 0:
                return True
        except Exception:
            pass

    # 2. Extract ZIP using shutil
    if not os.path.exists(DB_ZIP):
        st.sidebar.error(" chroma_db.zip not found!")
        return False

    zip_size = os.path.getsize(DB_ZIP)
    if zip_size < 1000000: 
        st.sidebar.error(f"🚨 LFS ERROR: ZIP is only {zip_size} bytes!")
        return False

    st.sidebar.info("️ Extracting database...")
    
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
        
    try:
        # shutil handles all OS pathing perfectly
        shutil.unpack_archive(DB_ZIP, current_dir)
        st.sidebar.success("✅ Database extracted!")
    except Exception as e:
        st.sidebar.error(f" Extraction failed: {e}")
        return False

    return True

# ==========================================
# CORE FUNCTIONS
# ==========================================
def get_chroma_collection():
    initialize_database()
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)

def get_unique_documents():
    try:
        collection = get_chroma_collection()
        if collection.count() == 0:
            return []

        results = collection.get(include=['metadatas'])
        metadatas = results['metadatas']
        
        unique_sources = set()
        for meta in metadatas:
            if meta and 'source' in meta:
                unique_sources.add(meta['source'])
                
        return sorted(list(unique_sources))
    except Exception as e:
        print(f"❌ Error: {e}")
        return []