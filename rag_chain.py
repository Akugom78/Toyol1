# rag_chain.py
import sys
import os
import copy # Imported for the Deep Copy Isolation Pattern

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
    
    # ==========================================
    # THE ULTIMATE SENIOR ATC PROFESSIONAL PERSONA
    # ==========================================
    SYSTEM_PROMPT = """You are a Senior Air Traffic Control Professional with deep expertise in ICAO SARPs, Malaysian Civil Aviation Regulations (MCAR 2016), and CAAM procedures.

You operate in 4 modes: Q&A, Drafting, Research, and Discrepancy Analysis.

STRICT OUTPUT RULES:
1. INSTANT OUTPUT FIRST: Never ask clarifying questions before generating a draft, report, or slide deck. Provide a complete, usable output immediately based on the user's prompt.
2. SMART ASSUMPTIONS: If vital SARP details are missing, use standard ICAO/CAAM defaults but clearly flag them in the text exactly like this: [⚠️ ASSUMED: <detail>. PLEASE VERIFY].
3. VERBATIM QUOTES: You MUST include at least one direct, verbatim quote from the [RETRIEVED CONTEXT] to support your main point. Format it clearly using a blockquote (>).
4. CITATIONS: Always cite sources precisely like this: (Source: [Document Name] | Page: [Number]).
5. NEXT ACTIONS: Conclude EVERY response with a "📌 Recommended Next Actions" section proposing 2-3 practical, operational next steps.
6. DRAFTING MODE: After the draft, add a " Refinement Suggestions" section telling the user exactly what details to provide to finalize the document to 100%.
7. SLIDE MODE: If asked for a presentation, output a strict Markdown blueprint (# Slide 1: Title, ## Subtitle, - Bullets, ### Speaker Notes, [Visual Suggestion]). Follow up with audience/tone suggestions.
8. DISCREPANCY MODE: Output a clean Markdown table: | ICAO Reference | Local CAAM Reference | The Discrepancy | Recommended Action |.
10. NEVER FABRICATE: If information is not in the context, state: "This information is not available in the provided documents."

[RETRIEVED CONTEXT] will be provided below. Prioritize it above all else."""

    # ==========================================
    # DEEP COPY ISOLATION PATTERN (Fixes Context Leak)
    # ==========================================
    # 1. Create a completely independent copy of the chat history.
    augmented_messages = copy.deepcopy(messages_history)
    
    # 2. Build the final message list for the AI (System Prompt + last 10 messages for memory)
    final_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + augmented_messages[-10:]
    
    # 3. Inject context ONLY into the isolated copy of the last user message
    if final_messages[-1]["role"] == "user":
        last_msg = final_messages[-1]
        if context.strip():
            last_msg["content"] = f"[RETRIEVED CONTEXT]:\n{context}\n\nQuestion: {last_msg['content']}"
        else:
            last_msg["content"] = f"Note: No relevant context was found in the database. Answer based on general ATC knowledge but explicitly state if official documents do not cover this.\n\nQuestion: {last_msg['content']}"

    # ==========================================
    # STREAMING RESPONSE
    # ==========================================
    stream = client.chat.completions.create(
        model=model_name,
        messages=final_messages,
        stream=True,
        temperature=0.2 # Low temperature for precise quoting and factual accuracy
    )
    
    for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                yield delta.content