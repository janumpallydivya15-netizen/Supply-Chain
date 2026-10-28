"""
Agent 1: Disruption Detection Agent
Analyzes shipment status, expected arrival dates, delay days, and inventory status.
Assigns severity levels (Critical, High, Medium, Low) and outputs structured findings.
"""

from typing import Dict, Any


def run_disruption_detector(shipment: Dict[str, Any], inventory: Dict[str, Any], disruptions: list) -> Dict[str, Any]:
    """
    Execute disruption detection analysis on the target shipment and associated inventory.
    """
    shipment_id = shipment.get("id", "UNKNOWN")
    delay_days = shipment.get("delay_days", 0)
    status = shipment.get("status", "Unknown")
    product = shipment.get("product", "Unknown Item")
    current_stock = inventory.get("available_stock", 0) if inventory else 0
    reorder_threshold = inventory.get("reorder_threshold", 0) if inventory else 0

    detected_issues = []
    severity = "Low"

    # Evaluate shipment delay
    if status == "Delayed" or delay_days > 0:
        detected_issues.append({
            "type": "Shipment Delay",
            "detail": f"Shipment {shipment_id} is delayed by {delay_days} days (Status: {status}).",
            "origin": shipment.get("origin"),
            "destination": shipment.get("destination")
        })

    # Evaluate inventory status
    if inventory:
        if current_stock < reorder_threshold:
            shortage_qty = reorder_threshold - current_stock
            severity = "Critical" if current_stock < (reorder_threshold * 0.3) else "High"
            detected_issues.append({
                "type": "Inventory Deficit",
                "detail": f"Inventory level ({current_stock} units) is below reorder threshold ({reorder_threshold} units). Shortage: {shortage_qty} units.",
                "facility": inventory.get("location")
            })
        elif current_stock == reorder_threshold:
            severity = "Medium"
            detected_issues.append({
                "type": "Inventory At Threshold",
                "detail": f"Inventory is exactly at reorder threshold ({reorder_threshold} units)."
            })

    # Integrate explicit disruption records
    for d in disruptions:
        detected_issues.append({
            "type": d.get("type", "Operational Alert"),
            "id": d.get("id"),
            "detail": d.get("description"),
            "severity_reported": d.get("severity")
        })
        # Elevate severity if recorded disruption is Critical or High
        if d.get("severity") == "Critical":
            severity = "Critical"
        elif d.get("severity") == "High" and severity != "Critical":
            severity = "High"

    # Fallback severity assignment for in-transit on-schedule shipments
    if not detected_issues and status in ("In Transit", "Delivered"):
        severity = "Low"

    return {
        "agent": "Disruption Detection Agent",
        "severity": severity,
        "is_disrupted": len(detected_issues) > 0 or status == "Delayed",
        "primary_product": product,
        "shipment_status": status,
        "delay_days": delay_days,
        "detected_issues": detected_issues,
        "summary": f"Detected {len(detected_issues)} operational concern(s) for {shipment_id} with overall severity '{severity}'."
    }
