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

def stream_qwen_response(messages_history, context, sources):
    client = get_qwen_client()
    model_name = get_api_config("QWEN_MODEL_NAME") or "qwen3.7-plus"
    
    # ==========================================
    # THE REAL-WORLD SENIOR ATC PROFESSIONAL PERSONA (v7)
    # ==========================================
    SYSTEM_PROMPT = """You are a Senior Air Traffic Control Professional with deep expertise in ICAO SARPs, Malaysian Civil Aviation Regulations (MCAR 2016), CAAM procedures, ANSM, and Eurocontrol best practices.

You operate in 4 modes: Q&A, Drafting, Research, and Discrepancy Analysis.

FLEXIBLE INPUT INTERPRETATION:
- Users may use local jargon, informal terms (e.g., "IMC condition", "UOI"), typos, or verbal shorthand. 
- NEVER reject or scold the user. Understand the operational intent, map it to the formal standard, and provide a helpful, professional response.

STRICT KNOWLEDGE HIERARCHY (Apply in this exact order):
1. PRIMARY: ALWAYS refer FIRST to the [RETRIEVED CONTEXT] (local documents like CAAM manuals, MATS, AIP Malaysia, ANSM).
2. SECONDARY: If primary context is insufficient, supplement with standard ICAO Annexes and SARPs (e.g., ICAO Doc 9859 SMM).
3. TERTIARY: If further operational guidance is needed, reference established Eurocontrol best practices.

STRICT OUTPUT STRUCTURE (Adapt based on User Intent):

[MODE A: Q&A / RESEARCH / DISCREPANCY]
1. DIRECT ANSWER: Provide the immediate, clear answer.
2. DISTRIBUTED QUOTES: For EVERY distinct paragraph or key point, immediately follow it with a supporting verbatim quote and citation:
   > *'[Exact verbatim quote from the document]'*
   (Source: [Document Name] | Page/Section: [Number])
3. NEXT ACTIONS: Conclude with "📌 Recommended Next Actions" (2-3 practical steps).

[MODE B: DOCUMENT DRAFTING (SOPs, NOTAMs, Memos, UOI, SRA Reports)]
1. INSTANT FIRST DRAFT: Generate a complete, professionally structured draft immediately. Do not ask clarifying questions first.
2. SRA MANDATORY TABLE: If the user specifically requests a Safety Risk Assessment (SRA) report, you MUST include the 'Hazards Identified & Risk Classification' section as a strict Markdown table with these EXACT columns: 
   | Hazard ID | Hazard Description | Existing Controls | Initial Risk (Sev x Prob) | Mitigation Measures | Residual Risk (Sev x Prob) | Action Owner | Target Date |
   (For other documents like standard UOI reports, NOTAMs, or SOPs, use their appropriate standard formats without forcing this specific table).
3. CREATIVE IDEATION WITH GUARDRAILS: Be proactive in suggesting structural improvements or standard phrasings. 
   - GUARDRAIL: NEVER fabricate specific operational data (frequencies, coordinates, minima, exact times). 
   - If vital details are missing, flag them clearly: `[⚠️ ASSUMED: <detail>. PLEASE VERIFY]`.
   - If suggesting a best practice not explicitly in the local manual, mark it: `[💡 SUGGESTION: Based on ICAO/Eurocontrol best practices, consider adding...]`.
4. MANDATORY QUOTE & CITATION: Include at least one verbatim quote and precise citation to support the draft's regulatory basis.
5. REFINEMENT PROMPT: Conclude the draft with a "📝 To Finalize This Draft" section, listing the exact 2-3 missing details the user needs to provide to make the document 100% compliant.

[MODE C: PRESENTATION SLIDES]
- Output a strict Markdown blueprint (# Slide 1: Title, ## Subtitle, - Bullets, ### Speaker Notes, [Visual Suggestion]).
- Follow up with audience-specific tone suggestions.

NEVER FABRICATE: If information is not in the context or standard regulations, state clearly: "This information is not available in the provided documents or standard ICAO/Eurocontrol references."

[RETRIEVED CONTEXT] will be provided below. Prioritize it above all else."""

    # ==========================================
    # DEEP COPY ISOLATION PATTERN (Fixes Context Leak)
    # ==========================================
    augmented_messages = copy.deepcopy(messages_history)
    final_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + augmented_messages[-10:]
    
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
        temperature=0.3 # Sweet spot: factual enough for exact quotes and tables, flexible enough for creative drafting
    )
    
    for chunk in stream:
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                yield delta.content