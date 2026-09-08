import sqlite3
import pandas as pd
from pathlib import Path
from langchain_core.tools import tool

# Dynamically locate the Use Case 9.1 database
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "processed" / "uc9_supply_chain.sqlite"

def execute_query(query: str, params: tuple = ()) -> pd.DataFrame:
    """Helper function to execute SQL queries safely with parameters."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

@tool
def get_network_inventory(part_id: str) -> str:
    """
    Fetches stock levels and calculates exact Surplus/Deficit (Variance) for all locations.
    A negative variance means a DEFICIT (stockout). A positive variance means a SURPLUS.
    """
    # We calculate the variance directly in SQL to prevent AI math errors
    query = """
    SELECT 
        location, 
        stock_on_hand, 
        min_threshold, 
        (stock_on_hand - min_threshold) AS variance, 
        weight_kg 
    FROM inventory_ledger 
    WHERE part_id = ?
    """
    df = execute_query(query, (part_id,))
    
    if df.empty:
        return f"No inventory records found for Part ID: {part_id}"
    if "error" in df.columns:
        return f"Database error: {df['error'].iloc[0]}"
        
    return df.to_string(index=False)

@tool
def get_logistics_routes(target_site: str) -> str:
    """
    Finds the transit days and freight rate per kg to move materials TO the specified target_site.
    """
    query = "SELECT source_site, transit_days, freight_rate_per_kg_zar FROM logistics_network WHERE target_site = ?"
    df = execute_query(query, (target_site,))
    
    if df.empty:
        return f"No logistics routes found targeting {target_site}."
    if "error" in df.columns:
        return f"Database error: {df['error'].iloc[0]}"
        
    return df.to_string(index=False)

@tool
def get_vendor_quotes(part_id: str) -> str:
    """
    Fetches external supplier quotes (lead time and purchase cost) for a specific part.
    """
    query = "SELECT vendor_name, lead_time_days, purchase_cost_zar FROM supplier_quotes WHERE part_id = ?"
    df = execute_query(query, (part_id,))
    
    if df.empty:
        return f"No external supplier quotes found for Part ID: {part_id}"
    if "error" in df.columns:
        return f"Database error: {df['error'].iloc[0]}"
        
    return df.to_string(index=False)