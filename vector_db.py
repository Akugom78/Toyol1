# vector_db.py
import sys
import os

# ==========================================
# CRITICAL: FIX PYTHON PATH
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ==========================================
# FIX HUGGING FACE UNAUTHENTICATED WARNING
# ==========================================
# We set the token in the environment BEFORE importing chromadb or transformers
try:
    import streamlit as st
    # Try to get from Streamlit secrets, fallback to local .env
    hf_token = st.secrets.get("HUGGINGFACE_TOKEN", os.getenv("HUGGINGFACE_TOKEN", ""))
except Exception:
    hf_token = os.getenv("HUGGINGFACE_TOKEN", "")

if hf_token:
    os.environ["HF_TOKEN"] = hf_token
    os.environ["HUGGINGFACE_TOKEN"] = hf_token
# ==========================================

import zipfile
import chromadb
from chromadb.utils import embedding_functions

DB_DIR = "chroma_db"
ZIP_FILE = "chroma_db.zip"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def ensure_database_is_ready():
    """Ultra-fast startup: Unzip pre-baked DB if folder is missing."""
    if not os.path.exists(DB_DIR):
        if os.path.exists(ZIP_FILE):
            print("📦 Unzipping pre-baked database (takes ~2 seconds)...")
            with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
                zip_ref.extractall(DB_DIR)
            print("✅ Database unzipped and ready!")
        else:
            raise FileNotFoundError("❌ Neither chroma_db folder nor chroma_db.zip found!")

def get_chroma_collection(collection_name="atc_documents"):
    ensure_database_is_ready()
    
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    
    return client.get_collection(
        name=collection_name,
        embedding_function=embed_func
    )

def get_db_stats(collection_name="atc_documents"):
    try:
        collection = get_chroma_collection(collection_name)
        return {"count": collection.count()}
    except Exception:
        return {"count": 0}

def get_unique_documents(collection_name="atc_documents"):
    """Returns a sorted list of unique document names in the database."""
    try:
        collection = get_chroma_collection(collection_name)
        results = collection.get(include=["metadatas"])
        if not results or not results['metadatas']:
            return []
        
        unique_docs = sorted(list(set(meta.get('source', 'Unknown') for meta in results['metadatas'])))
        return unique_docs
    except Exception:
        return []