from dotenv import load_dotenv
import os

load_dotenv()

from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

groq_key = os.environ.get("GROQ_API_KEY")
if not groq_key:
    raise RuntimeError("GROQ_API_KEY environment variable is missing. Please configure it in your .env file.")
os.environ["GROQ_API_KEY"] = groq_key

# ---------------- LLM ---------------- #

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    groq_api_key=groq_key
)

# ---------------- Text Splitter ---------------- #

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

# ---------------- Embeddings ---------------- #

try:
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
except Exception:
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"local_files_only": True}
        )
    except Exception as e:
        print(f"[EMBEDDINGS NOTICE] HuggingFaceEmbeddings init offline fallback: {e}")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

# ---------------- Vector Store ---------------- #

vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings
)

# ---------------- Retriever ---------------- #

retriever = vectorstore.as_retriever(
    search_kwargs={"k": 3},
    search_type="similarity"
)

def is_spaced_out(text: str) -> bool:
    tokens = text.split()
    if not tokens:
        return False
    avg_len = sum(len(t) for t in tokens) / len(tokens)
    return avg_len < 1.8

def clean_spaced_text(text: str) -> str:
    cleaned_lines = []
    for line in text.split('\n'):
        if not line.strip():
            cleaned_lines.append('')
            continue
        words = line.split('  ')
        cleaned_words = [word.replace(' ', '') for word in words]
        cleaned_lines.append(' '.join(cleaned_words))
    return '\n'.join(cleaned_lines)

import re
from langchain_core.documents import Document

def extract_text_from_file(file_path: str) -> list[Document]:
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == ".docx":
        try:
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            if docs and any(d.page_content.strip() for d in docs):
                return docs
        except Exception:
            pass

        try:
            import docx
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    row_txt = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if row_txt:
                        full_text.append(row_txt)
            text = "\n".join(full_text)
        except Exception:
            pass

    elif ext == ".doc":
        # Try docx2txt / python-docx first in case file is openxml with .doc extension
        try:
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            if docs and any(d.page_content.strip() for d in docs):
                return docs
        except Exception:
            pass

        try:
            import docx
            doc = docx.Document(file_path)
            full_text = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(full_text)
        except Exception:
            pass

        # Fallback for binary .doc files: extract printable text strings
        if not text.strip():
            try:
                with open(file_path, "rb") as f:
                    raw_bytes = f.read()
                printable_strings = re.findall(b'[\x20-\x7E\t\r\n]{4,}', raw_bytes)
                extracted_words = [s.decode('utf-8', errors='ignore').strip() for s in printable_strings if len(s.strip()) > 3]
                text = "\n".join(extracted_words)
            except Exception:
                pass

    if not text.strip():
        try:
            loader = PyPDFLoader(file_path)
            return loader.load()
        except Exception:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception:
                text = f"Document content from {os.path.basename(file_path)}"

    return [Document(page_content=text, metadata={"source": file_path})]

def add_file_to_vectordb(file_path, user_email="anonymous@college.edu", user_name="Anonymous", subject="General Engineering", semester="Semester 1", file_type="Notes"):

    # Prevent duplicate indexing if file already indexed
    try:
        existing = vectorstore._collection.get(where={"source": file_path}, limit=1)
        if existing and existing.get("ids"):
            print(f"{file_path} is already indexed in the vector store. Skipping.")
            return
    except Exception:
        pass

    try:
        docs = extract_text_from_file(file_path)
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        docs = [Document(page_content=f"Document content from {os.path.basename(file_path)}", metadata={"source": file_path})]

    for doc in docs:
        if is_spaced_out(doc.page_content):
            doc.page_content = clean_spaced_text(doc.page_content)
        if user_email:
            doc.metadata["uploaded_by_email"] = user_email
        if user_name:
            doc.metadata["uploaded_by_name"] = user_name
        if subject:
            doc.metadata["subject"] = subject
        if semester:
            doc.metadata["semester"] = semester
        if file_type:
            doc.metadata["file_type"] = file_type

    chunks = splitter.split_documents(docs)
    if chunks:
        vectorstore.add_documents(chunks)

    print(f"{file_path} ({subject}, {semester}, {file_type}) added successfully for user {user_email}!")

# Backward compatibility aliases
add_pdf_to_vectordb = add_file_to_vectordb

def delete_pdf_from_vectordb(pdf_path):
    try:
        vectorstore._collection.delete(where={"source": pdf_path})
        print(f"{pdf_path} deleted from vector store successfully!")
    except Exception as e:
        print(f"Error deleting {pdf_path} from vector store: {e}")

delete_file_from_vectordb = delete_pdf_from_vectordb

def clear_all_from_vectordb():
    try:
        results = vectorstore._collection.get()
        if results and "ids" in results:
            all_ids = results["ids"]
            if all_ids:
                chunk_size = 500
                for i in range(0, len(all_ids), chunk_size):
                    batch_ids = all_ids[i:i+chunk_size]
                    vectorstore._collection.delete(ids=batch_ids)
                print(f"Cleared {len(all_ids)} entries from vector store successfully!")
            else:
                print("Vector store was already empty.")
        else:
            print("Vector store was already empty.")
    except Exception as e:
        print(f"Error clearing vector store: {e}")
        raise e
def get_all_indexed_files():
    try:
        results = vectorstore._collection.get(include=["metadatas"])
        if results and results.get("metadatas"):
            sources = set()
            for meta in results["metadatas"]:
                if meta and "source" in meta:
                    sources.add(os.path.basename(meta["source"]))
            return sorted(list(sources))
    except Exception as e:
        print(f"Error in get_all_indexed_files: {e}")
    return []



# ---------------- RAG Tool ---------------- #

@tool
def rag_tool(query: str):
    """
    Search the uploaded PDF knowledge base.

    Use this tool ONLY when the user asks questions
    that require information from uploaded PDFs.
    """

    docs = retriever.invoke(query)

    context = [doc.page_content for doc in docs]

    metadata = [doc.metadata for doc in docs]

    return {
        "query": query,
        "context": context,
        "metadata": metadata
    }

# ---------------- Tools ---------------- #

tools = [rag_tool]

llm_with_tools = llm.bind_tools(tools)