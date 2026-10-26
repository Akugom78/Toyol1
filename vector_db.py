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
# AUTO-EXTRACT LOGIC (Fixes Live Server Issue)
# ==========================================
def initialize_database():
    """Checks if the DB folder exists. If not, extracts it from the ZIP file."""
    if not os.path.exists(DB_PATH):
        print(f"⚠️ Database folder not found at {DB_PATH}.")
        if os.path.exists(DB_ZIP):
            print(f"🗜️ Found {DB_ZIP}. Extracting database...")
            with zipfile.ZipFile(DB_ZIP, 'r') as zip_ref:
                zip_ref.extractall(current_dir)
            print("✅ Database extracted successfully!")
        else:
            print(f"❌ Error: Neither {DB_PATH} nor {DB_ZIP} found. Creating empty DB.")

# ==========================================
# CORE FUNCTIONS
# ==========================================
def get_chroma_collection():
    """Initializes the ChromaDB client and returns the knowledge collection."""
    # Ensure the database is extracted before connecting
    initialize_database()
    
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)

def get_unique_documents():
    """Fetches all unique document source names from the database metadata."""
    try:
        collection = get_chroma_collection()
        
        # Fetch all metadatas from the collection
        results = collection.get(include=['metadatas'])
        metadatas = results['metadatas']
        
        # Extract unique source filenames
        unique_sources = set()
        for meta in metadatas:
            if meta and 'source' in meta:
                unique_sources.add(meta['source'])
                
        # Return a sorted list of document names
        return sorted(list(unique_sources))
        
    except Exception as e:
        print(f"❌ Error fetching unique documents from DB: {e}")
        return []