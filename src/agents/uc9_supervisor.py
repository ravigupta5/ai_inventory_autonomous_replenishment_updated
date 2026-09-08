from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from pydantic import BaseModel
from typing import Literal

from src.state.graph_state import AgentState
from src.agents.uc9_prompts import SUPERVISOR_PROMPT

class Route(BaseModel):
    next_agent: Literal[
        "Consumption_Monitor", 
        "Transfer_Optimizer", 
        "Procurement_Trigger", 
        "FINISH"
    ]

def supervisor_node(state: AgentState):
    """
    Analyzes the state and determines the next agent.
    Includes hardcoded Python guardrails to prevent hallucinated routing.
    """
    # HARDCODED GUARDRAIL: Short-circuit if there is no deficit (e.g., VALV-102)
    if state.get("quantity_needed") == 0:
        return {"next_agent": "FINISH"}
        
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    supervisor_chain = llm.with_structured_output(Route)
    
    formatted_prompt = SUPERVISOR_PROMPT.format(current_part_id=state["current_part_id"])
    system_msg = SystemMessage(content=formatted_prompt)
    
    route_result = supervisor_chain.invoke([system_msg] + state["messages"])
    
    return {"next_agent": route_result.next_agent}