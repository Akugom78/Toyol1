# build_database.py
import os
import chromadb
import zipfile
import hashlib
import pymupdf 

# ==========================================
# CONFIGURATION
# ==========================================
RAW_FOLDER = "data/raw_documents" 
DB_FOLDER = "chroma_db"
DB_ZIP = "chroma_db.zip"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# ==========================================
# EXTRACTION FUNCTIONS
# ==========================================
def extract_text_from_pdf(pdf_path):
    """Extracts text from standard PDFs."""
    doc = pymupdf.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_md(md_path):
    """Reads text from Markdown files (preserving tables and structure)."""
    with open(md_path, 'r', encoding='utf-8') as f:
        return f.read()

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
        import shutil
        shutil.rmtree(DB_FOLDER)
    
    # In newer ChromaDB versions, PersistentClient saves automatically.
    client = chromadb.PersistentClient(path=DB_FOLDER)
    collection = client.get_or_create_collection(name="atc_knowledge")
    
    all_chunks = []
    
    if not os.path.exists(RAW_FOLDER):
        print(f"❌ Error: Folder '{RAW_FOLDER}' not found. Please check the path.")
        return
        
    # 2. Process all files in the folder
    for filename in os.listdir(RAW_FOLDER):
        filepath = os.path.join(RAW_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue
            
        text = ""
        # Process PDFs
        if filename.lower().endswith(".pdf"):
            print(f"📄 Processing PDF: {filename}")
            text = extract_text_from_pdf(filepath)
        # Process Markdown files
        elif filename.lower().endswith(".md"):
            print(f"📝 Processing Markdown: {filename}")
            text = extract_text_from_md(filepath)
        else:
            continue
            
        if not text.strip():
            print(f"⚠️ Warning: No text extracted from {filename}")
            continue
            
        chunks = chunk_text(text, filename)
        all_chunks.extend(chunks)
        
    # 3. Add to ChromaDB in batches
    if all_chunks:
        print(f"✨ Adding {len(all_chunks)} chunks to database in batches of 500...")
        batch_size = 500
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            collection.add(
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"]} for c in batch],
                ids=[c["chunk_id"] for c in batch]
            )
            print(f"  -> Processed {min(i + batch_size, len(all_chunks))} / {len(all_chunks)} chunks")
            
    # 4. Zip the database (No client.persist() needed anymore)
    print("🗜️ Compressing database...")
    with zipfile.ZipFile(DB_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(DB_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, DB_FOLDER)
                zipf.write(file_path, arcname)
                
    print(f"✅ SUCCESS! {DB_ZIP} is ready with {len(all_chunks)} chunks.")

if __name__ == "__main__":
    build_database()
