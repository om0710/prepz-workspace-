from dotenv import load_dotenv
import os

from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool

load_dotenv()

# ---------------- LLM ---------------- #

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

# ---------------- Text Splitter ---------------- #

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

# ---------------- Embeddings ---------------- #

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

def add_pdf_to_vectordb(pdf_path):

    # Prevent duplicate indexing if file already indexed
    try:
        existing = vectorstore._collection.get(where={"source": pdf_path}, limit=1)
        if existing and existing.get("ids"):
            print(f"{pdf_path} is already indexed in the vector store. Skipping.")
            return
    except Exception:
        pass

    loader = PyPDFLoader(pdf_path)

    docs = loader.load()

    for doc in docs:
        if is_spaced_out(doc.page_content):
            doc.page_content = clean_spaced_text(doc.page_content)

    chunks = splitter.split_documents(docs)

    vectorstore.add_documents(chunks)

    print(f"{pdf_path} added successfully!")

def delete_pdf_from_vectordb(pdf_path):
    try:
        vectorstore._collection.delete(where={"source": pdf_path})
        print(f"{pdf_path} deleted from vector store successfully!")
    except Exception as e:
        print(f"Error deleting {pdf_path} from vector store: {e}")

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