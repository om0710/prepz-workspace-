import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from database import workflow , retrieve_all_threads
import uuid
# ---------------- Page ----------------
st.set_page_config(
    page_title="LangGraph Chatbot",
    page_icon=""
)

st.title(" LangGraph Chatbot")

# ---------------- Session State ----------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = retrieve_all_threads()

# Add current thread if it doesn't already exist
if st.session_state.thread_id not in st.session_state.chat_threads:
    st.session_state.chat_threads.append(st.session_state.thread_id)

if "current_chat" not in st.session_state:
    st.session_state.current_chat = st.session_state.thread_id

# ---------------- Sidebar ----------------


with st.sidebar:

    st.title(" Chats")

    if st.button("➕ Knowledge Builder"):

        new_thread = str(uuid.uuid4())

        st.session_state.thread_id = new_thread
        st.session_state.current_chat = new_thread
        st.session_state.messages = []

        if new_thread not in st.session_state.chat_threads:
            st.session_state.chat_threads.append(new_thread)

        st.rerun()

    st.divider()

    for thread in st.session_state.chat_threads:

        if st.button(thread):

            st.session_state.thread_id = thread
            st.session_state.current_chat = thread

            config = {
                "configurable": {
                    "thread_id": thread
                }
            }

            state = workflow.get_state(config)

            if state.values:
                st.session_state.messages = state.values["messages"]
            else:
                st.session_state.messages = []

            st.rerun()

    st.divider()

    st.write("Current Thread")
    st.code(st.session_state.thread_id)
# ---------------- Chat History ----------------

for msg in st.session_state.messages:

    role = "user" if isinstance(msg, HumanMessage) else "assistant"

    with st.chat_message(role):
        st.markdown(msg.content)


# ---------------- Chat Input ----------------

user_input = st.chat_input("Type your message...")

if user_input:

    user_msg = HumanMessage(content=user_input)

    st.session_state.messages.append(user_msg)

    with st.chat_message("user"):
        st.markdown(user_input)

    config = {
        "configurable": {
            "thread_id": st.session_state.thread_id
        }
    }

    with st.chat_message("assistant"):

        placeholder = st.empty()
        full_response = ""

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
                placeholder.markdown(full_response + "▌")

        placeholder.markdown(full_response)

    st.session_state.messages.append(
        AIMessage(content=full_response)
    )

    # Refresh sidebar thread list from SQLite
st.session_state.chat_threads = retrieve_all_threads()