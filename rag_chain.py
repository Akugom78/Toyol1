# rag_chain.py
import sys
import os

# ==========================================
# CRITICAL: FIX PYTHON PATH FOR STREAMLIT
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# ==========================================

import streamlit as st
from openai import OpenAI
import vector_db

def get_api_config(key_name):
    try:
        return st.secrets[key_name]
    except (KeyError, FileNotFoundError):
        return os.getenv(key_name)

def get_qwen_client():
    api_key = get_api_config("QWEN_API_KEY")
    base_url = get_api_config("QWEN_BASE_URL")
    if not api_key or not base_url:
        raise ValueError("QWEN_API_KEY or QWEN_BASE_URL is missing from secrets!")
    return OpenAI(api_key=api_key, base_url=base_url)

def retrieve_context(query, top_k=4):
    collection = vector_db.get_chroma_collection()
    results = collection.query(query_texts=[query], n_results=top_k)
    
    context_chunks = []
    sources = []
    
    if results and results['documents'] and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            context_chunks.append(doc)
            if results['metadatas'] and results['metadatas'][0]:
                sources.append(results['metadatas'][0][i].get('source', 'Unknown Document'))
                
    return "\n\n---\n\n".join(context_chunks), sources

def stream_qwen_response(messages_history, context, sources):
    client = get_qwen_client()
    model_name = get_api_config("QWEN_MODEL_NAME") or "qwen3.7-plus"
    
    SYSTEM_PROMPT = """You are a Senior Air Traffic Control Professional with expertise in ICAO Standards and Recommended Practices (SARPs), Malaysian Civil Aviation Regulations (MCAR 2016), and Civil Aviation Authority of Malaysia (CAAM) procedures.

You operate in 4 modes depending on the user's request:
1. **Q&A Mode**: Answer procedural questions using [RETRIEVED CONTEXT]. Cite sources precisely.
2. **Drafting Mode**: Draft documents (SOPs, letters, memos, NOTAMs) using templates from context. If no template exists, propose a structure based on ICAO best practices and mark it with: [⚠️ BASED ON GENERAL BEST PRACTICES — REQUIRES LOCAL VERIFICATION].
3. **Research Mode**: Provide comprehensive regulatory research with cross-references between documents.
4. **Discrepancy Mode**: Identify conflicts, inconsistencies, or gaps between documents or between documents and ICAO standards.

RULES:
- Prioritize [RETRIEVED CONTEXT] above all else.
- Always cite sources like this: (Source: [Document Name])
- Never fabricate ATC procedures, phraseology, or minima.
- If information is not in the context and cannot be inferred safely, state: "This information is not available in the provided documents."
- Use professional ATC terminology and ICAO-standard phraseology."""

    # Create a copy of history to avoid mutating session state
    augmented_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add recent history (last 10 messages to prevent token overflow)
    augmented_messages.extend(messages_history[-10:])
    
    # Inject context into the very last user message
    if augmented_messages[-1]["role"] == "user":
        last_msg = augmented_messages[-1]
        if context.strip():
            last_msg["content"] = f"[RETRIEVED CONTEXT]:\n{context}\n\nQuestion: {last_msg['content']}"
        else:
            last_msg["content"] = f"Note: No relevant context was found in the database. Answer based on general ATC knowledge but explicitly state if official documents do not cover this.\n\nQuestion: {last_msg['content']}"

    stream = client.chat.completions.create(
        model=model_name,
        messages=augmented_messages,
        stream=True,
        temperature=0.2
    )
    
    for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                yield delta.content