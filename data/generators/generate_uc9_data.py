import sqlite3
import pandas as pd
from pathlib import Path
import os

# Dynamically calculate the Project Root Directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "uc9_supply_chain.sqlite"

def setup_directories():
    """Ensures target directories exist and removes old databases."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        os.remove(DB_PATH)

def generate_database():
    print(f"Generating Multi-Warehouse SQLite Database at: {DB_PATH}")
    
    # --- 1. INVENTORY LEDGER ---
    # Includes weight constraints to force the Capital Optimizer to calculate true freight costs.
    inventory_data = [
        # SCENARIO 1: HYD-2005 (Ideal Transfer Wins)
        {"part_id": "HYD-2005", "description": "High-Pressure Hydraulic Pump", "location": "Kolomela", "stock_on_hand": 0, "min_threshold": 5, "unit_cost_zar": 24500.0, "weight_kg": 45.0},
        {"part_id": "HYD-2005", "description": "High-Pressure Hydraulic Pump", "location": "Sishen", "stock_on_hand": 8, "min_threshold": 5, "unit_cost_zar": 24500.0, "weight_kg": 45.0}, # 3 Excess
        
        # SCENARIO 2: CRSH-9011 (External Procurement Wins due to massive weight)
        {"part_id": "CRSH-9011", "description": "Crusher Liner Segment", "location": "Saldanha", "stock_on_hand": 0, "min_threshold": 2, "unit_cost_zar": 35000.0, "weight_kg": 1200.0},
        {"part_id": "CRSH-9011", "description": "Crusher Liner Segment", "location": "Central WH", "stock_on_hand": 4, "min_threshold": 2, "unit_cost_zar": 35000.0, "weight_kg": 1200.0}, # 2 Excess
        
        # SCENARIO 3: SEN-4022 (Route Optimization - Multi-Site Surplus)
        {"part_id": "SEN-4022", "description": "Conveyor Speed Sensor", "location": "Thabazimbi", "stock_on_hand": 0, "min_threshold": 10, "unit_cost_zar": 4200.0, "weight_kg": 2.0},
        {"part_id": "SEN-4022", "description": "Conveyor Speed Sensor", "location": "Sishen", "stock_on_hand": 13, "min_threshold": 10, "unit_cost_zar": 4200.0, "weight_kg": 2.0}, # 3 Excess
        {"part_id": "SEN-4022", "description": "Conveyor Speed Sensor", "location": "Kolomela", "stock_on_hand": 15, "min_threshold": 10, "unit_cost_zar": 4200.0, "weight_kg": 2.0}, # 5 Excess
        
        # SCENARIO 4: FLT-8810 (Hybrid: Partial Transfer + Split PO)
        {"part_id": "FLT-8810", "description": "Heavy Fuel Filter Assembly", "location": "Sishen", "stock_on_hand": 0, "min_threshold": 10, "unit_cost_zar": 6500.0, "weight_kg": 12.0},
        {"part_id": "FLT-8810", "description": "Heavy Fuel Filter Assembly", "location": "Kolomela", "stock_on_hand": 14, "min_threshold": 10, "unit_cost_zar": 6500.0, "weight_kg": 12.0}, # 4 Excess
        
        # SCENARIO 5: VALV-102 (Healthy Baseline)
        {"part_id": "VALV-102", "description": "Flow Control Valve", "location": "Sishen", "stock_on_hand": 45, "min_threshold": 15, "unit_cost_zar": 800.0, "weight_kg": 5.0}
    ]
    
    # --- 2. LOGISTICS NETWORK ---
    # Maps geospatial transit times and per-kg freight tariffs between nodes.
    logistics_data = [
        {"source_site": "Sishen", "target_site": "Kolomela", "transit_days": 1, "freight_rate_per_kg_zar": 12.0},
        {"source_site": "Kolomela", "target_site": "Sishen", "transit_days": 1, "freight_rate_per_kg_zar": 12.0},
        {"source_site": "Sishen", "target_site": "Saldanha", "transit_days": 4, "freight_rate_per_kg_zar": 32.0},
        {"source_site": "Central WH", "target_site": "Saldanha", "transit_days": 3, "freight_rate_per_kg_zar": 28.0},
        {"source_site": "Sishen", "target_site": "Thabazimbi", "transit_days": 3, "freight_rate_per_kg_zar": 24.0},
        {"source_site": "Kolomela", "target_site": "Thabazimbi", "transit_days": 1, "freight_rate_per_kg_zar": 14.0} # Cheaper/Faster route for Scenario 3
    ]
    
    # --- 3. SUPPLIER QUOTES ---
    # Used by the Procurement Trigger to compare purchasing economics.
    supplier_data = [
        {"part_id": "HYD-2005", "vendor_name": "Hydraulics Int.", "lead_time_days": 18, "purchase_cost_zar": 24500.0},
        {"part_id": "CRSH-9011", "vendor_name": "Heavy Steel Co.", "lead_time_days": 10, "purchase_cost_zar": 35000.0},
        {"part_id": "SEN-4022", "vendor_name": "ElectroMining", "lead_time_days": 5, "purchase_cost_zar": 4200.0},
        {"part_id": "FLT-8810", "vendor_name": "FilterPro ZA", "lead_time_days": 7, "purchase_cost_zar": 6500.0},
        {"part_id": "VALV-102", "vendor_name": "Flow Systems", "lead_time_days": 4, "purchase_cost_zar": 800.0}
    ]

    # Save all to SQLite
    with sqlite3.connect(DB_PATH) as conn:
        pd.DataFrame(inventory_data).to_sql("inventory_ledger", conn, if_exists="replace", index=False)
        pd.DataFrame(logistics_data).to_sql("logistics_network", conn, if_exists="replace", index=False)
        pd.DataFrame(supplier_data).to_sql("supplier_quotes", conn, if_exists="replace", index=False)
        
    print("-> Multi-Warehouse database successfully populated.")

if __name__ == "__main__":
    setup_directories()
    generate_database()