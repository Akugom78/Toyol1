# vector_db.py
import os
import shutil
import zipfile
import chromadb
import streamlit as st
import time

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
    print(f"📦 [EXTRACT] ZIP path: {DB_ZIP}")

    # 3. Restore database
    st.sidebar.info("Restoring ChromaDB...")
    print("️ [EXTRACT] Starting extraction process...")

    try:
        temp_path = os.path.join(current_dir, "_chroma_restore")
        if os.path.exists(temp_path):
            print(f"🗑️ [EXTRACT] Cleaning up existing temp path: {temp_path}")
            shutil.rmtree(temp_path)
        os.makedirs(temp_path, exist_ok=True)
        print(f" [EXTRACT] Created temp directory: {temp_path}")

        # Extract the ZIP
        print(f"📥 [EXTRACT] Extracting {DB_ZIP} to {temp_path}...")
        with zipfile.ZipFile(DB_ZIP, "r") as z:
            z.extractall(temp_path)
        
        # WAIT for file system sync (critical on cloud environments)
        print("⏳ [EXTRACT] Waiting for file system sync...")
        time.sleep(2)

        # DIAGNOSTIC: List EVERYTHING recursively
        print(f"\n📂 [EXTRACT] === FULL DIRECTORY TREE AFTER EXTRACTION ===")
        for root, dirs, files in os.walk(temp_path):
            level = root.replace(temp_path, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f'{indent}{os.path.basename(root)}/')
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                print(f'{subindent}{file} ({file_size:,} bytes)')
        print(f" [EXTRACT] === END DIRECTORY TREE ===\n")

        # Find chroma.sqlite3 anywhere in the extracted tree
        print("🔍 [EXTRACT] Searching for chroma.sqlite3...")
        sqlite_found = None
        for root, dirs, files in os.walk(temp_path):
            if "chroma.sqlite3" in files:
                sqlite_found = os.path.join(root, "chroma.sqlite3")
                print(f"✅ [EXTRACT] Found chroma.sqlite3 at: {sqlite_found}")
                break
        
        if not sqlite_found:
            error_msg = f"chroma.sqlite3 NOT FOUND. Temp dir contents: {os.listdir(temp_path)}"
            print(f"❌ [EXTRACT] {error_msg}")
            st.sidebar.error(error_msg)
            return False

        # The parent directory of chroma.sqlite3 is our DB directory
        extracted_db_dir = os.path.dirname(sqlite_found)
        print(f" [EXTRACT] Database directory identified: {extracted_db_dir}")
        print(f"📂 [EXTRACT] DB dir contents: {os.listdir(extracted_db_dir)}")

        # Verify it's a valid ChromaDB
        if not os.path.isfile(sqlite_found):
            raise FileNotFoundError(f"chroma.sqlite3 not found at {sqlite_found}")
        
        # Check file size
        sqlite_size = os.path.getsize(sqlite_found)
        print(f" [EXTRACT] chroma.sqlite3 size: {sqlite_size:,} bytes")
        
        if sqlite_size < 1000:
            st.sidebar.warning(f"⚠️ chroma.sqlite3 is very small ({sqlite_size} bytes). Might be corrupted.")

        # Replace old DB only after successful extraction
        if os.path.exists(DB_PATH):
            print(f"🗑️ [EXTRACT] Removing old database: {DB_PATH}")
            shutil.rmtree(DB_PATH)

        # Move the extracted dir to the exact DB_PATH
        print(f"📦 [EXTRACT] Moving {extracted_db_dir} to {DB_PATH}")
        shutil.move(extracted_db_dir, DB_PATH)
        
        # Clean up temp folder
        if os.path.exists(temp_path):
            print(f"️ [EXTRACT] Cleaning up temp folder: {temp_path}")
            shutil.rmtree(temp_path)
            
        print(f"✅ [EXTRACT] Database successfully moved to {DB_PATH}")
        print(f"📂 [EXTRACT] Final DB contents: {os.listdir(DB_PATH)}")

        # 5. Verify ChromaDB
        print("🔍 [VERIFY] Testing ChromaDB connection...")
        client = chromadb.PersistentClient(path=DB_PATH)
        print("🔍 [VERIFY] Getting collection...")
        coll = client.get_or_create_collection(COLLECTION_NAME)
        count = coll.count()
        
        print(f"📊 [SUCCESS] Database loaded with {count:,} chunks!")
        st.sidebar.success(f"Database restored. Chunks: {count:,}")
        
        if count == 0:
            st.sidebar.warning("⚠️ Database has 0 chunks. Check build script.")
            
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