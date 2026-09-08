from typing import Annotated, Sequence, TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """
    Represents the shared, strict state of the LangGraph multi-agent system.
    """
    # Tracks the conversation history and agent reports
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # 1. Core Identifiers
    current_part_id: str
    active_alerts: list[str]
    next_agent: str
    
    # 2. Mathematical State Variables (Prevents LLM Hallucination)
    deficit_site: str
    quantity_needed: int
    part_weight_kg: float
    
    # 3. Fulfillment Options
    # Format: [{"site": "Sishen", "surplus": 3, "transit_days": 1, "freight_rate": 12.0}]
    surplus_options: List[Dict[str, Any]]
    
    # Format: {"vendor_name": "Supplier A", "lead_time_days": 10, "purchase_cost_zar": 5000.0}
    vendor_quote: Dict[str, Any]