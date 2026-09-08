from langgraph.graph import StateGraph, START, END
from src.state.graph_state import AgentState
from src.agents.uc9_supervisor import supervisor_node
from src.agents.uc9_specialist_nodes import (
    consumption_monitor_node,
    transfer_optimizer_node,
    procurement_trigger_node,
    capital_optimizer_node
)

def build_uc9_replenishment_system():
    # 1. Initialize the graph with our strict typed state
    builder = StateGraph(AgentState)
    
    # 2. Add all workflow nodes
    builder.add_node("Supervisor", supervisor_node)
    builder.add_node("Consumption_Monitor", consumption_monitor_node)
    builder.add_node("Transfer_Optimizer", transfer_optimizer_node)
    builder.add_node("Procurement_Trigger", procurement_trigger_node)
    builder.add_node("Capital_Optimizer", capital_optimizer_node)
    
    # 3. Define Entry Point
    builder.add_edge(START, "Supervisor")
    
    # 4. Define Conditional Routing from the Supervisor
    builder.add_conditional_edges(
        "Supervisor",
        lambda state: state["next_agent"],
        {
            "Consumption_Monitor": "Consumption_Monitor",
            "Transfer_Optimizer": "Transfer_Optimizer",
            "Procurement_Trigger": "Procurement_Trigger",
            "FINISH": "Capital_Optimizer"
        }
    )
    
    # 5. Define Node Returns (Specialists always report back to the Supervisor)
    builder.add_edge("Consumption_Monitor", "Supervisor")
    builder.add_edge("Transfer_Optimizer", "Supervisor")
    builder.add_edge("Procurement_Trigger", "Supervisor")
    
    # 6. Define Exit Point
    builder.add_edge("Capital_Optimizer", END)
    
    return builder.compile()