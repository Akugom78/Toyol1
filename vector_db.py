# vector_db.py
import os
import chromadb
import zipfile

# ==========================================
# CONFIGURATION
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "chroma_db")
DB_ZIP = os.path.join(current_dir, "chroma_db.zip")
COLLECTION_NAME = "atc_knowledge"

# ==========================================
# AUTO-EXTRACT LOGIC
# ==========================================
def initialize_database():
    """Checks if the DB folder exists. If not, extracts it from the ZIP file."""
    if not os.path.exists(DB_PATH):
        print(f"️ [DEBUG] Database folder not found at {DB_PATH}.")
        if os.path.exists(DB_ZIP):
            print(f"️ [DEBUG] Found {DB_ZIP}. Extracting database...")
            try:
                with zipfile.ZipFile(DB_ZIP, 'r') as zip_ref:
                    zip_ref.extractall(current_dir)
                print("✅ [DEBUG] Database extracted successfully!")
            except Exception as e:
                print(f"❌ [DEBUG] Failed to extract ZIP: {e}")
        else:
            print(f"❌ [DEBUG] Error: Neither {DB_PATH} nor {DB_ZIP} found. Creating empty DB.")
    else:
        print(f"✅ [DEBUG] Database folder already exists at {DB_PATH}.")

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
        print(f" [DEBUG] Total documents in DB: {total_docs}")
        
        if total_docs == 0:
            return []

        # FIX: Fetch only a limited number of metadatas to prevent memory crashes on Streamlit Cloud
        # 2000 is enough to get all unique filenames without crashing the server
        print(f" [DEBUG] Fetching metadatas (limit 2000)...")
        results = collection.get(include=['metadatas'], limit=2000)
        metadatas = results['metadatas']
        
        unique_sources = set()
        for meta in metadatas:
            if meta and 'source' in meta:
                unique_sources.add(meta['source'])
                
        sorted_sources = sorted(list(unique_sources))
        print(f"✅ [DEBUG] Found {len(sorted_sources)} unique documents.")
        return sorted_sources
        
    except Exception as e:
        print(f"❌ [DEBUG] Error fetching unique documents: {e}")
        import traceback
        traceback.print_exc()
        return []