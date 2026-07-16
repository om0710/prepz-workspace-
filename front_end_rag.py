import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
import uuid
import os

from backend_rag import workflow, retrieve_all_threads
from rag import add_pdf_to_vectordb, delete_pdf_from_vectordb, clear_all_from_vectordb

# ---------------- Query Params Sync ----------------
params = st.query_params
if "thread_id" in params:
    selected_thread = params["thread_id"]
    st.session_state.thread_id = selected_thread
    st.session_state.current_chat = selected_thread

# ---------------- Page Configuration ----------------
st.set_page_config(
    page_title="Intelligent Chat Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Streamlit UI Custom CSS Injection ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* Set font only on text elements, avoiding Streamlit SVG icons & material symbols */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
    h1, h2, h3, h4, p, textarea, input {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    span:not([class*="icon"]):not([class*="Icon"]):not([class*="material"]):not([class*="symbol"]),
    button:not([class*="icon"]):not([class*="Icon"]):not([class*="material"]) {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    /* Global Background Gradient */
    html, body, [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 10% 20%, rgb(18, 16, 32) 0%, rgb(7, 5, 14) 90%) !important;
        color: #f8fafc !important;
    }
    
    /* Hide Streamlit default decoration, deploy bar, and options menu */
    [data-testid="stDeployButton"], .stDeployButton, [data-testid="stMainMenu"], #MainMenu, footer {
        display: none !important;
        height: 0px !important;
        visibility: hidden !important;
    }
    
    /* Make header background transparent */
    [data-testid="stHeader"] {
        background: transparent !important;
    }
    
    /* Optimize padding to prevent top header from clipping the main title */
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 2rem !important;
        margin-top: 0 !important;
    }
    
    /* Main container max width limit for chat interface */
    [data-testid="stBlock"] {
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: rgba(10, 8, 22, 0.85) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    /* Streamlit reserves a separate header row at the top of the sidebar
       (stSidebarHeader) that holds the collapse-arrow control. Hiding just
       the broken icon earlier left this row's own height/padding behind -
       that reserved space was the remaining gap above "Assistant Portal".
       Collapsing the row itself removes it completely. */
    [data-testid="stSidebarHeader"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    /* Defensive: if Streamlit ever detects a multipage app (a pages/ folder),
       it injects a navigation block above stSidebarUserContent with its own
       height, independent of the header fix above. Collapsing it too. */
    [data-testid="stSidebarNav"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    /* Top padding is zeroed out here AND on the vertical block below so
       there is exactly ONE source of top spacing left in the sidebar: the
       .logo rule further down. That's what makes alignment with the main
       title reliable instead of a guessing game across multiple stacked
       padding values. */
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {
        padding: 0 16px 24px 16px !important;
    }
    
    /* Logo Styling - this padding-top is the ONLY top-spacing source in the
       sidebar now, set to the exact same 3.5rem as .block-container's
       padding-top (the main title's spacing), so the two line up. */
    .logo {
        display: flex;
        align-items: center;
        gap: 14px;
        font-size: 30px;
        font-weight: 800;
        padding-top: 3.5rem !important;
        margin-bottom: 24px !important;
        padding-left: 8px;
    }
    .logo svg {
        width: 32px !important;
        height: 32px !important;
    }
    
    /* Custom HTML Thread Items styling matching HTML5 mockup exactly */
    .thread-item {
        display: flex;
        align-items: center;
        gap: 12px;
        background-color: rgba(255, 255, 255, 0.02);
        color: #94a3b8;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 12px 16px;
        font-weight: 500;
        font-size: 14px;
        margin-bottom: 8px;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    .thread-item:hover {
        background-color: rgba(255, 255, 255, 0.05);
        color: #f8fafc;
        border-color: rgba(255, 255, 255, 0.12);
    }
    .thread-item.active {
        background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(79, 70, 229, 0.1)) !important;
        border-color: rgba(124, 58, 237, 0.4) !important;
        color: #c084fc !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.05) !important;
    }
    
    /* Primary Button Custom Styling (+ New Chat)
       Multiple selectors are targeted since Streamlit has renamed its
       internal data-testid attributes across versions (baseButton-primary,
       stBaseButton-primary, kind="primary", etc). Keeping all of them makes
       the styling resilient regardless of which Streamlit version is running. */
    div[data-testid="stButton"] button[data-testid="baseButton-primary"],
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],
    div[data-testid="stButton"] button[kind="primary"],
    div[data-testid="stButton"] button[kind="primaryFormSubmit"] {
        background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(124, 58, 237, 0.2) !important;
        justify-content: center !important;
        text-align: center !important;
        margin-bottom: 12px !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        width: 100% !important;
    }
    div[data-testid="stButton"] button[data-testid="baseButton-primary"]:hover,
    div[data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover,
    div[data-testid="stButton"] button[kind="primary"]:hover,
    div[data-testid="stButton"] button[kind="primaryFormSubmit"]:hover {
        background: linear-gradient(135deg, #8b5cf6, #6366f1) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(124, 58, 237, 0.4) !important;
        color: white !important;
    }
    
    /* Sidebar Headers style */
    [data-testid="stSidebar"] h3 {
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        color: #94a3b8 !important;
        letter-spacing: 0.05em !important;
        margin: 0 0 12px 0 !important;
        padding-left: 8px !important;
        border: none !important;
    }
    
    /* Sidebar horizontal lines */
    [data-testid="stSidebar"] hr {
        margin: 12px 0 !important;
        border-color: rgba(255, 255, 255, 0.06) !important;
    }
    
    /* Chat Message Bubbles styling
       Rendered via our own HTML/CSS (see .chat-row / .chat-bubble below)
       instead of relying on Streamlit's st.chat_message internals, whose
       data-testid attributes have changed across Streamlit versions. */
    .chat-scroll-wrapper {
        max-width: 800px;
        margin: 0 auto;
    }
    .chat-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 16px;
    }
    .chat-row.user {
        flex-direction: row-reverse;
    }
    .chat-avatar {
        flex-shrink: 0;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 17px;
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .chat-bubble {
        max-width: 75%;
        padding: 16px 20px;
        border-radius: 16px;
        font-size: 15px;
        line-height: 1.6;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .chat-bubble.user {
        background: linear-gradient(135deg, #7c3aed, #4f46e5);
        color: #ffffff;
        border: none;
        border-bottom-right-radius: 4px;
        box-shadow: 0 4px 20px rgba(124, 58, 237, 0.15);
    }
    .chat-bubble.assistant {
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        color: #f8fafc;
        border-bottom-left-radius: 4px;
    }
    
    /* Code blocks customization */
    code {
        color: #f472b6 !important;
        font-family: 'Courier New', Courier, monospace !important;
    }
    pre {
        background-color: rgba(15, 12, 30, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
    }
    
    /* Knowledge Base PDF Uploader Box styling */
    [data-testid="stFileUploader"] {
        background-color: rgba(255, 255, 255, 0.01) !important;
        border: 2.5px dashed rgba(124, 58, 237, 0.35) !important;
        border-radius: 12px !important;
        padding: 28px 16px !important;
        transition: all 0.3s ease !important;
        margin-top: 12px !important;
        text-align: center !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #c084fc !important;
        background-color: rgba(124, 58, 237, 0.04) !important;
    }
    
    /* Hide all default elements inside the dropzone container to prevent overlapping */
    [data-testid="stFileUploaderDropzone"] > * {
        display: none !important;
    }
    
    /* Inject custom cloud upload icon */
    [data-testid="stFileUploaderDropzone"]::before {
        content: "" !important;
        display: block !important;
        width: 36px !important;
        height: 36px !important;
        margin: 0 auto 10px auto !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='36' height='36' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpolyline points='17 8 12 3 7 8'/%3E%3Cline x1='12' y1='3' x2='12' y2='15'/%3E%3C/svg%3E") !important;
        background-repeat: no-repeat !important;
        background-size: contain !important;
        opacity: 0.8;
    }
    
    /* Inject custom upload instruction text */
    [data-testid="stFileUploaderDropzone"]::after {
        content: "Drag & Drop PDF or Click to Upload" !important;
        color: #94a3b8 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        display: block !important;
        text-align: center !important;
        margin-top: 10px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    /* Chat Input Bar style */
    [data-testid="stChatInput"] {
        background-color: rgba(15, 12, 30, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 30px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(15px) !important;
        padding: 8px 12px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #f8fafc !important;
    }
    
    /* Style Chat Input Send Button to be purple and rounded */
    [data-testid="stChatInput"] button {
        background-color: #7c3aed !important;
        color: white !important;
        border-radius: 50% !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stChatInput"] button:hover {
        background-color: #8b5cf6 !important;
        transform: scale(1.05) !important;
    }
    
    /* The sidebar collapse/expand controls render their icon via Streamlit's
       Material Symbols ligature text (e.g. "keyboard_double_arrow_left/right"),
       and that font isn't loading here, so the raw text shows instead of an
       arrow glyph. Hiding every possible testid/element these controls can
       use (this varies by Streamlit version) removes it completely. */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stIconMaterial"],
    button:has(> [data-testid="stIconMaterial"]) {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
    }

    /* ---------------- Empty State Welcome Screen ---------------- */
    .empty-state-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        min-height: 55vh;
        padding: 0 24px;
    }
    .empty-state-title {
        font-size: 30px;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.02em;
        margin-bottom: 14px;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .empty-state-subtitle {
        font-size: 15px;
        font-weight: 500;
        color: #94a3b8;
        max-width: 560px;
        line-height: 1.6;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Typing Indicator Styles */
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
    }
    .typing-indicator span {
        width: 8px;
        height: 8px;
        background-color: #a78bfa;
        border-radius: 50%;
        display: inline-block;
        animation: bounce 1.4s infinite ease-in-out both;
    }
    .typing-indicator span:nth-child(1) {
        animation-delay: -0.32s;
    }
    .typing-indicator span:nth-child(2) {
        animation-delay: -0.16s;
    }
    @keyframes bounce {
        0%, 80%, 100% { 
            transform: scale(0.3);
        } 40% { 
            transform: scale(1.0);
            background-color: #818cf8;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Session State Initialization ----------------
if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = retrieve_all_threads()

if "thread_id" not in st.session_state:
    if st.session_state.chat_threads:
        st.session_state.thread_id = st.session_state.chat_threads[0]
    else:
        st.session_state.thread_id = str(uuid.uuid4())

if st.session_state.thread_id not in st.session_state.chat_threads:
    st.session_state.chat_threads.insert(0, st.session_state.thread_id)

if "current_chat" not in st.session_state:
    st.session_state.current_chat = st.session_state.thread_id

if "messages" not in st.session_state:
    config = {
        "configurable": {
            "thread_id": st.session_state.thread_id
        }
    }
    state = workflow.get_state(config)
    if state.values and "messages" in state.values:
        st.session_state.messages = state.values["messages"]
    else:
        st.session_state.messages = []

if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

# ---------------- Sidebar Layout ----------------
with st.sidebar:
    st.markdown(
        """
        <div class="logo" style="font-family: 'Plus Jakarta Sans', sans-serif;">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-message-square-code"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="m10 8-2 2 2 2"/><path d="m14 8 2 2-2 2"/></svg>
            <span style="color: #ffffff;">Assistant </span><span style="color: #c084fc;">Portal</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if st.button("➕ New Chat", type="primary", use_container_width=True):
        new_thread = str(uuid.uuid4())
        st.session_state.thread_id = new_thread
        st.session_state.current_chat = new_thread
        st.session_state.messages = []
        if new_thread not in st.session_state.chat_threads:
            st.session_state.chat_threads.append(new_thread)
        st.rerun()

    st.divider()
    st.markdown("### 💬 ACTIVE SESSIONS")

    # List chat threads inside a scrollable container
    # (border=False avoids the default bordered box that newer Streamlit
    # versions render around st.container(height=...) by default)
    try:
        sessions_container = st.container(height=320, border=False)
    except TypeError:
        # Older Streamlit versions don't accept the `border` kwarg
        sessions_container = st.container(height=320)

    with sessions_container:
        for thread in st.session_state.chat_threads:
            short_id = thread[:8] + "..." if len(thread) > 8 else thread
            is_current = (thread == st.session_state.thread_id)
            
            active_class = "active" if is_current else ""
            
            # HTML Link-based thread switcher with exact visual styles matching client mockup
            st.markdown(
                f"""
                <a href="?thread_id={thread}" target="_self" style="text-decoration: none;">
                    <div class="thread-item {active_class}">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        <span>Chat {short_id}</span>
                    </div>
                </a>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    # ---------------- Knowledge Base Manager in Sidebar ----------------
    st.markdown("### 📄 KNOWLEDGE BASE")
    
    # 1. File Uploader
    uploaded_file = st.file_uploader(
        "Upload PDF context",
        type=["pdf"],
        label_visibility="collapsed",
        key="rag_pdf_uploader"
    )

    if uploaded_file is not None:
        file_name = uploaded_file.name
        if file_name not in st.session_state.processed_files:
            os.makedirs("uploads", exist_ok=True)
            pdf_path = os.path.join("uploads", file_name)
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner("Analyzing PDF..."):
                add_pdf_to_vectordb(pdf_path)
            st.session_state.processed_files.add(file_name)
            st.success("✅ Context uploaded and indexed!")
            st.rerun()

    # 2. List & Manage Uploaded Files
    if os.path.exists("uploads"):
        pdf_files = [f for f in os.listdir("uploads") if f.endswith(".pdf")]
        # Keep processed_files in sync with disk contents (for persistence across restarts)
        for pdf_file in pdf_files:
            st.session_state.processed_files.add(pdf_file)
            
        if pdf_files:
            st.markdown("#### 📁 Indexed Files:")
            for pdf_file in pdf_files:
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    short_name = pdf_file[:22] + "..." if len(pdf_file) > 22 else pdf_file
                    st.caption(f"📄 {short_name}")
                with col2:
                    if st.button("🗑️", key=f"del_{pdf_file}", help=f"Delete {pdf_file} from database"):
                        pdf_path = f"uploads/{pdf_file}"
                        delete_pdf_from_vectordb(pdf_path)
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
                        if pdf_file in st.session_state.processed_files:
                            st.session_state.processed_files.remove(pdf_file)
                        st.success(f"Deleted {pdf_file}!")
                        st.rerun()
            
            st.markdown("---")
            if st.button("🚨 Clear All Files", use_container_width=True, help="Wipe out the entire database and start fresh"):
                clear_all_from_vectordb()
                import shutil
                if os.path.exists("uploads"):
                    shutil.rmtree("uploads")
                st.session_state.processed_files.clear()
                st.success("Cleared entire knowledge base!")
                st.rerun()
        else:
            st.info("No documents uploaded yet.")
    else:
        st.info("No documents uploaded yet.")

# ---------------- Main Chat Area ----------------
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); padding-bottom: 16px;">
        <div style="font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; font-family: 'Plus Jakarta Sans', sans-serif;">Intelligent Chat <span style="color: #c084fc;">Agent</span></div>
    </div>
    """,
    unsafe_allow_html=True
)


# ---------------- Custom Bubble Renderer ----------------
# Streamlit's st.chat_message() relies on internal data-testid attributes
# (stChatMessageUser / stChatMessageAssistant) that have changed across
# Streamlit versions, which is why the purple/dark bubble styling was not
# applying. Rendering our own HTML bubble in a single st.markdown() call
# guarantees the exact look regardless of the Streamlit version installed,
# without touching any backend/workflow logic.
import html as _html
import re as _re


def _format_bubble_text(content: str) -> str:
    """Lightly convert markdown-ish text to safe HTML for bubble display."""
    escaped = _html.escape(content)
    # inline code `code`
    escaped = _re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    # bold **text**
    escaped = _re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    # newlines
    escaped = escaped.replace("\n", "<br>")
    return escaped


def render_bubble_html(content: str, role: str) -> str:
    avatar = "👤" if role == "user" else "🤖"
    return f"""
    <div class="chat-row {role}">
        <div class="chat-avatar">{avatar}</div>
        <div class="chat-bubble {role}">{_format_bubble_text(content)}</div>
    </div>
    """


def render_bubble(content: str, role: str):
    st.markdown(render_bubble_html(content, role), unsafe_allow_html=True)


def render_typing_indicator_html() -> str:
    return """
    <div class="chat-row assistant">
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble assistant" style="display: flex; align-items: center; gap: 8px; padding: 12px 18px;">
            <div class="typing-indicator" style="padding: 0; margin: 0; display: flex; align-items: center; gap: 4px;">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <div style="color: #94a3b8; font-size: 14px; font-weight: 500; font-family: 'Plus Jakarta Sans', sans-serif;">typing...</div>
        </div>
    </div>
    """


# ---------------- Chat History / Empty State ----------------
if len(st.session_state.messages) == 0:
    st.markdown(
        """
        <div class="empty-state-wrapper">
            <div class="empty-state-title">Hello! How can I assist you today?</div>
            <div class="empty-state-subtitle">
                I have access to your PDF knowledge base, mathematical tools, Wikipedia, and live stock queries.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown('<div class="chat-scroll-wrapper">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            render_bubble(msg.content, "user")
        elif isinstance(msg, AIMessage):
            if msg.content:
                render_bubble(msg.content, "assistant")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Chat Input ----------------
user_input = st.chat_input("Ask anything...")

if user_input:
    user_msg = HumanMessage(content=user_input)
    st.session_state.messages.append(user_msg)

    render_bubble(user_input, "user")

    config = {
        "configurable": {
            "thread_id": st.session_state.thread_id
        }
    }

    placeholder = st.empty()
    
    # Show typing indicator while graph computes response
    placeholder.markdown(
        render_typing_indicator_html(),
        unsafe_allow_html=True
    )
    
    full_response = ""
    try:
        for chunk in workflow.stream(
            {
                "messages": [user_msg]
            },
            config=config,
            stream_mode="values"
        ):
            ai_message = chunk["messages"][-1]
            if isinstance(ai_message, AIMessage):
                full_response = ai_message.content

        if not full_response:
            full_response = "⚠️ I received an empty response. Please check if your LLM connection is functioning properly."

        # Stream the final response word-by-word with a typewriter/streaming effect
        import time
        words = full_response.split(" ")
        displayed_text = ""
        for i, word in enumerate(words):
            if i == 0:
                displayed_text = word
            else:
                displayed_text += " " + word
            placeholder.markdown(
                render_bubble_html(displayed_text + "▌", "assistant"),
                unsafe_allow_html=True
            )
            time.sleep(0.03)  # 30ms typing speed per word

        placeholder.markdown(
            render_bubble_html(full_response, "assistant"),
            unsafe_allow_html=True
        )

        st.session_state.messages.append(
            AIMessage(content=full_response)
        )
    except Exception as e:
        error_msg = f"⚠️ **Service Connection Error**: {str(e)}\n\n*Please verify that your `GROQ_API_KEY` in the `.env` file is valid and check your network connection.*"
        placeholder.markdown(
            render_bubble_html(error_msg, "assistant"),
            unsafe_allow_html=True
        )
        st.session_state.messages.append(
            AIMessage(content=error_msg)
        )

    # Refresh sidebar thread list from SQLite
    st.session_state.chat_threads = retrieve_all_threads()