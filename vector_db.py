# vector_db.py
import os
import shutil
import zipfile
import chromadb
import streamlit as st

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
                return True
        except Exception as e:
            print(f"Existing DB check failed: {e}")

    # 2. ZIP availability
    if not os.path.isfile(DB_ZIP):
        st.sidebar.error(f"Database ZIP missing: {DB_ZIP}")
        return False

    # 3. Inspect ZIP
    try:
        with zipfile.ZipFile(DB_ZIP, "r") as z:
            names = z.namelist()
            
            # Normalize paths to forward slashes for cross-platform compatibility
            normalized_names = [n.replace("\\", "/") for n in names]
            sqlite_files = [n for n in normalized_names if n.lower().endswith(".sqlite3")]
            
            st.sidebar.write(f"ZIP size: {os.path.getsize(DB_ZIP):,} bytes")
            st.sidebar.write(f"SQLite files found: {sqlite_files[:10]}")

            # Check if chroma.sqlite3 exists inside a chroma_db folder
            valid_sqlite = any(
                n.lower().endswith("chroma.sqlite3") and "chroma_db" in n.lower() 
                for n in normalized_names
            )

            if not valid_sqlite:
                st.sidebar.error("Expected 'chroma_db/chroma.sqlite3' not found inside ZIP.")
                return False

            # Zip-Slip protection: Avoid extracting arbitrary paths
            for name in names:
                target = os.path.realpath(os.path.join(current_dir, name))
                if os.path.commonpath([current_dir, target]) != os.path.realpath(current_dir):
                    st.sidebar.error("Unsafe ZIP path detected.")
                    return False

    except Exception as e:
        st.sidebar.error(f"ZIP inspection failed: {e}")
        return False

    # 4. Restore database
    st.sidebar.info("Restoring ChromaDB...")

    try:
        temp_path = os.path.join(current_dir, "_chroma_restore")
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        os.makedirs(temp_path)

        with zipfile.ZipFile(DB_ZIP, "r") as z:
            z.extractall(temp_path)

        restored_db = os.path.join(temp_path, "chroma_db")

        if not os.path.isfile(os.path.join(restored_db, "chroma.sqlite3")):
            raise FileNotFoundError("chroma.sqlite3 missing after extraction")

        # Replace old DB only after successful extraction
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)

        shutil.move(restored_db, DB_PATH)
        shutil.rmtree(temp_path)

        # 5. Verify ChromaDB
        client = chromadb.PersistentClient(path=DB_PATH)
        coll = client.get_or_create_collection(COLLECTION_NAME)

        st.sidebar.success(f"Database restored. Chunks: {coll.count():,}")
        return True

    except Exception as e:
        st.sidebar.error(f"Database restore failed: {e}")
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