# vector_db.py
import os
import glob
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
# SMART HUNTER EXTRACTION LOGIC
# ==========================================
def initialize_database():
    """Extracts the ZIP and hunts for the database files regardless of folder structure."""
    
    # 1. Check ZIP file
    if not os.path.exists(DB_ZIP):
        st.sidebar.error("🚨 CRITICAL: chroma_db.zip not found!")
        return False

    zip_size = os.path.getsize(DB_ZIP)
    if zip_size < 1000000: 
        st.sidebar.error(f"🚨 LFS ERROR: ZIP is only {zip_size} bytes! Git LFS failed.")
        return False

    # 2. Check if current DB is already healthy
    if os.path.exists(DB_PATH):
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            coll = client.get_or_create_collection(name=COLLECTION_NAME)
            if coll.count() > 0:
                print(f"✅ [DEBUG] Database is healthy with {coll.count()} chunks.")
                return True
        except Exception:
            pass # Corrupted, needs rebuild

    print(f"⚠️ [DEBUG] Database missing, empty, or corrupted. Hunting for DB files in ZIP...")

    # 3. Extract to a temporary folder
    temp_dir = os.path.join(current_dir, "temp_db_extract")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    try:
        with zipfile.ZipFile(DB_ZIP, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        print(f"✅ [DEBUG] ZIP extracted to temp folder.")
    except Exception as e:
        st.sidebar.error(f"🚨 ZIP EXTRACTION FAILED: {e}")
        return False

    # 4. HUNT for the .sqlite3 file anywhere in the extracted folder
    sqlite_files = glob.glob(os.path.join(temp_dir, "**/*.sqlite3"), recursive=True)
    
    if not sqlite_files:
        st.sidebar.error("🚨 Could not find ANY .sqlite3 database file inside the ZIP!")
        return False

    # 5. Move the found database files to the final destination
    db_root_folder = os.path.dirname(sqlite_files[0])
    print(f"🎯 [DEBUG] Found database files in: {db_root_folder}")

    # Clean up destination and create fresh
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
    os.makedirs(DB_PATH, exist_ok=True)

    # Move all files from the found root folder to DB_PATH
    for item in os.listdir(db_root_folder):
        s = os.path.join(db_root_folder, item)
        d = os.path.join(DB_PATH, item)
        shutil.move(s, d)
        
    # Clean up temp folder
    shutil.rmtree(temp_dir)
    print(f"✅ [DEBUG] Database files successfully moved to {DB_PATH}")

    # 6. Verify final count
    client = chromadb.PersistentClient(path=DB_PATH)
    coll = client.get_or_create_collection(name=COLLECTION_NAME)
    print(f"📊 [DEBUG] Final chunk count: {coll.count()}")
    
    if coll.count() == 0:
        st.sidebar.warning("⚠️ Extracted successfully, but database contains 0 chunks.")
    else:
        st.sidebar.success(f"✅ Database loaded successfully: {coll.count()} chunks!")
        
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
        print(f"❌ Error fetching documents: {e}")
        return []