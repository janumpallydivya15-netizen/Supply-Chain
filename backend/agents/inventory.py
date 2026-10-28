"""
Agent 3: Inventory Agent
Calculates stock deficits, safety stock breaches, replenishment quantities,
and estimates days of inventory remaining based on daily burn rate.
"""

from typing import Dict, Any


def run_inventory_analysis(shipment: Dict[str, Any], inventory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform deep inventory shortage calculation and evaluate the impact of shipment delays.
    """
    if not inventory:
        return {
            "agent": "Inventory Agent",
            "has_inventory_data": False,
            "notes": "No specific local warehouse record found for this product SKU."
        }

    available = inventory.get("available_stock", 0)
    reorder_threshold = inventory.get("reorder_threshold", 0)
    target_stock = inventory.get("target_stock", reorder_threshold * 1.3)
    burn_rate = inventory.get("daily_burn_rate", 10)
    unit = inventory.get("unit", "units")
    shipment_qty = shipment.get("quantity", 0)
    delay_days = shipment.get("delay_days", 0)

    # Shortage to threshold vs shortage to target
    shortage_to_threshold = max(0, reorder_threshold - available)
    shortage_to_target = max(0, int(target_stock - available))

    # Days of buffer stock remaining
    days_of_stock_left = round(available / burn_rate, 1) if burn_rate > 0 else 999.0

    # Stockout risk evaluation
    stockout_in_hours = int(days_of_stock_left * 24)
    will_stockout_before_arrival = days_of_stock_left < delay_days

    urgency = "Standard"
    if available < reorder_threshold * 0.3 or days_of_stock_left <= 2.0:
        urgency = "Immediate / Critical"
    elif available < reorder_threshold:
        urgency = "High Priority"

    return {
        "agent": "Inventory Agent",
        "has_inventory_data": True,
        "product_name": inventory.get("product_name"),
        "sku": inventory.get("sku"),
        "warehouse_location": inventory.get("location"),
        "current_stock": available,
        "reorder_threshold": reorder_threshold,
        "target_stock": target_stock,
        "daily_burn_rate": burn_rate,
        "unit": unit,
        "shortage_to_threshold": shortage_to_threshold,
        "quantity_needed_for_target": shortage_to_target,
        "days_of_stock_remaining": days_of_stock_left,
        "estimated_hours_to_stockout": stockout_in_hours,
        "delay_days_faced": delay_days,
        "will_stockout_before_arrival": will_stockout_before_arrival,
        "urgency_level": urgency,
        "impact_explanation": (
            f"Current stock of {available} {unit} depletes at ~{burn_rate} {unit}/day "
            f"({days_of_stock_left} days remaining). Delayed arrival (+{delay_days} days) "
            f"{'will cause an unavoidable stockout' if will_stockout_before_arrival else 'tightens safety buffer'}."
        )
    }
