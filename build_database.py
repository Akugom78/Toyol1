# build_database.py
import os
import chromadb
import hashlib
import pymupdf 
import shutil

# ==========================================
# CONFIGURATION
# ==========================================
RAW_FOLDER = "data/raw_documents" 
DB_FOLDER = "chroma_db"
DB_ZIP = "chroma_db" # shutil will automatically add .zip
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# ==========================================
# EXTRACTION & CHUNKING
# ==========================================
def extract_text_from_pdf(pdf_path):
    try:
        doc = pymupdf.open(pdf_path)
        return "".join(page.get_text() for page in doc).strip()
    except Exception as e:
        print(f"   ❌ Error reading PDF: {e}")
        return ""

def extract_text_from_md(md_path):
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"   ❌ Error reading MD: {e}")
        return ""

def chunk_text(text, source, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append({
            "text": text[start:end],
            "source": source,
            "chunk_id": hashlib.md5(f"{source}_{start}".encode()).hexdigest()
        })
        start += chunk_size - chunk_overlap
    return chunks

# ==========================================
# MAIN BUILD PROCESS
# ==========================================
def build_database():
    if os.path.exists(DB_FOLDER):
        shutil.rmtree(DB_FOLDER)
    
    client = chromadb.PersistentClient(path=DB_FOLDER)
    collection = client.get_or_create_collection(name="atc_knowledge")
    all_chunks = []
    
    if not os.path.exists(RAW_FOLDER):
        print(f"❌ Error: Folder '{RAW_FOLDER}' not found.")
        return
        
    print(f"🔍 Scanning '{RAW_FOLDER}'...")
    files_processed = 0
    
    for root, dirs, files in os.walk(RAW_FOLDER):
        for filename in files:
            filepath = os.path.join(root, filename)
            text = ""
            if filename.lower().endswith(".pdf"):
                text = extract_text_from_pdf(filepath)
            elif filename.lower().endswith(".md"):
                text = extract_text_from_md(filepath)
                
            if text:
                all_chunks.extend(chunk_text(text, filename))
                files_processed += 1
                
    print(f"✅ Processed {files_processed} files. Total chunks: {len(all_chunks)}")
        
    if all_chunks:
        print(f"✨ Adding chunks to database...")
        for i in range(0, len(all_chunks), 500):
            batch = all_chunks[i:i + 500]
            collection.add(
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"]} for c in batch],
                ids=[c["chunk_id"] for c in batch]
            )

    # ==========================================
    # BULLETPROOF ZIP CREATION
    # ==========================================
    zip_path = f"{DB_ZIP}.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    print("🗜️ Creating ZIP archive with 'chroma_db' as root folder...")
    
    # This ensures the ZIP contains: chroma_db/chroma.sqlite3 (not just chroma.sqlite3 at root)
    shutil.make_archive(
        DB_ZIP,
        'zip',
        root_dir=os.path.dirname(os.path.abspath(__file__)),
        base_dir=DB_FOLDER
    )
    
    print(f"✅ SUCCESS! {zip_path} is ready.")

if __name__ == "__main__":
    build_database()