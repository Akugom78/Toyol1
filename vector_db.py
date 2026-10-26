# vector_db.py
import os
import chromadb
import zipfile
import shutil

# ==========================================
# CONFIGURATION
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "chroma_db")
DB_ZIP = os.path.join(current_dir, "chroma_db.zip")
COLLECTION_NAME = "atc_knowledge"

# ==========================================
# AUTO-HEAL & DIAGNOSTIC LOGIC
# ==========================================
def initialize_database():
    """Ensures the database is extracted and populated."""
    
    # 1. Check ZIP file size to confirm LFS worked
    if os.path.exists(DB_ZIP):
        zip_size = os.path.getsize(DB_ZIP)
        print(f"📦 [DEBUG] chroma_db.zip size: {zip_size} bytes")
        if zip_size < 1000000: # Less than 1MB
            print(f"❌ [DEBUG] WARNING: ZIP file is too small! Git LFS likely failed to upload the real file.")
    else:
        print(f"❌ [DEBUG] chroma_db.zip not found!")

    # 2. Extract if folder is missing or empty
    if not os.path.exists(DB_PATH) or not os.listdir(DB_PATH):
        print(f"⚠️ [DEBUG] Database folder missing or empty. Extracting...")
        if os.path.exists(DB_PATH):
            shutil.rmtree(DB_PATH)
            
        if os.path.exists(DB_ZIP):
            try:
                with zipfile.ZipFile(DB_ZIP, 'r') as zip_ref:
                    zip_ref.extractall(current_dir)
                print("✅ [DEBUG] Extraction successful!")
            except Exception as e:
                print(f"❌ [DEBUG] Failed to extract ZIP: {e}")
                
    # 3. DIAGNOSTIC: List files inside the extracted folder
    if os.path.exists(DB_PATH):
        print(f"📂 [DEBUG] Contents of '{DB_PATH}':")
        for item in os.listdir(DB_PATH):
            print(f"   - {item}")
    else:
        print(f"❌ [DEBUG] Extraction failed, folder still missing.")

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
        print(f"📊 [DEBUG] Total chunks in DB: {total_docs}")
        
        if total_docs == 0:
            return []

        results = collection.get(include=['metadatas'])
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
        return []