import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from backend import workflow

# ---------------- Page ----------------
st.set_page_config(
    page_title="LangGraph Chatbot",
    page_icon=""
)

st.title(" LangGraph Chatbot")

# ---------------- Session State ----------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "threads" not in st.session_state:
    st.session_state.threads = {
        "Chat 1": "thread-1"
    }

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "thread-1"

# ---------------- Sidebar ----------------

with st.sidebar:

    st.title(" Chats")

    if st.button("➕ Knowledge Builder"):

        chat_no = len(st.session_state.threads) + 1

        chat_name = f"Chat {chat_no}"

        thread = f"thread-{chat_no}"

        st.session_state.threads[chat_name] = thread

        st.session_state.current_chat = chat_name

        st.session_state.thread_id = thread

        st.session_state.messages = []

        st.rerun()

    st.divider()
    for chat_name, thread in st.session_state.threads.items():

     if st.button(chat_name):

        st.session_state.current_chat = chat_name
        st.session_state.thread_id = thread

        config = {
            "configurable": {
                "thread_id": st.session_state.thread_id
            }
        }

        state = workflow.get_state(config)

        if state.values:
            st.session_state.messages = state.values["messages"]
        else:
            st.session_state.messages = []

        st.rerun()

    

        

            
            
            

            

    st.divider()

    st.write(f"Current Chat : {st.session_state.current_chat}")

    st.caption(f"Thread ID : {st.session_state.thread_id}")

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