"""
Agente multi-step costruito con LangGraph, nodo per nodo.
 
Flusso:
  utente -> [agent] -> decide se chiamare un tool -> [tools] -> torna a [agent]
                     -> se non serve altro tool -> FINE
 
Questo è il pattern "ReAct" (Reason + Act) fatto a mano.
Capire questo grafo è la base per capire DOVE un attaccante può inserirsi:
- nell'input utente (prompt injection diretta)
- nel contenuto letto dal tool read_file (prompt injection indiretta)
- nell'output del tool che torna al modello (data poisoning del contesto)
"""
 
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
 
from tools import ALL_TOOLS
 
load_dotenv()  # carica ANTHROPIC_API_KEY dal file .env, se presente
 
 
# --- 1. Definizione dello stato del grafo ---
class AgentState(TypedDict):
    # `add_messages` fa in modo che i nuovi messaggi si accumulino
    # invece di sovrascrivere quelli precedenti
    messages: Annotated[list, add_messages]
    # Contatore di sicurezza: quante volte il nodo "agent" è stato eseguito
    step_count: int
 
 
# Numero massimo di cicli agent->tools consentiti prima di forzare lo stop.
# Senza questo limite, un contenuto malevolo letto da un tool potrebbe in
# teoria indurre il modello a richiedere tool call all'infinito.
MAX_STEPS = 6
 
 
# --- 2. Modello con i tool "agganciati" ---
llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
llm_with_tools = llm.bind_tools(ALL_TOOLS)
 
 
# --- 3. Nodo "agent": il modello ragiona e decide cosa fare ---
def agent_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(state["messages"])
    current_steps = state.get("step_count", 0)
    return {"messages": [response], "step_count": current_steps + 1}
 
 
# --- 4. Nodo "tools": esegue i tool richiesti dal modello ---
tool_node = ToolNode(ALL_TOOLS)
 
 
# --- 5. Logica di instradamento: continuare o fermarsi? ---
def should_continue(state: AgentState) -> str:
    # Circuit breaker: se abbiamo superato il numero massimo di cicli,
    # fermiamo l'agente indipendentemente da cosa vorrebbe fare il modello.
    if state.get("step_count", 0) >= MAX_STEPS:
        print(f"\n⚠️  STOP FORZATO: raggiunto il limite di {MAX_STEPS} step.\n")
        return END
 
    last_message = state["messages"][-1]
    # Se il modello ha chiesto di usare un tool, andiamo al nodo tools
    if getattr(last_message, "tool_calls", None):
        return "tools"
    # Altrimenti abbiamo finito
    return END
 
 
# --- 6. Costruzione del grafo ---
def build_graph():
    graph = StateGraph(AgentState)
 
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
 
    graph.set_entry_point("agent")
 
    # Dopo l'agente, decidi se andare ai tool o finire
    graph.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        END: END,
    })
 
    # Dopo aver eseguito i tool, torna sempre all'agente
    # (questo è il ciclo che rende l'agente "multi-step")
    graph.add_edge("tools", "agent")
 
    return graph.compile()
 
 
if __name__ == "__main__":
    app = build_graph()
 
    system_prompt = (
        "Sei un assistente che analizza report di vendita. "
        "Hai accesso a tool per leggere file, contare parole, estrarre numeri "
        "e convertire valute con tassi di cambio reali. "
        "Usa i tool necessari, poi produci un riepilogo chiaro in italiano."
    )
 
    user_task = (
        "Leggi il file sample_data/report.txt, poi dimmi quante parole contiene "
        "e quali numeri principali riporta. Converti anche il ricavo totale "
        "(somma dei tre prodotti) da EUR a USD usando il tasso di cambio reale. "
        "Concludi con un riepilogo di 2 righe."
    )
 
    result = app.invoke({
        "messages": [
            ("system", system_prompt),
            ("user", user_task),
        ],
        "step_count": 0,
    }, config={"recursion_limit": 50})
 
    print("\n=== CONVERSAZIONE COMPLETA (per capire ogni step) ===\n")
    for msg in result["messages"]:
        role = msg.__class__.__name__
        content = msg.content if isinstance(msg.content, str) else msg.content
        print(f"[{role}] {content}\n")
 
    print("=== RISPOSTA FINALE ===")
    print(result["messages"][-1].content)
