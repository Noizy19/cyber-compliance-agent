"""
RAG Engine & Multi-Agent Architecture for Cybersecurity Compliance

Agent 1: Retriever / Router (Groq: llama-3.1-8b-instant)
- Analyzes user compliance query intent
- Generates optimized search strategy
- Retrieves top relevant policy passages from local Chroma vector DB

Agent 2: Advisor / Critic (OpenRouter: meta-llama/llama-3.3-70b-instruct)
- Step 2A (Draft Phase): Formulates initial structured compliance advice
- Step 2B (Critique Phase): Self-critiques the draft against RAG context & refines final response
"""

import os
import glob
from typing import Dict, List, Any
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document

# Safe embedding import
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

load_dotenv()

CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), ".chroma")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def get_embeddings():
    """Initializes the local sentence-transformer embedding model."""
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def load_policy_documents() -> List[Document]:
    """Loads all policy text files from data/ directory."""
    documents = []
    txt_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
    for filepath in txt_files:
        filename = os.path.basename(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract Policy ID and Title if available in header
            policy_id = filename
            title = filename
            lines = content.splitlines()
            for l in lines[:3]:
                if l.startswith("POLICY ID:"):
                    policy_id = l.replace("POLICY ID:", "").strip()
                elif l.startswith("TITLE:"):
                    title = l.replace("TITLE:", "").strip()

            doc = Document(
                page_content=content,
                metadata={
                    "source": filename,
                    "policy_id": policy_id,
                    "title": title,
                    "filepath": filepath
                }
            )
            documents.append(doc)
    return documents

def build_vectorstore(force_rebuild: bool = False):
    """
    Builds or loads the local Chroma vector store over policy documents.
    """
    embeddings = get_embeddings()
    if force_rebuild or not os.path.exists(CHROMA_DB_DIR) or len(os.listdir(CHROMA_DB_DIR)) == 0:
        docs = load_policy_documents()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=650,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = text_splitter.split_documents(docs)
        
        # Initialize Chroma and persist
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DB_DIR
        )
        # Persist if supported by Chroma version
        if hasattr(vectorstore, "persist"):
            try:
                vectorstore.persist()
            except Exception:
                pass
        return vectorstore, len(docs), len(chunks)
    else:
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embeddings
        )
        return vectorstore, len(load_policy_documents()), vectorstore._collection.count()

def agent_1_retriever_router(
    query: str,
    vectorstore: Chroma,
    groq_api_key: str = None
) -> Dict[str, Any]:
    """
    Agent 1 (Retriever / Router): Uses Groq llama-3.1-8b-instant to process user query,
    determine retrieval scope, and retrieve relevant contexts from ChromaDB.
    """
    api_key = groq_api_key or os.getenv("GROQ_API_KEY")
    
    # 1. Direct Vector Search
    retrieved_docs = vectorstore.similarity_search_with_score(query, k=4)
    formatted_docs = []
    doc_context_text = ""
    
    for idx, (doc, score) in enumerate(retrieved_docs, start=1):
        formatted_docs.append({
            "rank": idx,
            "policy_id": doc.metadata.get("policy_id", "N/A"),
            "title": doc.metadata.get("title", "N/A"),
            "source": doc.metadata.get("source", "N/A"),
            "similarity_score": round(float(score), 4),
            "content": doc.page_content
        })
        doc_context_text += f"\n--- DOCUMENT {idx} [{doc.metadata.get('source')}] ---\n{doc.page_content}\n"

    # 2. Query Routing & Intent Analysis via Groq LLM if API key provided
    query_analysis = ""
    if api_key and api_key != "your_groq_api_key_here":
        try:
            llm_groq = ChatGroq(
                model_name="llama-3.1-8b-instant",
                groq_api_key=api_key,
                temperature=0.1
            )
            router_prompt = f"""You are Agent 1 (Security Router & Retriever) in an enterprise cybersecurity compliance system.
Analyze the following user compliance query:
User Query: "{query}"

Retrieved Policy Documents:
{doc_context_text}

Provide a concise breakdown in markdown covering:
1. Core Compliance Intent & Security Domains (e.g., IAM, Incident Response, Encryption).
2. Key Governance Standards Targeted (e.g., ISO 27001, SOC 2, NIST, GDPR).
3. Retrieval Relevance Assessment: Briefly explain why the retrieved policy documents match or address the query.
"""
            res = llm_groq.invoke(router_prompt)
            query_analysis = res.content
        except Exception as e:
            query_analysis = f"*(Groq Router Notice: {str(e)}. Proceeding with raw retrieved vectors.)*"
    else:
        query_analysis = (
            f"**Query Intent Analysis (Local Vector Search)**:\n"
            f"- Search Term: '{query}'\n"
            f"- Matched {len(formatted_docs)} top policy segments in local ChromaDB.\n"
            f"- Policies identified: {', '.join(set(d['source'] for d in formatted_docs))}"
        )

    return {
        "query": query,
        "query_analysis": query_analysis,
        "docs": formatted_docs,
        "doc_context_text": doc_context_text
    }

def agent_2_advisor_critic(
    query: str,
    retrieval_data: Dict[str, Any],
    openrouter_api_key: str = None
) -> Dict[str, Any]:
    """
    Agent 2 (Advisor / Critic): Uses OpenRouter meta-llama/llama-3.3-70b-instruct
    to analyze context, draft compliance advice, and perform a self-critique/reflection pass.
    """
    api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
    doc_context = retrieval_data["doc_context_text"]
    
    if not api_key or api_key == "your_openrouter_api_key_here":
        # Fallback response if no API key is provided
        draft_advice = "*(OpenRouter API Key not set. Enter a valid key in the sidebar to generate LLM compliance advice.)*"
        critique = "*(Critique skipped: OpenRouter API Key required.)*"
        final_advice = f"""### 🛡️ Compliance Policy Excerpts Found

Below are the exact relevant policy sections retrieved for your query: **"{query}"**

{doc_context}

*Please provide an OpenRouter API key in the sidebar for full AI analysis, gap analysis, and self-critique generation.*
"""
        return {
            "draft_advice": draft_advice,
            "critique": critique,
            "final_advice": final_advice
        }

    try:
        # Initialize OpenRouter LLM using ChatOpenAI client wrapper
        llm_openrouter = ChatOpenAI(
            model_name="meta-llama/llama-3.3-70b-instruct",
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.2,
            default_headers={
                "HTTP-Referer": "https://github.com/cyber-compliance-agent",
                "X-Title": "Cyber Compliance Agentic RAG"
            }
        )

        # STAGE 2A: DRAFT COMPLIANCE ADVICE
        draft_prompt = f"""You are Agent 2 (Senior Cybersecurity Compliance Advisor).
Your task is to draft detailed, highly structured cybersecurity compliance advice based strictly on the user query and the retrieved corporate policy passages.

User Query: "{query}"

Retrieved Corporate Policies:
{doc_context}

Drafting Requirements:
- Structure your response clearly with:
  1. Executive Summary & Policy Scope
  2. Specific Mandatory Requirements & SLAs (cite exact Policy IDs, hours/days, standards like ISO/NIST/SOC2)
  3. Actionable Implementation & Governance Checklist
  4. Non-Compliance Risks & Escalation Protocols
- Base all claims strictly on the provided policy context.
"""
        draft_res = llm_openrouter.invoke(draft_prompt)
        draft_advice = draft_res.content

        # STAGE 2B: SELF-CRITIQUE & REFINEMENT PASS (Reflection Pattern)
        critique_prompt = f"""You are Agent 2 acting in CRITIC / AUDITOR mode.
Review your own initial draft response against the original user query and retrieved corporate policies to perform a rigorous self-audit.

User Query: "{query}"

Retrieved Corporate Policies:
{doc_context}

Initial Draft Response:
{draft_advice}

Perform a 4-Point Compliance Audit:
1. Context Fidelity Check: Did the draft hallucinate any SLAs, numbers, or rules not present in the policies?
2. Omission Check: Did the draft leave out key mandatory requirements, exception rules, or timelines mentioned in the retrieved policies?
3. Regulatory Alignment Check: Are ISO 27001, NIST, SOC 2, GDPR, or PCI-DSS standards referenced correctly?
4. Clarity & Formatting Assessment: Is the advice clear, authoritative, and actionable for security leadership?

Provide your Audit Feedback followed by your REFINED FINAL COMPLIANCE ADVICE.

Format your output exactly as:
---CRITIQUE START---
[Your 4-Point Audit Feedback here]
---CRITIQUE END---

---FINAL ADVICE START---
[Your refined, polished, and comprehensive final compliance advice here]
---FINAL ADVICE END---
"""
        critique_res = llm_openrouter.invoke(critique_prompt)
        raw_critic_output = critique_res.content

        # Parse Critique vs Final Advice
        critique = "Self-critique pass completed successfully."
        final_advice = draft_advice

        if "---CRITIQUE START---" in raw_critic_output and "---CRITIQUE END---" in raw_critic_output:
            critique = raw_critic_output.split("---CRITIQUE START---")[1].split("---CRITIQUE END---")[0].strip()
        
        if "---FINAL ADVICE START---" in raw_critic_output and "---FINAL ADVICE END---" in raw_critic_output:
            final_advice = raw_critic_output.split("---FINAL ADVICE START---")[1].split("---FINAL ADVICE END---")[0].strip()
        elif "---FINAL ADVICE START---" in raw_critic_output:
            final_advice = raw_critic_output.split("---FINAL ADVICE START---")[1].strip()

        return {
            "draft_advice": draft_advice,
            "critique": critique,
            "final_advice": final_advice
        }

    except Exception as e:
        error_msg = f"Error communicating with OpenRouter API: {str(e)}"
        return {
            "draft_advice": f"*(Draft Generation Error: {error_msg})*",
            "critique": f"*(Critique Error: {error_msg})*",
            "final_advice": f"⚠️ **API Error**: {error_msg}\n\n**Retrieved Context Excerpt**:\n{doc_context}"
        }

def run_compliance_pipeline(
    query: str,
    groq_api_key: str = None,
    openrouter_api_key: str = None,
    force_rebuild_db: bool = False
) -> Dict[str, Any]:
    """
    Executes the full two-agent RAG pipeline:
    VectorStore -> Agent 1 (Router/Retriever) -> Agent 2 (Advisor/Critic Draft & Reflection)
    """
    vectorstore, num_docs, num_chunks = build_vectorstore(force_rebuild=force_rebuild_db)
    retrieval_data = agent_1_retriever_router(query, vectorstore, groq_api_key=groq_api_key)
    advisor_data = agent_2_advisor_critic(query, retrieval_data, openrouter_api_key=openrouter_api_key)
    
    return {
        "query": query,
        "num_docs": num_docs,
        "num_chunks": num_chunks,
        "query_analysis": retrieval_data["query_analysis"],
        "retrieved_docs": retrieval_data["docs"],
        "draft_advice": advisor_data["draft_advice"],
        "critique": advisor_data["critique"],
        "final_advice": advisor_data["final_advice"]
    }
