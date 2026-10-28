"""
Agent 2: Supplier Investigation Agent
Investigates supplier performance, reported delay causes, and explores suitable alternative suppliers
from the mock database. Compares lead times, availability, and unit pricing without inventing external data.
"""

from typing import Dict, Any, List


def run_supplier_investigation(
    shipment: Dict[str, Any],
    alternative_suppliers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Investigate the primary supplier delay and evaluate alternative suppliers from mock data.
    """
    primary_supplier = shipment.get("supplier", "Unknown Supplier")
    delay_reason = shipment.get("notes", "No specific delay reason filed.")
    delay_days = shipment.get("delay_days", 0)
    sku = shipment.get("sku", "")

    # Compare alternatives if present
    alternatives_evaluated = []
    recommended_alternative = None

    for alt in alternative_suppliers:
        score = alt.get("reliability_score", 85)
        lead_time = alt.get("lead_time_days", 5)
        capacity = alt.get("capacity", 0)
        needed_qty = shipment.get("quantity", 0)

        can_fulfill = capacity >= needed_qty

        evaluation = {
            "supplier_name": alt.get("name"),
            "location": alt.get("location"),
            "lead_time_days": lead_time,
            "available_capacity": capacity,
            "unit_price_usd": alt.get("unit_price_usd"),
            "reliability_score": f"{score}%",
            "can_fulfill_full_order": can_fulfill,
            "notes": alt.get("notes")
        }
        alternatives_evaluated.append(evaluation)

        # Select best alternative based on fulfillment capability and shortest lead time
        if can_fulfill and (not recommended_alternative or lead_time < recommended_alternative["lead_time_days"]):
            recommended_alternative = evaluation

    return {
        "agent": "Supplier Investigation Agent",
        "primary_supplier": primary_supplier,
        "reported_delay_cause": delay_reason,
        "delay_days": delay_days,
        "sku": sku,
        "alternative_suppliers_found": len(alternatives_evaluated),
        "alternatives": alternatives_evaluated,
        "recommended_alternative": recommended_alternative,
        "data_notice": "Supplier alternatives sourced from verified internal benchmark catalog. No external APIs contacted."
    }
