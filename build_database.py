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
    """Reads text from Markdown files."""
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
            "source": source, # Just the filename for cleaner UI
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
    
    client = chromadb.PersistentClient(path=DB_FOLDER)
    collection = client.get_or_create_collection(name="atc_knowledge")
    
    all_chunks = []
    files_processed = 0
    files_skipped = 0
    
    if not os.path.exists(RAW_FOLDER):
        print(f"❌ Error: Folder '{RAW_FOLDER}' not found.")
        return
        
    print(f"🔍 Scanning '{RAW_FOLDER}' and all subfolders for PDFs and MDs...\n")
    
    # 2. Process ALL files recursively (including subfolders)
    for root, dirs, files in os.walk(RAW_FOLDER):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            text = ""
            if filename.lower().endswith(".pdf"):
                print(f"📄 Processing: {filename}")
                text = extract_text_from_pdf(filepath)
            elif filename.lower().endswith(".md"):
                print(f"📝 Processing: {filename}")
                text = extract_text_from_md(filepath)
            else:
                continue # Skip non-PDF/MD files
                
            if not text:
                print(f"   ⚠️ SKIPPED: No text extracted (likely an image-only scan or empty file).\n")
                files_skipped += 1
                continue
                
            # Use just the filename for the source metadata to keep the UI clean
            chunks = chunk_text(text, filename)
            all_chunks.extend(chunks)
            files_processed += 1
            print(f"   ✅ Success: Generated {len(chunks)} chunks.\n")
            
    print("-" * 50)
    print(f"📊 SUMMARY:")
    print(f"   Files Processed Successfully: {files_processed}")
    print(f"   Files Skipped (Empty/Image):  {files_skipped}")
    print(f"   Total Chunks Generated:       {len(all_chunks)}")
    print("-" * 50)
        
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
            
    # 4. Persist and Zip
    print("🗜️ Compressing database...")
    with zipfile.ZipFile(DB_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(DB_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, DB_FOLDER)
                zipf.write(file_path, arcname)
                
    print(f"✅ SUCCESS! {DB_ZIP} is ready.")

if __name__ == "__main__":
    build_database()