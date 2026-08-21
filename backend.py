from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from typing import TypedDict, Annotated
from langchain_groq import ChatGroq

import os
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage

# Persistence
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState):
    # Take query from user
    messages = state["messages"]

    # Send to LLM
    response = llm.invoke(messages)

    # Store response in state
    return {
        "messages": [response]
    }


memory = MemorySaver()

graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)

graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

# Compile with persistence
workflow = graph.compile(checkpointer=memory)
thread_id = "1"
config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
workflow.get_state(config)
# this is for streaming 
# thread_id = "1"
# config = {
#         "configurable": {
#             "thread_id": thread_id
#         }
#     }
# for message_chunk,metadata in  workflow.stream(
#         {
#             "messages": [HumanMessage(content = 'what is the receipe to make pasta')]
#         },
#         config=config,
#         stream_mode='messages'

# ):
#     if message_chunk.content:
#         print(message_chunk.content , end = " ",flush=True)

