from typing import TypedDict, Annotated

from dotenv import load_dotenv

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_core.tools import tool

from langchain_groq import ChatGroq

from langgraph.checkpoint.sqlite import SqliteSaver

import sqlite3

# Import retriever from your RAG file
from rag import retriever, vectorstore
# Import new tools
from tools import calculator, wikipedia_search, get_current_time, get_stock_price

load_dotenv()

# Active streams registry for mapping thread_id -> CallbackHandler
active_streams = {}

# ---------------- LLM ---------------- #

llm_primary = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    streaming=True
)
llm_fallback = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0,
    streaming=True
)
llm = llm_primary.with_fallbacks([llm_fallback])

def grade_document(question: str, document_content: str) -> str:
    prompt = f"""System: You are a grader assessing relevance of a retrieved document to a user question.
If the document contains keywords or semantic meaning related to the user question, reply with 'yes', otherwise reply with 'no'.
Do not write any other explanation. Just write 'yes' or 'no'.

Question: {question}
Document: {document_content}

Relevance:"""
    try:
        response = llm.invoke(prompt)
        score = response.content.strip().lower()
        if "yes" in score:
            return "yes"
        return "no"
    except Exception:
        return "yes"

def is_general_knowledge_query(question: str) -> bool:
    prompt = f"""System: You are an assistant classifying whether a user question is a general knowledge question (which can be answered by Wikipedia/general web search, e.g., science, history, geography, famous people, general definitions) OR a query specific to local uploaded files, resumes, certificates, or personal context (which CANNOT be answered by Wikipedia).

Reply with 'general' if it is a general knowledge question.
Reply with 'local' if it is about a specific uploaded file, certificate, resume, personal data, or local context.

Do not write any other explanation. Just write 'general' or 'local'.

Question: {question}

Classification:"""
    try:
        response = llm.invoke(prompt)
        classification = response.content.strip().lower()
        if "general" in classification:
            return True
        return False
    except Exception:
        return False

# ---------------- Advanced RAG / CRAG Helpers ---------------- #

def rewrite_query(user_query: str, chat_history: list[BaseMessage]) -> str:
    # Extract recent messages to provide context
    history_text = ""
    for msg in chat_history[-5:]: # last 5 messages
        if isinstance(msg, HumanMessage):
            history_text += f"User: {msg.content}\n"
        elif isinstance(msg, AIMessage) and msg.content:
            history_text += f"Assistant: {msg.content}\n"
    
    if not history_text:
        return user_query

    prompt = f"""System: You are an expert query rewriter. Your task is to take a user's latest query and the conversation history, and rewrite it into a single search query optimized for document retrieval (Vector DB and BM25 search).
Do NOT answer the question. Just output the rewritten search query.
If the query is self-contained and needs no context, output it as is.
Do not add any preamble, explanation, or quotes.

Conversation History:
{history_text}

User Query: {user_query}

Search Query:"""
    try:
        response = llm.invoke(prompt)
        rewritten = response.content.strip()
        if (rewritten.startswith('"') and rewritten.endswith('"')) or (rewritten.startswith("'") and rewritten.endswith("'")):
            rewritten = rewritten[1:-1].strip()
        return rewritten if rewritten else user_query
    except Exception:
        return user_query

def check_groundedness_and_relevance(query: str, context: str, response_text: str) -> str:
    lower_res = response_text.lower()
    if any(phrase in lower_res for phrase in ["no relevant information", "not found", "cannot find", "do not have", "unavailable"]):
        return "yes"

    prompt = f"""System: You are an expert auditor evaluating if an assistant's response is relevant to the user's query, strictly grounded in the provided context, and written in a natural, concise, human-like way.
- Grounded: Every fact, claim, name, or number in the response is directly supported by the context.
- Relevant: The response directly addresses and answers the user's query.
- Natural: The response is written in a natural, concise, human-like summary. It must NOT be a raw copy-paste, line-by-line dump, or listing of the retrieved context.

If the response contains any facts not supported by the context (hallucinations), fails to address the query, OR is a raw copy-paste/dump of the context, reply with 'no'.
If the response is fully supported by the context, answers the query, AND is a clean, natural summary (not a copy-paste dump), reply with 'yes'.

Do not write any other explanation. Just reply with 'yes' or 'no'.

Context:
{context}

Query: {query}
Response: {response_text}

Grounded, Relevant, and Natural (yes/no):"""
    try:
        res = llm.invoke(prompt)
        score = res.content.strip().lower()
        if "yes" in score:
            return "yes"
        return "no"
    except Exception:
        return "yes"

def regenerate_grounded_response(query: str, context: str, thread_id: str = "default_thread") -> AIMessage:
    prompt = f"""You are a helpful assistant. Answer the user's query concisely and directly based ONLY on the provided context.
- Be concise and direct. Do NOT copy-paste the entire context, and do NOT repeat information.
- If the query is about what a document/certificate/resume is about, summarize its core purpose, recipient, and main details in 1-3 sentences (e.g. 'This is an operating systems certificate issued to Om Bansal by Coursera on March 31, 2026').
- Do NOT make up details. Every fact must be directly traceable to the context.

Context:
{context}

User Query: {query}
"""
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=query)
    ]
    try:
        handler = active_streams.get(thread_id)
        llm_config = {}
        if handler:
            llm_config["callbacks"] = [handler]
        response = llm.invoke(messages, config=llm_config)
        return response
    except Exception as e:
        return AIMessage(content=f"I encountered an error generating the response: {str(e)}")

_cached_bm25 = None
_cached_doc_count = 0

def reset_bm25_cache():
    global _cached_bm25, _cached_doc_count
    _cached_bm25 = None
    _cached_doc_count = 0


def get_uploaded_files():
    import os
    if os.path.exists("uploads"):
        return [f for f in os.listdir("uploads") if f.endswith(".pdf")]
    return []

def route_query_to_files(query: str, uploaded_files: list[str]) -> list[str]:
    if not uploaded_files:
        return []
    if len(uploaded_files) == 1:
        return uploaded_files
    
    files_list_str = "\n".join([f"- {f}" for f in uploaded_files])
    prompt = f"""System: You are an expert routing assistant. Given a user search query and a list of uploaded PDF files, identify which files are likely to contain the answer to the query.
- Be highly selective: if the query mentions a specific name, subject, or keyword (e.g. 'kanak'), do NOT select files that do not match or contain that name/keyword (e.g. 'OM_BANSAL'), even if they share common document suffixes or extensions (like 'cv' or 'pdf').
- If the query references 'my resume', 'my cv', or 'my certificate', and the query does not contain another name, select the primary user resume (e.g., matching 'OM_BANSAL').
- If the query is general, chit-chat, or it is unclear which file is relevant, select ALL files.

Output ONLY the exact filenames, one per line. Do not include any other text, explanation, list symbols, or markdown.

Uploaded Files:
{files_list_str}

User Query: {query}

Relevant Files:"""
    try:
        response = llm.invoke(prompt)
        selected = [line.strip() for line in response.content.split("\n") if line.strip()]
        cleaned = []
        for s in selected:
            s_clean = s
            if s_clean.startswith(("- ", "* ", "• ")):
                s_clean = s_clean[2:]
            elif s_clean.strip() and s_clean.strip()[0].isdigit() and s_clean.strip()[1:].startswith((". ", ") ")):
                parts = s_clean.split(None, 1)
                if len(parts) > 1:
                    s_clean = parts[1]
            s_clean = s_clean.strip()
            if s_clean in uploaded_files:
                cleaned.append(s_clean)
        return cleaned if cleaned else uploaded_files
    except Exception:
        return uploaded_files

def get_bm25_retriever(filter_sources: list[str] = None):
    global _cached_bm25, _cached_doc_count
    try:
        if filter_sources:
            if len(filter_sources) == 1:
                where_clause = {"source": filter_sources[0]}
            else:
                where_clause = {"source": {"$in": filter_sources}}
                
            db_data = vectorstore.get(where=where_clause, include=["documents", "metadatas"])
            all_texts = db_data.get("documents", [])
            all_metadatas = db_data.get("metadatas", [])
            
            if all_texts:
                langchain_docs = []
                for text, meta in zip(all_texts, all_metadatas):
                    if meta is None:
                        meta = {}
                    langchain_docs.append(Document(page_content=text, metadata=meta))
                bm25 = BM25Retriever.from_documents(langchain_docs)
                bm25.k = min(4, len(langchain_docs))
                return bm25
            return None

        count = vectorstore._collection.count()
        if count == 0:
            return None
        # Return cache if valid
        if _cached_bm25 is not None and count == _cached_doc_count:
            return _cached_bm25
            
        print(f"Rebuilding global BM25 index for {count} documents...")
        all_texts = []
        all_metadatas = []
        batch_size = 1000
        for offset in range(0, count, batch_size):
            batch = vectorstore._collection.get(
                limit=batch_size, 
                offset=offset, 
                include=["documents", "metadatas"]
            )
            all_texts.extend(batch.get("documents", []))
            all_metadatas.extend(batch.get("metadatas", []))
            
        if all_texts:
            langchain_docs = []
            for text, meta in zip(all_texts, all_metadatas):
                if meta is None:
                    meta = {}
                langchain_docs.append(Document(page_content=text, metadata=meta))
            
            _cached_bm25 = BM25Retriever.from_documents(langchain_docs)
            _cached_doc_count = count
            return _cached_bm25
    except Exception as e:
        print(f"Error building/retrieving BM25 index: {e}")
    return None

@tool
def rag_tool(query: str):
    """
        Retrieve relevant information from the PDF document.
    Use this tool when the user asks factual or conceptual
    questions that might be answered from the stored documents.

    """
    # 1. Determine metadata filter dynamically using filenames
    filter_dict = None
    filter_sources = None
    try:
        uploaded_files = get_uploaded_files()
        if uploaded_files:
            relevant_files = route_query_to_files(query, uploaded_files)
            if relevant_files:
                filter_sources = [f"uploads/{f}" for f in relevant_files]
                if len(filter_sources) == 1:
                    filter_dict = {"source": filter_sources[0]}
                else:
                    filter_dict = {"source": {"$in": filter_sources}}
                print(f"Routing query '{query}' to files: {relevant_files}")
    except Exception as e:
        print(f"Error routing query to files: {e}")

    # 2. Hybrid Retrieval: Dense (Chroma) + Sparse (BM25)
    dense_docs = []
    try:
        if filter_dict:
            dense_docs = vectorstore.similarity_search(query, k=3, filter=filter_dict)
        else:
            dense_docs = retriever.invoke(query)
    except Exception as e:
        print(f"Dense retrieval error: {e}")
        dense_docs = retriever.invoke(query)
    
    sparse_docs = []
    try:
        bm25 = get_bm25_retriever(filter_sources)
        if bm25 is not None:
            bm25.k = min(2, len(bm25.doc_list) if hasattr(bm25, "doc_list") else 2)
            sparse_docs = bm25.invoke(query)
    except Exception as e:
        print(f"BM25 Retrieval error: {e}")

    # Combine & Deduplicate
    combined_docs = []
    seen_contents = set()
    for doc in sparse_docs + dense_docs:
        content_key = doc.page_content.strip()
        if content_key not in seen_contents:
            seen_contents.add(content_key)
            combined_docs.append(doc)

    is_general = is_general_knowledge_query(query)
    
    # 3. Document Grading (CRAG)
    relevant_docs = []
    if filter_dict:
        # If filtered to specific target files, keep all retrieved chunks
        relevant_docs = combined_docs
    else:
        for doc in combined_docs:
            score = grade_document(query, doc.page_content)
            if score == "yes" or len(combined_docs) <= 1:
                relevant_docs.append(doc)

    context_list = [doc.page_content for doc in relevant_docs]
    
    # 4. Fallback Search / Error mitigation if no relevant docs found
    if not relevant_docs:
        if is_general:
            try:
                search_result = wikipedia_search.invoke(query)
                context_list.append(f"[Corrective Search Fallback Context] {search_result}")
            except Exception:
                pass
        else:
            context_list.append("[No relevant information found in the uploaded documents. Do not attempt to guess or use web search for local document questions.]")

    context = "\n\n".join(context_list)
    return context


tools = [rag_tool, calculator, wikipedia_search, get_current_time, get_stock_price]

llm_with_tools = llm.bind_tools(tools)

tool_node = ToolNode(tools)

# ---------------- State ---------------- #

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------- Chat Node ---------------- #

def prune_messages(messages: list, max_count: int = 8) -> list:
    # 1. Clean up past ToolMessages to remove massive context blocks
    cleaned_messages = []
    for i, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            # If it is not the very last message in the history, replace its content with a placeholder
            if i < len(messages) - 1:
                name = getattr(msg, "name", "tool")
                msg = ToolMessage(
                    content=f"[Context retrieved from {name}]",
                    name=name,
                    tool_call_id=msg.tool_call_id
                )
        cleaned_messages.append(msg)
    
    messages = cleaned_messages

    if len(messages) <= max_count:
        return messages
    
    sliced = messages[-max_count:]
    while sliced and isinstance(sliced[0], ToolMessage):
        idx = len(messages) - len(sliced)
        if idx > 0:
            sliced.insert(0, messages[idx - 1])
        else:
            break
    return sliced

def chat_node(state: ChatState, config = None):
    uploaded_files = get_uploaded_files()
    files_str = ", ".join([f"'{f}'" for f in uploaded_files]) if uploaded_files else "None"

    system_instruction = SystemMessage(
        content=(
            "You are a helpful and friendly assistant. System instructions:\n"
            f"- The currently uploaded documents in the knowledge base database are: [{files_str}]. If the user asks about 'this pdf', 'the document', or any uploaded file, you MUST use the tools (like rag_tool) to read from these current files. Do NOT rely on old file details from the history.\n"
            "- PROFILE ISOLATION: Keep candidate profiles completely isolated. When answering queries about a specific document (e.g., Kanak's resume), you MUST NOT merge, copy, or inherit facts, names, roles, or employers (like Flipkart, Blinkit, or Niyo) from other profiles mentioned in the conversation history. Keep different individuals' details 100% distinct.\n"
            "- CRITICAL: Always answer the user's query in a natural, concise, human-like summary. Do NOT copy-paste large blocks or output raw line-by-line text from the retrieved documents. Summarize the document details in 1-3 clear sentences instead (e.g., 'This is a Google IT support certificate issued to Om Bansal on Coursera.').\n"
            "- Do NOT call any tools (especially wikipedia_search or rag_tool) for personal introductions, greetings, chit-chat, or questions about the user's name (e.g. 'my name is om', 'hii', 'what is my name?'). Just reply directly as a friendly chat.\n"
            "- For questions requiring PDF contents or general knowledge, you MUST first call the appropriate tool (rag_tool or wikipedia_search) to retrieve the context. Only say that you do not know if the tools return no information.\n"
            "- For stock prices/quotes/values, you MUST call the get_stock_price tool. The returned value metric represents its stock price in USD. You MUST explicitly output this value metric to the user as the actual stock price (e.g., if the tool returns 'Value metric for AAPL: 316.22', your response MUST state that the stock price is $316.22). Do NOT hide, omit, or replace it with a disclaimer, and do NOT claim the value is simulated or fictional. Report it as the actual stock price.\n"
            "- Only call rag_tool for queries about uploaded files (resumes, certificates, documents).\n"
            "- The candidate/student's name on a certificate is the person who 'successfully completed' the course (e.g., 'Om Bansal'). Do NOT confuse the student with directors, signers, or authorizers listed at the bottom (like 'Amanda Brophy').\n"
            "- Call calculator for math, wikipedia_search for general knowledge, and get_current_time for system time.\n"
            "- IMPORTANT: You MUST include the exact numbers, names, and facts returned by tools in your response. Do not censor or alter them, but always present them in a clean, natural summary. Do NOT copy-paste raw lists or lines from the database."
        )
    )

    pruned = prune_messages(state["messages"])
    messages = [system_instruction] + pruned

    thread_id = config.get("configurable", {}).get("thread_id", "default_thread") if config else "default_thread"
    handler = active_streams.get(thread_id)
    llm_config = {}
    if handler:
        llm_config["callbacks"] = [handler]

    response = llm_with_tools.invoke(messages, config=llm_config)

    # Intercept tool calls to rewrite query using conversational history
    if response.tool_calls:
        new_tool_calls = []
        for tc in response.tool_calls:
            if tc["name"] == "rag_tool":
                original_query = tc["args"].get("query", "")
                if original_query:
                    rewritten = rewrite_query(original_query, pruned)
                    tc["args"]["query"] = rewritten
            new_tool_calls.append(tc)
        response.tool_calls = new_tool_calls
        return {
            "messages": [response]
        }

    # If this is a final response (no tool calls generated) and we just ran a RAG tool search,
    # let's run the Groundedness and Relevance check to prevent hallucinations
    last_message = pruned[-1] if pruned else None
    if (
        isinstance(last_message, ToolMessage)
        and last_message.name == "rag_tool"
    ):
        context = last_message.content
        user_query = ""
        # Find the user's corresponding query
        for msg in reversed(pruned):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break
        
        if user_query:
            is_valid = check_groundedness_and_relevance(user_query, context, response.content)
            if is_valid == "no":
                # Self-correction loop: regenerate response strictly grounded in context
                response = regenerate_grounded_response(user_query, context, thread_id)

    return {
        "messages": [response]
    }


# ---------------- SQLite ---------------- #

conn = sqlite3.connect(
    "chatbot.db",
    check_same_thread=False
)

memory = SqliteSaver(conn)

# ---------------- Graph ---------------- #

graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)

graph.add_node("tools", tool_node)

graph.add_edge(
    START,
    "chat_node"
)

graph.add_conditional_edges(
    "chat_node",
    tools_condition
)

graph.add_edge(
    "tools",
    "chat_node"
)

workflow = graph.compile(
    checkpointer=memory
)

# ---------------- Thread Utility ---------------- #

# ---------------- Thread Utility ---------------- #

def init_metadata_db():
    import sqlite3
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thread_metadata (
            thread_id TEXT PRIMARY KEY,
            is_pinned INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()

init_metadata_db()

def get_thread_metadata(thread_id: str):
    import sqlite3
    try:
        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_pinned, is_archived FROM thread_metadata WHERE thread_id = ?;", (thread_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"is_pinned": bool(row[0]), "is_archived": bool(row[1])}
    except Exception:
        pass
    return {"is_pinned": False, "is_archived": False}

def set_thread_metadata(thread_id: str, is_pinned: bool = None, is_archived: bool = None):
    import sqlite3
    try:
        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_pinned, is_archived FROM thread_metadata WHERE thread_id = ?;", (thread_id,))
        row = cursor.fetchone()
        curr_pinned = row[0] if row else 0
        curr_archived = row[1] if row else 0
        
        new_pinned = int(is_pinned) if is_pinned is not None else curr_pinned
        new_archived = int(is_archived) if is_archived is not None else curr_archived
        
        cursor.execute("""
            INSERT INTO thread_metadata (thread_id, is_pinned, is_archived)
            VALUES (?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET is_pinned=excluded.is_pinned, is_archived=excluded.is_archived;
        """, (thread_id, new_pinned, new_archived))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error setting thread metadata: {e}")

def delete_thread_from_db(thread_id: str):
    import sqlite3
    try:
        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?;", (thread_id,))
        cursor.execute("DELETE FROM checkpoint_blobs WHERE thread_id = ?;", (thread_id,))
        cursor.execute("DELETE FROM checkpoint_writes WHERE thread_id = ?;", (thread_id,))
        cursor.execute("DELETE FROM thread_metadata WHERE thread_id = ?;", (thread_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error deleting thread: {e}")

def retrieve_all_threads_metadata():
    import sqlite3
    threads = []
    try:
        conn = sqlite3.connect("chatbot.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.thread_id, MAX(c.checkpoint_id) as latest, COALESCE(m.is_pinned, 0) as pinned
            FROM checkpoints c
            LEFT JOIN thread_metadata m ON c.thread_id = m.thread_id
            WHERE COALESCE(m.is_archived, 0) = 0
            GROUP BY c.thread_id
            ORDER BY pinned DESC, latest DESC;
        """)
        rows = cursor.fetchall()
        for row in rows:
            threads.append({"thread_id": row[0], "is_pinned": bool(row[2])})
        conn.close()
    except Exception as e:
        print(f"Error retrieving threads metadata: {e}")
    
    # Fallback if no database rows
    if not threads:
        try:
            for checkpoint in memory.list(None):
                thread = checkpoint.config["configurable"]["thread_id"]
                if thread not in [t["thread_id"] for t in threads]:
                    threads.append({"thread_id": thread, "is_pinned": False})
        except Exception:
            pass
    return threads

def retrieve_all_threads() -> list[str]:
    """Backward compatibility wrapper for Streamlit frontends."""
    return [t["thread_id"] for t in retrieve_all_threads_metadata()]