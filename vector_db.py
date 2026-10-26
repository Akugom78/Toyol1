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
# BULLETPROOF AUTO-HEAL LOGIC
# ==========================================
def initialize_database():
    """Extracts and fixes the database regardless of nested folders."""
    
    # 1. Check ZIP file
    if not os.path.exists(DB_ZIP):
        st.sidebar.error("🚨 CRITICAL: chroma_db.zip not found!")
        return False

    zip_size = os.path.getsize(DB_ZIP)
    if zip_size < 1000000: 
        st.sidebar.error(f"🚨 LFS ERROR: ZIP is only {zip_size} bytes! Git LFS failed.")
        return False

    # 2. Check if current DB is healthy
    if os.path.exists(DB_PATH):
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            coll = client.get_or_create_collection(name=COLLECTION_NAME)
            if coll.count() > 0:
                print(f"✅ [DEBUG] Database is healthy with {coll.count()} chunks.")
                return True
        except Exception:
            pass # Corrupted, needs rebuild

    print(f"⚠️ [DEBUG] Database missing, empty, or corrupted. Rebuilding from ZIP...")

    # 3. Extract to a temporary folder to avoid nested folder issues
    temp_extract = os.path.join(current_dir, "temp_extract")
    if os.path.exists(temp_extract):
        shutil.rmtree(temp_extract)
    os.makedirs(temp_extract)

    try:
        with zipfile.ZipFile(DB_ZIP, 'r') as zip_ref:
            zip_ref.extractall(temp_extract)
        print(f"✅ [DEBUG] Extracted to temp folder.")
    except Exception as e:
        st.sidebar.error(f"🚨 EXTRACTION FAILED: {e}")
        return False

    # 4. Hunt for the actual database folder (handles nested folders)
    source_db_path = None
    
    # Check if it extracted directly into temp_extract
    if os.path.exists(os.path.join(temp_extract, "chroma.sqlite3")):
        source_db_path = temp_extract
    else:
        # Walk through to find chroma.sqlite3
        for root, dirs, files in os.walk(temp_extract):
            if "chroma.sqlite3" in files:
                source_db_path = root
                break

    if not source_db_path:
        st.sidebar.error("🚨 Could not find chroma.sqlite3 in ZIP!")
        return False

    # 5. Move to final destination
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
        
    shutil.move(source_db_path, DB_PATH)
    shutil.rmtree(temp_extract) # Clean up
    
    print(f"✅ [DEBUG] Database successfully moved to {DB_PATH}")

    # 6. Verify final count
    client = chromadb.PersistentClient(path=DB_PATH)
    coll = client.get_or_create_collection(name=COLLECTION_NAME)
    print(f"📊 [DEBUG] Final chunk count: {coll.count()}")
    
    if coll.count() == 0:
        st.sidebar.warning("⚠️ Extracted, but database is empty. Check local build.")
    else:
        st.sidebar.success(f"✅ Database loaded: {coll.count()} chunks!")
        
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