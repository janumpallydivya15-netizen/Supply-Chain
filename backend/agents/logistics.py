"""
Agent 4: Logistics Agent
Evaluates current shipping routes, alternative logistics carriers, expedited shipping options,
indicative freight costs, and transit times using verified mock logistics benchmarks.
"""

from typing import Dict, Any, List


def run_logistics_analysis(
    shipment: Dict[str, Any],
    alternative_logistics: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluate available shipping routes, alternative carriers, and freight turnaround times.
    """
    shipment_id = shipment.get("id")
    origin = shipment.get("origin", "Origin Port")
    destination = shipment.get("destination", "Destination Hub")
    delay_days = shipment.get("delay_days", 0)

    options_evaluated = []
    recommended_route = None

    for opt in alternative_logistics:
        carrier = opt.get("carrier")
        mode = opt.get("mode")
        transit_days = opt.get("transit_days", 2)
        cost = opt.get("indicative_cost_usd", 0)
        feasibility = opt.get("feasibility", "Medium")

        route_info = {
            "carrier": carrier,
            "transport_mode": mode,
            "transit_days": transit_days,
            "indicative_cost_usd": cost,
            "feasibility": feasibility,
            "description": opt.get("description")
        }
        options_evaluated.append(route_info)

        # Select highest feasibility with fastest transit time
        if not recommended_route or (feasibility == "High" and transit_days < recommended_route["transit_days"]):
            recommended_route = route_info

    has_alternatives = len(options_evaluated) > 0

    return {
        "agent": "Logistics Agent",
        "shipment_id": shipment_id,
        "current_route": f"{origin} -> {destination}",
        "current_delay": f"+{delay_days} days",
        "has_alternative_routes": has_alternatives,
        "available_routes_count": len(options_evaluated),
        "route_options": options_evaluated,
        "recommended_route": recommended_route,
        "recommendation_summary": (
            f"Recommended {recommended_route['carrier']} ({recommended_route['transport_mode']}) - saves {max(0, delay_days - recommended_route['transit_days'])} days for ${recommended_route['indicative_cost_usd']}."
            if recommended_route else "No verified expedited carrier alternative recorded in benchmark dataset."
        ),
        "data_notice": "Carrier rates and transit schedules are simulated logistics benchmarks."
    }
