"""
Agent 5: Impact Analysis Agent
Synthesizes findings across supplier delays, inventory depletion, and logistics options
to project operational revenue at risk, potential downtime, dynamic risk scoring,
and comprehensive business impact comparisons between recovery playbooks.
Explicitly highlights all assumptions and distinguishes estimates from audited losses.
"""

from typing import Dict, Any, List
from backend.risk_service import (
    calculate_risk_score,
    analyze_recovery_options_impact,
    formulate_explainable_recommendation
)


def run_impact_analysis(
    shipment: Dict[str, Any],
    inventory: Dict[str, Any],
    supplier_findings: Dict[str, Any],
    inventory_findings: Dict[str, Any],
    logistics_findings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Formulate operational impact projections and generate comparative recovery options.
    Phase 5 enhanced with dynamic risk scoring, option comparison, and explainable recommendations.
    """
    quantity = shipment.get("quantity", 0)
    delay_days = shipment.get("delay_days", 0)
    product = shipment.get("product", "General Inventory")

    unit_cost = inventory.get("unit_cost_usd", 100) if inventory else 100
    daily_burn = inventory.get("daily_burn_rate", 10) if inventory else 10
    days_stock = inventory_findings.get("days_of_stock_remaining", 5.0)

    # Indicative batch value calculation
    batch_value_usd = round(quantity * unit_cost, 2)

    # Dynamic multi-factor risk scoring
    alt_suppliers = supplier_findings.get("all_alternatives", [])
    alt_logistics = logistics_findings.get("available_routes", [])
    risk_assessment = calculate_risk_score(
        shipment=shipment,
        inventory=inventory,
        alt_suppliers=alt_suppliers,
        alt_logistics=alt_logistics
    )

    # Formulate Feasible Raw Recovery Options
    raw_recovery_options: List[Dict[str, Any]] = []

    # Option A: Expedited Logistics on existing shipment
    rec_route = logistics_findings.get("recommended_route")
    if rec_route:
        raw_recovery_options.append({
            "option_id": "OPT-1",
            "name": f"Expedited Logistics via {rec_route['carrier']}",
            "type": "Carrier Intercept / Air Freight",
            "action": f"Upgrade in-transit or port cargo to {rec_route['transport_mode']}.",
            "indicative_cost_usd": rec_route["indicative_cost_usd"],
            "expected_time_to_resolve_days": rec_route["transit_days"],
            "risk_mitigation": "Prevents warehouse stockout before buffer depletes.",
            "feasibility": rec_route["feasibility"]
        })

    # Option B: Alternative Supplier Sourcing
    rec_supplier = supplier_findings.get("recommended_alternative")
    if rec_supplier:
        qty_needed = inventory_findings.get("quantity_needed_for_target", quantity)
        est_procurement_cost = round(qty_needed * rec_supplier["unit_price_usd"], 2)
        raw_recovery_options.append({
            "option_id": "OPT-2",
            "name": f"Emergency PO with {rec_supplier['supplier_name']}",
            "type": "Alternative Supplier Sourcing",
            "action": f"Issue purchase order for {qty_needed} units from {rec_supplier['location']}.",
            "indicative_cost_usd": est_procurement_cost,
            "expected_time_to_resolve_days": rec_supplier["lead_time_days"],
            "risk_mitigation": "Diversifies supplier base and secures domestic backup delivery.",
            "feasibility": "High" if rec_supplier["can_fulfill_full_order"] else "Medium"
        })

    # Option C: Baseline / Do Nothing (Wait for Delayed Shipment)
    raw_recovery_options.append({
        "option_id": "OPT-3",
        "name": "Passive Monitoring (Wait for Original Delivery)",
        "type": "No Active Intervention",
        "action": f"Allow shipment {shipment.get('id')} to clear standard channels without expediting.",
        "indicative_cost_usd": 0,
        "expected_time_to_resolve_days": delay_days,
        "risk_mitigation": "Zero operational cash outlay, but accepts stockout risk and delayed order fulfillments.",
        "feasibility": "High"
    })

    # Deep business impact analysis & side-by-side comparison
    ranked_options = analyze_recovery_options_impact(
        shipment=shipment,
        inventory=inventory,
        raw_recovery_options=raw_recovery_options,
        risk_assessment=risk_assessment
    )

    # Explainable recommendation formulation
    rec_intelligence = formulate_explainable_recommendation(
        ranked_options=ranked_options,
        risk_assessment=risk_assessment,
        shipment=shipment
    )

    recommended_plan = rec_intelligence["recommended_option_name"]

    assumptions = rec_intelligence.get("assumptions", [
        f"Daily consumption rate is assumed constant at {daily_burn} units/day.",
        f"Indicative product inventory cost baseline is ${unit_cost:,.2f}/unit.",
        "Revenue at risk models customer order cancellation penalties and fulfillment delays.",
        "Carrier expediting fees and supplier lead times reflect deterministic benchmark figures.",
        "All recovery estimates are indicative simulation projections and not audited financial commitments."
    ])

    return {
        "agent": "Impact Analysis Agent",
        "batch_value_usd": batch_value_usd,
        "estimated_days_of_stockout": risk_assessment.get("days_to_stockout", 0.0),
        "revenue_at_risk_usd": risk_assessment.get("revenue_at_risk_usd", 0.0),
        "risk_assessment": risk_assessment,
        "recovery_options": ranked_options,
        "recommended_plan": recommended_plan,
        "recommendation_intelligence": rec_intelligence,
        "assumptions": assumptions,
        "notes": rec_intelligence.get("selection_rationale", "")
    }
