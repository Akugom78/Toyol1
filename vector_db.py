# vector_db.py

# ==========================================
# CRITICAL: SQLite Compatibility Fix for Streamlit Cloud
# This MUST be at the very top, before any other imports!
# ==========================================
try:
    import pysqlite3
    import sys
    sys.modules['sqlite3'] = pysqlite3
    print("✅ [SQLITE] Successfully swapped to pysqlite3")
except ImportError as e:
    print(f"⚠️ [SQLITE] pysqlite3 not available: {e}")

# Now import everything else
import os
import shutil
import zipfile
import streamlit as st
import chromadb

current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "chroma_db")
DB_ZIP = os.path.join(current_dir, "chroma_db.zip")
COLLECTION_NAME = "atc_knowledge"

def initialize_database():
    # 1. Existing database check
    if os.path.isdir(DB_PATH):
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            coll = client.get_or_create_collection(COLLECTION_NAME)
            if coll.count() > 0:
                print(f"✅ [CACHE] Database healthy with {coll.count()} chunks.")
                return True
        except Exception as e:
            print(f"⚠️ Existing DB check failed: {e}. Will rebuild from ZIP.")

    # 2. ZIP availability
    if not os.path.isfile(DB_ZIP):
        st.sidebar.error(f"Database ZIP missing: {DB_ZIP}")
        return False

    zip_size = os.path.getsize(DB_ZIP)
    if zip_size < 1000000: 
        st.sidebar.error(f"🚨 LFS ERROR: ZIP is only {zip_size} bytes. Git LFS failed.")
        return False

    print(f"📦 [EXTRACT] ZIP size: {zip_size:,} bytes")

    # 3. Restore database
    st.sidebar.info("Restoring ChromaDB...")
    print("🛠️ [EXTRACT] Starting extraction process...")

    try:
        temp_path = os.path.join(current_dir, "_chroma_restore")
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        os.makedirs(temp_path, exist_ok=True)

        with zipfile.ZipFile(DB_ZIP, "r") as z:
            z.extractall(temp_path)

        # Find chroma.sqlite3
        expected_db_dir = os.path.join(temp_path, "chroma_db")
        expected_sqlite = os.path.join(expected_db_dir, "chroma.sqlite3")

        sqlite_found = None

        if os.path.isdir(expected_db_dir) and os.path.isfile(expected_sqlite):
            sqlite_found = expected_sqlite
            print(f"✅ [EXTRACT] Found chroma.sqlite3 at exact expected path.")
        else:
            print(f"⚠️ [EXTRACT] Exact path failed. Hunting recursively...")
            if os.path.isdir(expected_db_dir):
                print(f"📂 [EXTRACT] Contents of chroma_db folder: {os.listdir(expected_db_dir)}")
            
            for root, dirs, files in os.walk(temp_path):
                for f in files:
                    if f.lower().endswith('.sqlite3'):
                        sqlite_found = os.path.join(root, f)
                        print(f"🎯 [EXTRACT] Found sqlite file via recursive hunt: {f}")
                        break
                if sqlite_found:
                    break

        if not sqlite_found:
            error_msg = "chroma.sqlite3 NOT FOUND after exhaustive search."
            print(f"❌ [EXTRACT] {error_msg}")
            st.sidebar.error(error_msg)
            return False

        extracted_db_dir = os.path.dirname(sqlite_found)
        print(f"🎯 [EXTRACT] Identified DB directory: {extracted_db_dir}")

        # Replace old DB
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)

        shutil.move(extracted_db_dir, DB_PATH)
        
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
            
        print(f"✅ [EXTRACT] Database successfully moved to {DB_PATH}")

        # 4. Verify ChromaDB (This is where the SQLite error happens)
        print("🔍 [VERIFY] Testing ChromaDB connection...")
        client = chromadb.PersistentClient(path=DB_PATH)
        coll = client.get_or_create_collection(COLLECTION_NAME)
        count = coll.count()
        
        print(f"📊 [SUCCESS] Database loaded with {count:,} chunks!")
        st.sidebar.success(f"Database restored. Chunks: {count:,}")
        
        return True

    except Exception as e:
        error_detail = f"Database restore failed: {e}"
        st.sidebar.error(error_detail)
        print(f"❌ [EXTRACT] Restoration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_chroma_collection():
    if not initialize_database():
        raise RuntimeError("ChromaDB initialization failed")
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(COLLECTION_NAME)

def get_unique_documents():
    try:
        collection = get_chroma_collection()
        results = collection.get(include=["metadatas"])
        
        unique_sources = {
            meta["source"]
            for meta in results["metadatas"]
            if meta and "source" in meta
        }
        return sorted(list(unique_sources))

    except Exception as e:
        print(f"Error fetching documents: {e}")
        return []