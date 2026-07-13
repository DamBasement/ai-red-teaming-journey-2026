"""
Multi-step agent built with LangGraph, node by node.
 
Flow:
  user -> [agent] -> decides whether to call a tool -> [tools] -> back to [agent]
                   -> if no more tools are needed -> END
 
This is the "ReAct" pattern (Reason + Act) built by hand.
Understanding this graph is the foundation for understanding WHERE an
attacker can insert themselves:
- in the user input (direct prompt injection)
- in the content read by the read_file tool (indirect prompt injection)
- in the tool output that goes back to the model (context poisoning)
"""
 
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
 
from tools import ALL_TOOLS
 
load_dotenv()  # loads ANTHROPIC_API_KEY from the .env file, if present
 
 
# --- 1. Graph state definition ---
class AgentState(TypedDict):
    # `add_messages` makes new messages accumulate
    # instead of overwriting the previous ones
    messages: Annotated[list, add_messages]
    # Safety counter: how many times the "agent" node has run
    step_count: int
 
 
# Maximum number of agent->tools cycles allowed before forcing a stop.
# Without this limit, malicious content read by a tool could in theory
# induce the model to request tool calls indefinitely.
MAX_STEPS = 6
 
 
# --- 2. Model with tools "bound" to it ---
llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
llm_with_tools = llm.bind_tools(ALL_TOOLS)
 
 
# --- 3. "agent" node: the model reasons and decides what to do ---
def agent_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(state["messages"])
    current_steps = state.get("step_count", 0)
    return {"messages": [response], "step_count": current_steps + 1}
 
 
# --- 4. "tools" node: executes the tools requested by the model ---
tool_node = ToolNode(ALL_TOOLS)
 
 
# --- 5. Routing logic: continue or stop? ---
def should_continue(state: AgentState) -> str:
    # Circuit breaker: if we've exceeded the maximum number of cycles,
    # stop the agent regardless of what the model wants to do.
    if state.get("step_count", 0) >= MAX_STEPS:
        print(f"\n⚠️  FORCED STOP: reached the limit of {MAX_STEPS} steps.\n")
        return END
 
    last_message = state["messages"][-1]
    # If the model requested a tool, go to the tools node
    if getattr(last_message, "tool_calls", None):
        return "tools"
    # Otherwise we're done
    return END
 
 
# --- 6. Graph construction ---
def build_graph():
    graph = StateGraph(AgentState)
 
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
 
    graph.set_entry_point("agent")
 
    # After the agent, decide whether to go to tools or finish
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        END: END,
    })
 
    # After running the tools, always go back to the agent
    # (this is the loop that makes the agent "multi-step")
    graph.add_edge("tools", "agent")
 
    return graph.compile()
 
 
if __name__ == "__main__":
    app = build_graph()
 
    system_prompt = (
        "You are an assistant that analyzes sales reports. "
        "You have access to tools for reading files, counting words, extracting numbers, "
        "and converting currencies using real exchange rates. "
        "Use the tools you need, then produce a clear summary in English."
    )
 
    user_task = (
        "Read the file sample_data/report.txt, then tell me how many words it contains "
        "and what the main numbers are. Also convert the total revenue "
        "(sum of the three products) from EUR to USD using the real exchange rate. "
        "Conclude with a 2-line summary."
    )
 
    result = app.invoke({
        "messages": [
            ("system", system_prompt),
            ("user", user_task),
        ],
        "step_count": 0,
    }, config={"recursion_limit": 50})
 
    print("\n=== FULL CONVERSATION (to understand each step) ===\n")
    for msg in result["messages"]:
        role = msg.__class__.__name__
        content = msg.content if isinstance(msg.content, str) else msg.content
        print(f"[{role}] {content}\n")
 
    print("=== FINAL RESPONSE ===")
    print(result["messages"][-1].content)
