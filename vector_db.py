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
# AUTO-HEAL LOGIC (Destroys Ghost Empty Folders)
# ==========================================
def initialize_database():
    """Ensures the database is extracted and populated."""
    
    # 1. Check if ZIP exists
    if not os.path.exists(DB_ZIP):
        st.sidebar.error("🚨 CRITICAL: chroma_db.zip not found in repository!")
        return False

    zip_size = os.path.getsize(DB_ZIP)
    if zip_size < 1000000: 
        st.sidebar.error(f" CRITICAL LFS ERROR: ZIP is only {zip_size} bytes!")
        return False

    # 2. Check if we need to extract
    needs_extraction = False
    
    if os.path.exists(DB_PATH):
        # Connect to existing DB to check if it's a "ghost" empty folder
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            coll = client.get_or_create_collection(name=COLLECTION_NAME)
            if coll.count() == 0:
                needs_extraction = True
                print(f"⚠️ [DEBUG] Ghost folder detected! DB exists but has 0 chunks. Will extract ZIP.")
            else:
                print(f"✅ [DEBUG] Database is healthy with {coll.count()} chunks. No extraction needed.")
        except Exception as e:
            needs_extraction = True
            print(f"⚠️ [DEBUG] Database is corrupted ({e}). Will extract ZIP.")
    else:
        needs_extraction = True
        print(f"⚠️ [DEBUG] Database folder missing. Will extract ZIP.")

    # 3. Extract the ZIP if needed
    if needs_extraction:
        print(f"️ [DEBUG] Extracting {DB_ZIP} into {DB_PATH}...")
        
        # Destroy the ghost folder completely
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)
            
        # Create fresh folder and extract
        os.makedirs(DB_PATH, exist_ok=True)
        with zipfile.ZipFile(DB_ZIP, 'r') as zip_ref:
            zip_ref.extractall(DB_PATH)
            
        print(f"✅ [DEBUG] Extraction successful!")

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
            st.sidebar.warning("️ Database is empty. Please check build script.")
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