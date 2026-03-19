"""
test_foundation.py
===================
Manual test script to verify PDF loading, chunking, and vector storage.

Usage:
    python test_foundation.py "path/to/your/book.pdf"
"""

import sys
import os
from modules.pdf_loader import load_and_split_pdf, get_pdf_info
from modules.embeddings import store_embeddings, query_embeddings, collection_exists

def run_test(pdf_path: str):
    print(f"--- Starting Foundation Test ---")
    
    # 1. Check if file exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File '{pdf_path}' not found.")
        return

    # 2. Test PDF Loading & Chunking
    print(f"\n[1/3] Loading and splitting PDF...")
    chunks = load_and_split_pdf(pdf_path)
    info = get_pdf_info(chunks, pdf_path)
    
    if not chunks:
        print("❌ Failed to create chunks.")
        return
        
    print(f"✅ Success! Found {info['total_pages']} pages and created {info['total_chunks']} chunks.")

    # 3. Test Embedding Storage
    collection_name = "test_collection"
    print(f"\n[2/3] Storing embeddings in ChromaDB (collection: '{collection_name}')...")
    
    success = store_embeddings(chunks, collection_name)
    if success:
        print(f"✅ Embeddings stored successfully.")
    else:
        print("❌ Failed to store embeddings.")
        return

    # 4. Test Querying
    print(f"\n[3/3] Querying: 'What is this book about?'")
    results = query_embeddings("What is this book about?", collection_name, top_k=2)
    
    if results:
        print(f"✅ Query returned {len(results)} relevant chunks.")
        print("\n--- Sample Content from first chunk ---")
        print(results[0].page_content[:500] + "...")
    else:
        print("❌ Query returned no results.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_foundation.py <path_to_pdf>")
    else:
        run_test(sys.argv[1])
