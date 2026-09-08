import os
import json
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from src.state.graph_state import AgentState
from src.tools.uc9_sql_tools import get_network_inventory, get_logistics_routes, get_vendor_quotes
from src.agents.uc9_prompts import (
    CONSUMPTION_MONITOR_PROMPT,
    TRANSFER_OPTIMIZER_PROMPT,
    PROCUREMENT_TRIGGER_PROMPT,
    CAPITAL_OPTIMIZER_PROMPT
)

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Instantiate ReAct agents
consumption_agent = create_react_agent(llm, tools=[get_network_inventory])
transfer_agent = create_react_agent(llm, tools=[get_logistics_routes, get_network_inventory])
procurement_agent = create_react_agent(llm, tools=[get_vendor_quotes])

def extract_json(text: str) -> dict:
    """Safely extracts JSON from LLM output, bypassing markdown blocks."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(text) # Fallback if no markdown blocks are used

def consumption_monitor_node(state: AgentState):
    prompt = SystemMessage(content=CONSUMPTION_MONITOR_PROMPT.format(current_part_id=state["current_part_id"]))
    result = consumption_agent.invoke({"messages": [prompt] + state["messages"]})
    
    # Parse the LLM's JSON and update our strict state variables
    data = extract_json(result['messages'][-1].content)
    
    return {
        "messages": [HumanMessage(content=f"Consumption Data Extracted: {data}", name="Consumption_Monitor")],
        "deficit_site": data.get("deficit_site", "None"),
        "quantity_needed": data.get("quantity_needed", 0),
        "part_weight_kg": data.get("part_weight_kg", 0.0)
    }

def transfer_optimizer_node(state: AgentState):
    prompt = SystemMessage(content=TRANSFER_OPTIMIZER_PROMPT.format(current_part_id=state["current_part_id"]))
    result = transfer_agent.invoke({"messages": [prompt] + state["messages"]})
    
    data = extract_json(result['messages'][-1].content)
    
    return {
        "messages": [HumanMessage(content=f"Transfer Data Extracted: {data}", name="Transfer_Optimizer")],
        "surplus_options": data.get("surplus_options", [])
    }

def procurement_trigger_node(state: AgentState):
    prompt = SystemMessage(content=PROCUREMENT_TRIGGER_PROMPT.format(current_part_id=state["current_part_id"]))
    result = procurement_agent.invoke({"messages": [prompt] + state["messages"]})
    
    data = extract_json(result['messages'][-1].content)
    
    return {
        "messages": [HumanMessage(content=f"Procurement Data Extracted: {data}", name="Procurement_Trigger")],
        "vendor_quote": data.get("vendor_quote", {})
    }

def capital_optimizer_node(state: AgentState):
    """
    The Deterministic Math Engine. 
    Processes state variables to calculate the absolute optimal fulfillment strategy without LLM hallucination.
    """
    qty_needed = state.get("quantity_needed", 0)
    
    # Safe fallback if there's no deficit
    if qty_needed == 0:
        return {"messages": [HumanMessage(content="No action required. Stock levels are healthy.", name="Capital_Optimizer")]}

    weight = state.get("part_weight_kg", 0.0)
    surplus_options = state.get("surplus_options", [])
    vendor = state.get("vendor_quote", {})
    
    vendor_cost_per_unit = vendor.get("purchase_cost_zar", 0.0)
    vendor_lead = vendor.get("lead_time_days", 0)

    # Sort surplus locations by cheapest freight rate
    surplus_options = sorted(surplus_options, key=lambda x: x.get("freight_rate", 99999.0))

    remaining_qty = qty_needed
    internal_transfer_cost = 0.0
    internal_units_moved = 0
    max_transit_days = 0
    transfer_details = []

    # 1. Evaluate Internal Network First
    for option in surplus_options:
        if remaining_qty <= 0: break
        
        available = option.get("surplus", 0)
        freight_rate = option.get("freight_rate", 0.0)
        
        if available <= 0: continue
        
        # Calculate logistics logic
        cost_per_unit_to_ship = weight * freight_rate
        
        # Financial Guardrail: If shipping is more expensive than buying new, DO NOT TRANSFER (Fixes CRSH-9011)
        if cost_per_unit_to_ship >= vendor_cost_per_unit:
            continue
            
        take_qty = min(available, remaining_qty)
        route_cost = take_qty * cost_per_unit_to_ship
        
        internal_transfer_cost += route_cost
        remaining_qty -= take_qty
        internal_units_moved += take_qty
        max_transit_days = max(max_transit_days, option.get("transit_days", 0))
        
        transfer_details.append(f"{take_qty} units from {option.get('site')}")

    # 2. Fulfill Remainder via External Procurement (Fixes FLT-8810 Hybrid Execution)
    new_procurement_cost = remaining_qty * vendor_cost_per_unit
    total_fulfillment_cost = internal_transfer_cost + new_procurement_cost
    
    # 3. Calculate Savings against Baseline (Buying all brand new)
    baseline_cost = qty_needed * vendor_cost_per_unit
    net_savings = baseline_cost - total_fulfillment_cost
    
    # 4. Calculate Timeline Acceleration
    days_accelerated = 0
    if internal_units_moved > 0:
        days_accelerated = max(0, vendor_lead - max_transit_days)

    # 5. Build the Math Payload
    execution_type = "Purchase Requisition"
    if internal_units_moved == qty_needed:
        execution_type = "Internal Transfer Order"
    elif internal_units_moved > 0 and remaining_qty > 0:
        execution_type = "Hybrid Execution (Transfer + Purchase)"

    payload = {
        "Recommended Action": execution_type,
        "Deficit Location": state.get("deficit_site", "Unknown"),
        "Quantity Needed": qty_needed,
        "Transfers": ", ".join(transfer_details) if transfer_details else "None",
        "Purchases": f"{remaining_qty} units from {vendor.get('vendor_name')}" if remaining_qty > 0 else "None",
        "Internal Transfer Cost": f"R {internal_transfer_cost:,.2f}",
        "New Procurement Cost": f"R {new_procurement_cost:,.2f}",
        "Net Savings": f"R {net_savings:,.2f}",
        "Days Accelerated": f"{days_accelerated} Days"
    }

    # 6. Hand payload to the LLM Synthesizer for formatting
    system_msg = SystemMessage(content=CAPITAL_OPTIMIZER_PROMPT)
    human_msg = HumanMessage(content=f"Math Engine Output:\n{json.dumps(payload, indent=2)}")
    
    response = llm.invoke([system_msg, human_msg])
    return {"messages": [response]}