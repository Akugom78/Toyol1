# vector_db.py
import os
import chromadb

# ==========================================
# CONFIGURATION
# ==========================================
# Get the directory where this script is located to ensure the path is always correct
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "chroma_db")
COLLECTION_NAME = "atc_knowledge"

# ==========================================
# CORE FUNCTIONS
# ==========================================
def get_chroma_collection():
    """Initializes the ChromaDB client and returns the knowledge collection."""
    # Ensure the folder exists to prevent crashes on first load
    if not os.path.exists(DB_PATH):
        print(f"⚠️ Warning: Database folder not found at {DB_PATH}. Creating empty collection.")
        
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)

def get_unique_documents():
    """Fetches all unique document source names from the database metadata."""
    try:
        collection = get_chroma_collection()
        
        # Fetch all metadatas from the collection
        # We only request 'metadatas' to keep the query fast and lightweight
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