import argparse
import warnings
from src.graph.uc9_orchestrator import build_uc9_replenishment_system

# Suppress LangChain deprecation warnings for cleaner CLI output
warnings.filterwarnings("ignore", category=UserWarning, module="langgraph")

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Autonomous Replenishment System")
    parser.add_argument("--part", type=str, required=True, help="Part ID to investigate (e.g., HYD-2005)")
    args = parser.parse_args()

    print(f"\nInitializing Autonomous Replenishment System for Part: {args.part}...")
    
    # Build the compiled graph
    app = build_uc9_replenishment_system()
    
    # Initialize the strict AgentState
    initial_state = {
        "current_part_id": args.part,
        "messages": [],
        "active_alerts": [],
        "next_agent": "",
        "deficit_site": "None",
        "quantity_needed": -1,  # Set to -1 to ensure Supervisor doesn't short-circuit immediately
        "part_weight_kg": 0.0,
        "surplus_options": [],
        "vendor_quote": {}
    }
    
    print("\nExecuting Agentic Workflow...")
    print("=" * 60)
    
    final_state = None
    for s in app.stream(initial_state, config={"recursion_limit": 50}):
        node_name = list(s.keys())[0]
        print(f"-> Completed execution step: [{node_name}]")
        final_state = s
            
    print("=" * 60 + "\n")
    
    # Extract and display the final mathematically synthesized output
    if final_state and "Capital_Optimizer" in final_state:
        final_msg = final_state["Capital_Optimizer"]["messages"][-1].content
        print(final_msg)
    else:
        print("Error: Workflow did not reach the Capital Optimizer synthesis.")

if __name__ == "__main__":
    main()