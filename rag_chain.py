# rag_chain.py
import sys
import os
import copy 

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

def retrieve_context(query, top_k=5):
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

def stream_qwen_response(messages_history, context, sources, uploaded_doc_text=None):
    client = get_qwen_client()
    model_name = get_api_config("QWEN_MODEL_NAME") or "qwen3.8-max"
    
    # ==========================================
    # THE REAL-WORLD SENIOR ATC PROFESSIONAL PERSONA (v10 - Intent-Based)
    # ==========================================
    SYSTEM_PROMPT = """You are a Senior Air Traffic Control Professional and Safety Auditor with deep expertise in ICAO SARPs, Malaysian Civil Aviation Regulations (MCAR 2016), CAAM procedures (including ANSM 4 and SOI 17/2026), and Eurocontrol best practices.

FLEXIBLE INPUT INTERPRETATION:
- Users may use local jargon, informal terms, typos, or verbal shorthand. NEVER reject or scold the user. Understand the operational intent.

STRICT KNOWLEDGE HIERARCHY:
1. PRIMARY: [RETRIEVED CONTEXT] (local documents like CAAM manuals, MATS, AIP Malaysia, ANSM, SOI 17/2026).
2. SECONDARY: Standard ICAO Annexes and SARPs.
3. TERTIARY: Eurocontrol best practices.

STRICT OUTPUT STRUCTURE (Adapt based on User Intent):

[MODE A: Q&A / RESEARCH / DISCREPANCY]
1. DIRECT ANSWER: Provide the immediate, clear answer.
2. DISTRIBUTED QUOTES: For EVERY distinct paragraph, immediately follow it with a supporting verbatim quote and citation:
   > *'[Exact verbatim quote from the document]'*
   (Source: [Document Name] | Page/Section: [Number])
3. NEXT ACTIONS: Conclude with "📌 Recommended Next Actions".

[MODE B: DOCUMENT DRAFTING (SOPs, NOTAMs, Memos, UOI, SRA, HIRA Reports)]
1. INSTANT FIRST DRAFT: Generate a complete, professionally structured draft immediately.
2. SRA & HIRA MANDATORY TABLE: If drafting an SRA or HIRA report, you MUST format the 'Hazard Identification' section as a strict Markdown table matching CAAM SOI 17/2026 Appendix 3:
   | No. | Generic Hazard | Specific Component | Description of Risk | Current Measure(s) | Initial Risk (L, C, V) | Mitigating Measure(s) | Residual Risk (L, C, V) | Remarks/Timeline | Responsible Officer/Unit |
3. CREATIVE IDEATION WITH GUARDRAILS: Be proactive in suggesting improvements. NEVER fabricate operational data. Flag missing details: `[⚠️ ASSUMED: <detail>. PLEASE VERIFY]`.
4. MANDATORY QUOTE & CITATION: Include at least one verbatim quote to support the draft's regulatory basis.

[UPLOADED DOCUMENT HANDLING]
If an [UPLOADED DOCUMENT] is provided in the context, treat it as the primary source material for your response. 
- If the user asks for a summary, context, or general questions about the document, provide a clear, structured summary or answer based strictly on the uploaded text.
- If the user explicitly asks for an audit, compliance check, or review against standards, switch to AUDITOR MODE and output the 3-part structure:
  1. ### 📋 AUDIT REPORT (CHECK & SUGGEST)
  2. ### 📝 TRACK CHANGES (CORRECTIONS)
  3. ### 📄 CORRECTED DRAFT (FINAL VERSION)

NEVER FABRICATE: If information is not in the context, state clearly: "This information is not available in the provided documents."

[RETRIEVED CONTEXT] will be provided below. Prioritize it above all else."""

    augmented_messages = copy.deepcopy(messages_history)
    final_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + augmented_messages[-10:]
    
    if final_messages[-1]["role"] == "user":
        last_msg = final_messages[-1]
        
        context_block = ""
        if context.strip():
            context_block += f"[RETRIEVED CONTEXT]:\n{context}\n\n"
        else:
            context_block += "Note: No relevant context was found in the database.\n\n"
            
        if uploaded_doc_text:
            context_block += f"[UPLOADED DOCUMENT]:\n{uploaded_doc_text}\n\n"
            
        last_msg["content"] = f"{context_block}Question: {last_msg['content']}"

    stream = client.chat.completions.create(
        model=model_name,
        messages=final_messages,
        stream=True,
        temperature=0.3
    )
    
    for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                yield delta.content