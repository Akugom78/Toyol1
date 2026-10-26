# build_database.py
import os
import chromadb
import hashlib
import pymupdf 
import shutil # Added for robust zipping

# ==========================================
# CONFIGURATION
# ==========================================
RAW_FOLDER = "data/raw_documents" 
DB_FOLDER = "chroma_db"
DB_ZIP = "chroma_db" # shutil will automatically add .zip
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# ==========================================
# EXTRACTION FUNCTIONS
# ==========================================
def extract_text_from_pdf(pdf_path):
    try:
        doc = pymupdf.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
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

# ==========================================
# CHUNKING LOGIC
# ==========================================
def chunk_text(text, source, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append({
            "text": chunk,
            "source": source,
            "chunk_id": hashlib.md5(f"{source}_{start}".encode()).hexdigest()
        })
        start += chunk_size - chunk_overlap
    return chunks

# ==========================================
# MAIN BUILD PROCESS
# ==========================================
def build_database():
    # 1. Clear existing DB
    if os.path.exists(DB_FOLDER):
        shutil.rmtree(DB_FOLDER)
    
    client = chromadb.PersistentClient(path=DB_FOLDER)
    collection = client.get_or_create_collection(name="atc_knowledge")
    
    all_chunks = []
    files_processed = 0
    
    if not os.path.exists(RAW_FOLDER):
        print(f"❌ Error: Folder '{RAW_FOLDER}' not found.")
        return
        
    print(f"🔍 Scanning '{RAW_FOLDER}'...")
    
    # 2. Process files
    for root, dirs, files in os.walk(RAW_FOLDER):
        for filename in files:
            filepath = os.path.join(root, filename)
            text = ""
            if filename.lower().endswith(".pdf"):
                text = extract_text_from_pdf(filepath)
            elif filename.lower().endswith(".md"):
                text = extract_text_from_md(filepath)
            else:
                continue
                
            if text:
                chunks = chunk_text(text, filename)
                all_chunks.extend(chunks)
                files_processed += 1
                
    print(f" Processed {files_processed} files. Total chunks: {len(all_chunks)}")
        
    # 3. Add to ChromaDB
    if all_chunks:
        print(f"✨ Adding chunks to database...")
        batch_size = 500
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            collection.add(
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"]} for c in batch],
                ids=[c["chunk_id"] for c in batch]
            )
            
    # 4. Create ZIP using shutil (Bulletproof method)
    print("🗜️ Creating ZIP archive...")
    if os.path.exists(f"{DB_ZIP}.zip"):
        os.remove(f"{DB_ZIP}.zip")
        
    # This creates a perfect ZIP where the root is the chroma_db folder
    shutil.make_archive(DB_ZIP, 'zip', DB_FOLDER)
    print(f"✅ SUCCESS! {DB_ZIP}.zip is ready.")

if __name__ == "__main__":
    build_database()