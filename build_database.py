# build_database.py
import os
import sys
import shutil
import zipfile
import uuid
import re
import chromadb
from chromadb.utils import embedding_functions
import pypdf
import tiktoken

RAW_PDFS_DIR = "data/raw_pdfs"
DB_DIR = "chroma_db"
ZIP_FILE = "chroma_db.zip"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def get_hf_token():
    """Loads HF token from .env or .streamlit/secrets.toml"""
    # 1. Check .env first
    token = os.getenv("HUGGINGFACE_TOKEN")
    if token:
        return token
    
    # 2. Check .streamlit/secrets.toml
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple regex to find the token between quotes
                match = re.search(r'HUGGINGFACE_TOKEN\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        except Exception:
            pass
            
    return ""

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            pdf_reader = pypdf.PdfReader(f)
            return "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def chunk_text(text, chunk_size=500, chunk_overlap=50):
    if not text.strip(): return []
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks, start = [], 0
    while start < len(tokens):
        chunks.append(enc.decode(tokens[start:start + chunk_size]))
        start += (chunk_size - chunk_overlap)
    return chunks

def build_and_zip_database():
    print("=" * 50)
    print("🔨 STARTING LOCAL DATABASE BUILD...")
    print("=" * 50)
    
    # 1. Load and set HF Token to avoid rate limits and speed up downloads
    hf_token = get_hf_token()
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        print("✅ Hugging Face Token loaded. Downloads will be faster and authenticated.")
    else:
        print("⚠️ Warning: No Hugging Face Token found. Downloads may be rate-limited.")

    # 2. Clean up old database
    if os.path.exists(DB_DIR):
        print("🗑️ Cleaning up old chroma_db folder...")
        shutil.rmtree(DB_DIR)
        
    # 3. Initialize ChromaDB
    print("📂 Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    collection = client.get_or_create_collection(
        name="atc_documents",
        embedding_function=embed_func,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 4. Process PDFs
    pdf_files = [f for f in os.listdir(RAW_PDFS_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("❌ No PDFs found in data/raw_pdfs/. Please add some and try again.")
        return

    all_chunks, all_metadata, all_ids = [], [], []
    print(f"📖 Processing {len(pdf_files)} PDFs...")
    
    for pdf_file in pdf_files:
        file_path = os.path.join(RAW_PDFS_DIR, pdf_file)
        print(f"  -> Reading {pdf_file}...")
        text = extract_text_from_pdf(file_path)
        chunks = chunk_text(text)
        
        for chunk in chunks:
            all_chunks.append(chunk)
            all_metadata.append({"source": pdf_file})
            all_ids.append(str(uuid.uuid4()))
            
        print(f"✨ Adding {len(all_chunks)} chunks to database in batches of 500...")
    
    # Process in batches of 500 to avoid ChromaDB's max batch size limit
    batch_size = 500
    for i in range(0, len(all_chunks), batch_size):
        collection.add(
            documents=all_chunks[i:i + batch_size],
            metadatas=all_metadata[i:i + batch_size],
            ids=all_ids[i:i + batch_size]
        )
        print(f"  -> Processed {min(i + batch_size, len(all_chunks))} / {len(all_chunks)} chunks")
        
    print("✅ Database built successfully!")
    
    # 5. Zip the database
    print(f"📦 Compressing {DB_DIR} into {ZIP_FILE}...")
    with zipfile.ZipFile(ZIP_FILE, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(DB_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                # Create an archive name that puts files directly in the root of the zip
                arcname = os.path.relpath(file_path, DB_DIR)
                zipf.write(file_path, arcname)
                
    print(f"🎉 SUCCESS! {ZIP_FILE} is ready to be committed to GitHub.")
    print("=" * 50)

if __name__ == "__main__":
    build_and_zip_database()