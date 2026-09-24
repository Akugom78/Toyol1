# rag_chain.py
import sys
import os

# ==========================================
# CRITICAL: FIX PYTHON PATH FOR STREAMLIT
# ==========================================
# This ensures Python can always find vector_db.py, even when Streamlit runs the app
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ==========================================

import streamlit as st
from openai import OpenAI
import vector_db

def get_api_config(key_name):
    """Fetches secrets from Streamlit Cloud or local .streamlit/secrets.toml"""
    try:
        return st.secrets[key_name]
    except (KeyError, FileNotFoundError):
        # Fallback for local testing if secrets.toml isn't set up yet
        return os.getenv(key_name)

def get_qwen_client():
    """Initializes the OpenAI client pointing to the Qwen API."""
    api_key = get_api_config("QWEN_API_KEY")
    base_url = get_api_config("QWEN_BASE_URL")
    
    if not api_key or not base_url:
        raise ValueError("QWEN_API_KEY or QWEN_BASE_URL is missing from secrets!")
        
    return OpenAI(api_key=api_key, base_url=base_url)

def retrieve_context(query, top_k=3):
    """Searches the Vector DB for the most relevant document chunks."""
    collection = vector_db.get_chroma_collection()
    
    # Query the database
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    # Format the results into a single context string
    context_chunks = []
    sources = []
    
    if results and results['documents'] and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            context_chunks.append(doc)
            # Get the source filename from metadata if available
            if results['metadatas'] and results['metadatas'][0]:
                sources.append(results['metadatas'][0][i].get('source', 'Unknown Document'))
                
    return "\n\n---\n\n".join(context_chunks), sources

def stream_qwen_response(query, context, sources):
    """
    Sends the query and context to Qwen and streams the response.
    Yields chunks of text for the Streamlit UI to display.
    """
    client = get_qwen_client()
    model_name = get_api_config("QWEN_MODEL_NAME") or "qwen-plus"
    
    # ATC is safety-critical. We use a strict system prompt to prevent hallucinations.
    system_prompt = """You are an expert Air Traffic Control (ATC) assistant. 
    Your job is to answer questions strictly based on the provided ATC document context.
    Rules:
    1. ONLY use the provided context to answer.
    2. If the answer is not in the context, you MUST say: "I cannot find the answer in the provided ATC documents."
    3. Do not make up information or use outside knowledge.
    4. Be concise, professional, and clear."""
    
    user_prompt = f"""
    Context from ATC Documents:
    {context}
    
    User Question: {query}
    """
    
    # Call the Qwen API with streaming enabled
    stream = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        stream=True,
        temperature=0.2 # Low temperature for factual, deterministic answers
    )
    
        # Yield the response chunk by chunk (safely handling empty chunks)
    for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                yield delta.content