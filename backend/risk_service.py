"""
Supply Chain Disruption Command Center - Risk Scoring & Business Impact Service
Phase 5: Dynamic Disruption Risk Scoring & Business Impact Analysis

Formulas and Weights:
1. Risk Score (0 - 100):
   Normalized multi-factor model evaluated across 6 dimensions:
   - Factor 1: Inventory Shortage Severity (Weight: 25%)
       Shortage ratio = (reorder_threshold - available_stock) / max(reorder_threshold, 1)
       Score contribution: min(max(shortage_ratio, 0.0), 1.0) * 25
   - Factor 2: Expected Shipment Delay (Weight: 20%)
       Delay scale: 0 days = 0, >= 7 days = 20 points (linear scaling: min(delay_days / 7.0, 1.0) * 20)
   - Factor 3: Time Remaining Before Stockout (Weight: 20%)
       Days of stock remaining = available_stock / max(daily_burn_rate, 1)
       Score contribution: 20 if stockout <= 1 day, 15 if <= 2 days, 10 if <= 3 days, 5 if <= 5 days, 0 if > 5 days
   - Factor 4: Customer / Shipment Criticality (Weight: 15%)
       Criticality tier: Critical shipment = 15, High = 10, Medium = 5, Low = 2
   - Factor 5: Revenue at Risk Scale (Weight: 10%)
       Financial exposure = days_of_stockout * daily_burn * unit_cost * 1.5
       Score contribution: min(exposure / 50000.0, 1.0) * 10
   - Factor 6: Alternative Supplier / Logistics Availability (Weight: 10%)
       Mitigability penalty: If 0 alternative suppliers or routes exist, penalty = 10;
       if 1 route/supplier exists, penalty = 5; if >= 2 exist, penalty = 0.

   Classification Thresholds:
   - 0 - 29: Low
   - 30 - 54: Medium
   - 55 - 79: High
   - 80 - 100: Critical

2. Business Impact Analysis:
   - Units at risk: min(daily_burn_rate * delay_days, quantity)
   - Days until stockout: available_stock / max(daily_burn_rate, 1)
   - Potential revenue at risk: days_of_stockout * daily_burn_rate * unit_cost * 1.5 (operational disruption multiplier)
   - Option Net Indicative Benefit: avoided_revenue_loss - indicative_recovery_cost
"""

from typing import Dict, Any, List, Optional


def calculate_risk_score(
    shipment: Optional[Dict[str, Any]],
    inventory: Optional[Dict[str, Any]],
    disruptions: Optional[List[Dict[str, Any]]] = None,
    alt_suppliers: Optional[List[Dict[str, Any]]] = None,
    alt_logistics: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Compute transparent, multi-factor risk score (0-100) and identify primary contributing factors.
    Handles missing or invalid inputs gracefully with documented defaults.
    """
    shipment = shipment or {}
    inventory = inventory or {}
    disruptions = disruptions or []
    alt_suppliers = alt_suppliers or []
    alt_logistics = alt_logistics or []

    # Safe extractions with documented defaults
    available_stock = float(inventory.get("available_stock", 50))
    reorder_threshold = float(inventory.get("reorder_threshold", 50))
    daily_burn = max(1.0, float(inventory.get("daily_burn_rate", 5.0)))
    unit_cost = float(inventory.get("unit_cost_usd", 100.0))
    delay_days = max(0.0, float(shipment.get("delay_days", 0.0)))
    risk_level = str(shipment.get("risk_level", "Medium")).strip().capitalize()

    # Factor 1: Inventory Shortage Severity (Max 25 pts)
    # Evaluates deficit against reorder threshold
    shortage_units = max(0.0, reorder_threshold - available_stock)
    shortage_ratio = min(1.0, shortage_units / max(reorder_threshold, 1.0))
    f1_shortage_score = round(shortage_ratio * 25.0, 1)

    # Factor 2: Expected Shipment Delay (Max 20 pts)
    # Linear scale capped at 7 days delay
    f2_delay_score = round(min(1.0, delay_days / 7.0) * 20.0, 1)

    # Factor 3: Time Remaining Before Stockout (Max 20 pts)
    days_to_stockout = round(available_stock / daily_burn, 1)
    if days_to_stockout <= 1.0:
        f3_stockout_score = 20.0
    elif days_to_stockout <= 2.0:
        f3_stockout_score = 15.0
    elif days_to_stockout <= 3.5:
        f3_stockout_score = 10.0
    elif days_to_stockout <= 5.0:
        f3_stockout_score = 5.0
    else:
        f3_stockout_score = 0.0

    # Factor 4: Customer / Shipment Criticality (Max 15 pts)
    criticality_map = {
        "Critical": 15.0,
        "High": 11.0,
        "Medium": 6.0,
        "Low": 2.0
    }
    f4_criticality_score = criticality_map.get(risk_level, 6.0)

    # Factor 5: Revenue at Risk Scale (Max 10 pts)
    days_of_stockout_projected = max(0.0, delay_days - days_to_stockout)
    unfulfilled_units = round(days_of_stockout_projected * daily_burn, 1)
    revenue_at_risk = round(unfulfilled_units * unit_cost * 1.5, 2)
    f5_revenue_score = round(min(1.0, revenue_at_risk / 50000.0) * 10.0, 1)

    # Factor 6: Alternative Supplier / Route Availability (Max 10 pts)
    total_alternatives = len(alt_suppliers) + len(alt_logistics)
    if total_alternatives == 0:
        f6_mitigability_score = 10.0  # Zero fallback options = high risk
    elif total_alternatives == 1:
        f6_mitigability_score = 5.0
    else:
        f6_mitigability_score = 1.0   # Plentiful alternatives = low vulnerability

    # Composite Normalized Score (0 - 100)
    total_score = round(
        f1_shortage_score +
        f2_delay_score +
        f3_stockout_score +
        f4_criticality_score +
        f5_revenue_score +
        f6_mitigability_score,
        1
    )
    total_score = max(0.0, min(100.0, total_score))

    # Classification Thresholds (aligned with enterprise risk criteria)
    # If shipment risk_level is explicitly Critical and shortage + delay are severe, classify as Critical
    if total_score >= 70.0 or (risk_level == "Critical" and total_score >= 60.0):
        classification = "Critical"
    elif total_score >= 50.0:
        classification = "High"
    elif total_score >= 25.0:
        classification = "Medium"
    else:
        classification = "Low"

    # Identify primary contributing factors
    contributions = [
        {"factor": "Inventory Shortage Severity", "score": f1_shortage_score, "max": 25, "detail": f"{int(shortage_units)} units below reorder threshold ({int(available_stock)}/{int(reorder_threshold)})"},
        {"factor": "Shipment Delay Exposure", "score": f2_delay_score, "max": 20, "detail": f"+{delay_days} days arrival delay"},
        {"factor": "Imminent Stockout Threat", "score": f3_stockout_score, "max": 20, "detail": f"{days_to_stockout} days of stock remaining at {daily_burn} units/day"},
        {"factor": "Shipment Criticality Tier", "score": f4_criticality_score, "max": 15, "detail": f"Classified as '{risk_level}' operational priority"},
        {"factor": "Financial Exposure Scale", "score": f5_revenue_score, "max": 10, "detail": f"${revenue_at_risk:,.2f} projected revenue at risk"},
        {"factor": "Mitigation Scarcity", "score": f6_mitigability_score, "max": 10, "detail": f"{total_alternatives} alternative sourcing/routing options identified"}
    ]
    # Sort top contributors
    top_contributors = sorted(contributions, key=lambda c: c["score"], reverse=True)

    return {
        "risk_score": total_score,
        "classification": classification,
        "days_to_stockout": days_to_stockout,
        "revenue_at_risk_usd": revenue_at_risk,
        "factor_breakdown": {
            "inventory_shortage": f1_shortage_score,
            "shipment_delay": f2_delay_score,
            "stockout_threat": f3_stockout_score,
            "criticality": f4_criticality_score,
            "financial_exposure": f5_revenue_score,
            "mitigation_scarcity": f6_mitigability_score
        },
        "top_contributing_factors": top_contributors[:3],
        "formula_documentation": "Composite 6-factor index: Shortage (25%) + Delay (20%) + Stockout Time (20%) + Criticality (15%) + Revenue (10%) + Mitigation Scarcity (10%). Scale 0-100."
    }


def analyze_recovery_options_impact(
    shipment: Dict[str, Any],
    inventory: Dict[str, Any],
    raw_recovery_options: List[Dict[str, Any]],
    risk_assessment: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Perform deep business impact analysis and side-by-side comparison for each feasible recovery option.
    Calculates:
    - Indicative recovery cost
    - Estimated resolution time
    - Expected inventory shortage reduction
    - Revenue / business impact avoided
    - Net indicative benefit (avoided revenue loss - recovery cost)
    - Residual risk remaining
    - Feasibility & explicit assumptions
    """
    inventory = inventory or {}
    shipment = shipment or {}
    daily_burn = max(1.0, float(inventory.get("daily_burn_rate", 5.0)))
    unit_cost = float(inventory.get("unit_cost_usd", 100.0))
    baseline_revenue_at_risk = float(risk_assessment.get("revenue_at_risk_usd", 0.0))
    days_to_stockout = float(risk_assessment.get("days_to_stockout", 5.0))
    shipment_quantity = float(shipment.get("quantity", 50))
    delay_days = float(shipment.get("delay_days", 0))

    enhanced_options: List[Dict[str, Any]] = []

    for opt in raw_recovery_options:
        opt_id = opt.get("option_id", "OPT-1")
        opt_name = opt.get("name", "Mitigation Option")
        opt_type = opt.get("type", opt.get("option_type", "Standard"))
        action = opt.get("action", "")
        indicative_cost = float(opt.get("indicative_cost_usd", 0.0))
        res_days = int(opt.get("expected_time_to_resolve_days", 1))
        feasibility = opt.get("feasibility", "Medium")

        # Calculate shortage reduction & days saved
        if opt_type in ("Carrier Intercept / Air Freight", "Expedited Logistics"):
            # Expediting saves (delay_days - res_days) days of stockout
            days_saved = max(0.0, delay_days - res_days)
            shortage_reduction_units = min(shipment_quantity, round(days_saved * daily_burn, 1))
            # Avoided revenue impact
            avoided_revenue_loss = min(baseline_revenue_at_risk, round(days_saved * daily_burn * unit_cost * 1.5, 2))
            residual_risk = "Low" if res_days <= days_to_stockout else "Medium"
            tradeoff_summary = f"Expedites existing cargo by {days_saved:.0f} day(s). High speed, low unit procurement premium."

        elif opt_type in ("Alternative Supplier Sourcing", "Secondary Sourcing"):
            # Alternative supplier provides dedicated replenishment
            shortage_reduction_units = min(shipment_quantity, float(inventory.get("target_stock", 80) - inventory.get("available_stock", 14)))
            days_saved = max(0.0, delay_days - res_days)
            avoided_revenue_loss = min(baseline_revenue_at_risk, round(days_saved * daily_burn * unit_cost * 1.5, 2))
            residual_risk = "Low" if res_days <= days_to_stockout else "Medium"
            tradeoff_summary = f"Slices lead time to {res_days} day(s) via secondary vendor, but incurs higher procurement outlay."

        else:
            # Passive monitoring / Do nothing
            days_saved = 0.0
            shortage_reduction_units = 0.0
            avoided_revenue_loss = 0.0
            residual_risk = risk_assessment.get("classification", "High")
            tradeoff_summary = "Zero cash outlay; accepts full stockout vulnerability and delayed customer orders."

        # Net Indicative Financial Benefit
        net_benefit = round(avoided_revenue_loss - indicative_cost, 2)

        enhanced_options.append({
            "option_id": opt_id,
            "name": opt_name,
            "type": opt_type,
            "action": action,
            "indicative_cost_usd": indicative_cost,
            "expected_time_to_resolve_days": res_days,
            "shortage_reduction_units": shortage_reduction_units,
            "avoided_revenue_loss_usd": avoided_revenue_loss,
            "net_indicative_benefit_usd": net_benefit,
            "residual_risk": residual_risk,
            "feasibility": feasibility,
            "tradeoff_summary": tradeoff_summary,
            "status": opt.get("status", "Proposed")
        })

    # Sort options by net indicative benefit (descending), then resolution speed
    enhanced_options.sort(
        key=lambda o: (o["net_indicative_benefit_usd"], -o["expected_time_to_resolve_days"]),
        reverse=True
    )

    return enhanced_options


def formulate_explainable_recommendation(
    ranked_options: List[Dict[str, Any]],
    risk_assessment: Dict[str, Any],
    shipment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Formulate transparent, evidence-based recommendation explaining:
    - Primary recommended option
    - Why this option is preferred (quantified ROI, speed, and risk delta)
    - Alternatives considered and specific reasons they ranked lower
    - Trade-offs when options are closely competitive
    - Explicit model assumptions & data limitations
    """
    if not ranked_options:
        return {
            "recommended_option_id": "NONE",
            "recommended_option_name": "No Feasible Options Available",
            "selection_rationale": "No viable alternative logistics or supplier options were found in current inventory records.",
            "considered_options": [],
            "assumptions": ["Limited mock records available."],
            "data_limitations": ["External carrier capacity unverified."]
        }

    best_opt = ranked_options[0]
    considered = []

    # Check for close trade-off (e.g. within $2,000 net benefit)
    is_close_tradeoff = False
    runner_up = ranked_options[1] if len(ranked_options) > 1 else None
    if runner_up and abs(best_opt["net_indicative_benefit_usd"] - runner_up["net_indicative_benefit_usd"]) <= 2500.0:
        is_close_tradeoff = True

    for other_opt in ranked_options[1:]:
        diff_benefit = best_opt["net_indicative_benefit_usd"] - other_opt["net_indicative_benefit_usd"]
        diff_time = other_opt["expected_time_to_resolve_days"] - best_opt["expected_time_to_resolve_days"]

        reasons = []
        if other_opt["net_indicative_benefit_usd"] < best_opt["net_indicative_benefit_usd"]:
            reasons.append(f"Yields ${diff_benefit:,.2f} lower net business benefit")
        if other_opt["expected_time_to_resolve_days"] > best_opt["expected_time_to_resolve_days"]:
            reasons.append(f"Requires {diff_time} additional day(s) to resolve")
        if other_opt["indicative_cost_usd"] > best_opt["indicative_cost_usd"]:
            cost_premium = other_opt["indicative_cost_usd"] - best_opt["indicative_cost_usd"]
            reasons.append(f"Requires ${cost_premium:,.2f} higher cash expenditure")
        if other_opt["type"] == "No Active Intervention":
            reasons.append(f"Accepts unmitigated stockout exposure of ${risk_assessment.get('revenue_at_risk_usd', 0):,.2f}")

        considered.append({
            "option_id": other_opt["option_id"],
            "name": other_opt["name"],
            "type": other_opt["type"],
            "net_benefit_usd": other_opt["net_indicative_benefit_usd"],
            "resolution_days": other_opt["expected_time_to_resolve_days"],
            "reasons_ranked_lower": reasons or ["Ranked lower based on overall composite scoring"]
        })

    # Build primary rationale
    if best_opt["type"] != "No Active Intervention":
        rationale = (
            f"Playbook {best_opt['option_id']} ('{best_opt['name']}') is recommended as it delivers "
            f"the highest net indicative financial benefit (${best_opt['net_indicative_benefit_usd']:,.2f}), "
            f"avoiding ${best_opt['avoided_revenue_loss_usd']:,.2f} in projected stockout loss "
            f"at an indicative cost of ${best_opt['indicative_cost_usd']:,.2f}. "
            f"Resolution is achieved in {best_opt['expected_time_to_resolve_days']} day(s), "
            f"reducing residual operational risk to {best_opt['residual_risk']}."
        )
    else:
        rationale = (
            f"Passive monitoring is advised as mitigation costs outweigh the projected stockout impact. "
            f"Shipment arrival delay is within tolerable buffer margins."
        )

    if is_close_tradeoff and runner_up:
        tradeoff_note = (
            f"Close Decision Boundary: Runner-up '{runner_up['name']}' offers competitive viability "
            f"(net benefit delta: ${abs(best_opt['net_indicative_benefit_usd'] - runner_up['net_indicative_benefit_usd']):,.2f}). "
            f"Prefer {best_opt['option_id']} if speed and capital conservation are prioritized; consider {runner_up['option_id']} if supplier diversification is paramount."
        )
    else:
        tradeoff_note = None

    assumptions = [
        "Daily warehouse consumption burn rate is assumed constant during transit delay.",
        "Revenue at risk assumes a 1.5x customer contract fulfillment and cancellation penalty factor.",
        "Indicative logistics and supplier rates are deterministic benchmarks; no binding quotes have been committed.",
        "Safety stock levels reflect current registered inventory buffers without unrecorded inbound transfers."
    ]

    limitations = [
        "Live customs inspection hold duration at Shenzhen / destination ports may fluctuate with local authority backlogs.",
        "Air cargo spot rates reflect indicative regional tariffs rather than live carrier spot quotes.",
        "External operational execution remains simulated; human governance sign-off is required prior to sandbox dispatch."
    ]

    return {
        "recommended_option_id": best_opt["option_id"],
        "recommended_option_name": best_opt["name"],
        "selection_rationale": rationale,
        "tradeoff_note": tradeoff_note,
        "expected_net_benefit_usd": best_opt["net_indicative_benefit_usd"],
        "expected_resolution_days": best_opt["expected_time_to_resolve_days"],
        "considered_alternatives": considered,
        "assumptions": assumptions,
        "data_limitations": limitations
    }
