"""
Multi-Agent Orchestrator using LangGraph.
Coordinates parallel execution of investigation agents (Supplier, Inventory, Logistics),
integrates disruption detection and impact analysis, and supports LLM narrative synthesis
with deterministic fallback.
"""

from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, START, END

from backend.config import get_llm_configuration, call_llm
from backend.agents.detector import run_disruption_detector
from backend.agents.supplier import run_supplier_investigation
from backend.agents.inventory import run_inventory_analysis
from backend.agents.logistics import run_logistics_analysis
from backend.agents.impact import run_impact_analysis


class OrchestratorState(TypedDict, total=False):
    # Inputs
    shipment: Dict[str, Any]
    inventory: Dict[str, Any]
    disruptions: list
    alternative_suppliers: list
    alternative_logistics: list

    # Agent findings
    detector_findings: Dict[str, Any]
    supplier_findings: Dict[str, Any]
    inventory_findings: Dict[str, Any]
    logistics_findings: Dict[str, Any]
    impact_findings: Dict[str, Any]

    # Synthesis & Execution Metadata
    executive_summary: str
    execution_mode: str
    llm_synthesis: Dict[str, Any]
    errors: list


# Node 1: Disruption Detection Node
def node_detect(state: OrchestratorState) -> Dict[str, Any]:
    try:
        findings = run_disruption_detector(
            state["shipment"],
            state.get("inventory") or {},
            state.get("disruptions") or []
        )
        return {"detector_findings": findings}
    except Exception as exc:
        return {
            "detector_findings": {"error": str(exc), "severity": "Medium"},
            "errors": [f"Detection Agent error: {str(exc)}"]
        }


# Node 2: Supplier Investigation Node
def node_supplier(state: OrchestratorState) -> Dict[str, Any]:
    try:
        findings = run_supplier_investigation(
            state["shipment"],
            state.get("alternative_suppliers") or []
        )
        return {"supplier_findings": findings}
    except Exception as exc:
        return {
            "supplier_findings": {"error": str(exc)},
            "errors": [f"Supplier Agent error: {str(exc)}"]
        }


# Node 3: Inventory Analysis Node
def node_inventory(state: OrchestratorState) -> Dict[str, Any]:
    try:
        findings = run_inventory_analysis(
            state["shipment"],
            state.get("inventory") or {}
        )
        return {"inventory_findings": findings}
    except Exception as exc:
        return {
            "inventory_findings": {"error": str(exc)},
            "errors": [f"Inventory Agent error: {str(exc)}"]
        }


# Node 4: Logistics Analysis Node
def node_logistics(state: OrchestratorState) -> Dict[str, Any]:
    try:
        findings = run_logistics_analysis(
            state["shipment"],
            state.get("alternative_logistics") or []
        )
        return {"logistics_findings": findings}
    except Exception as exc:
        return {
            "logistics_findings": {"error": str(exc)},
            "errors": [f"Logistics Agent error: {str(exc)}"]
        }


# Node 5: Impact Analysis Node
def node_impact(state: OrchestratorState) -> Dict[str, Any]:
    try:
        findings = run_impact_analysis(
            state["shipment"],
            state.get("inventory") or {},
            state.get("supplier_findings") or {},
            state.get("inventory_findings") or {},
            state.get("logistics_findings") or {}
        )
        return {"impact_findings": findings}
    except Exception as exc:
        return {
            "impact_findings": {"error": str(exc), "recovery_options": []},
            "errors": [f"Impact Agent error: {str(exc)}"]
        }


# Node 6: Synthesis & LLM Enrichment Node
def node_synthesize(state: OrchestratorState) -> Dict[str, Any]:
    cfg = get_llm_configuration()
    shipment = state.get("shipment", {})
    detector = state.get("detector_findings", {})
    impact = state.get("impact_findings", {})
    supplier = state.get("supplier_findings", {})
    logistics = state.get("logistics_findings", {})

    # Default deterministic executive summary
    executive_summary = (
        f"Investigation for shipment {shipment.get('id')} ({shipment.get('product')}): "
        f"Assigned severity '{detector.get('severity', 'Medium')}'. "
        f"Recommended Action: {impact.get('recommended_plan', 'Active Monitoring')}. "
        f"Estimated revenue at risk is ${impact.get('revenue_at_risk_usd', 0):,.2f}."
    )

    llm_narrative = None
    if cfg["mode"] == "live_llm":
        prompt = f"""
You are the Chief Supply Chain Orchestration Officer.
Provide an executive synthesis for shipment {shipment.get('id')}.
Product: {shipment.get('product')}
Supplier: {shipment.get('supplier')}
Delay: {shipment.get('delay_days')} days
Assigned Severity: {detector.get('severity')}
Supplier Delay Reason: {supplier.get('reported_delay_cause')}
Impact Revenue at Risk: ${impact.get('revenue_at_risk_usd', 0):,.2f}
Recommended Plan: {impact.get('recommended_plan')}

Summarize key root causes, inventory exposure, and operational trade-offs concisely in 3-4 professional bullet points.
"""
        try:
            response = call_llm(prompt)
            if response:
                llm_narrative = response
                executive_summary = response
        except Exception:
            # Deterministic fallback takes precedence on any LLM failure
            llm_narrative = None

    return {
        "executive_summary": executive_summary,
        "execution_mode": cfg["mode"],
        "llm_synthesis": {
            "provider": cfg["provider"],
            "model": cfg["model"],
            "narrative": llm_narrative,
            "is_live_llm": cfg["mode"] == "live_llm"
        }
    }


from datetime import datetime, timezone

def build_orchestrator_graph():
    """
    Construct the LangGraph workflow:
    START -> detect -> [supplier, inventory, logistics] in parallel -> impact -> synthesize -> END
    """
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("detect", node_detect)
    workflow.add_node("supplier", node_supplier)
    workflow.add_node("inventory", node_inventory)
    workflow.add_node("logistics", node_logistics)
    workflow.add_node("impact", node_impact)
    workflow.add_node("synthesize", node_synthesize)

    workflow.add_edge(START, "detect")

    # Fan out to parallel investigation agents
    workflow.add_edge("detect", "supplier")
    workflow.add_edge("detect", "inventory")
    workflow.add_edge("detect", "logistics")

    # Fan in to impact analysis
    workflow.add_edge("supplier", "impact")
    workflow.add_edge("inventory", "impact")
    workflow.add_edge("logistics", "impact")

    # Final synthesis
    workflow.add_edge("impact", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile()


# Singleton compiled graph instance
ORCHESTRATOR_GRAPH = build_orchestrator_graph()


def run_orchestration(
    shipment: Dict[str, Any],
    inventory: Dict[str, Any],
    disruptions: list,
    alternative_suppliers: list,
    alternative_logistics: list
) -> Dict[str, Any]:
    """
    Execute the multi-agent graph with given parameters and return unified results.
    Includes agent execution timeline tracking for Phase 4 frontend inspection.
    """
    start_time = datetime.now(timezone.utc)
    initial_state: OrchestratorState = {
        "shipment": shipment,
        "inventory": inventory,
        "disruptions": disruptions,
        "alternative_suppliers": alternative_suppliers,
        "alternative_logistics": alternative_logistics,
        "errors": []
    }

    final_state = ORCHESTRATOR_GRAPH.invoke(initial_state)

    impact_findings = final_state.get("impact_findings", {})
    risk_assessment = impact_findings.get("risk_assessment", {})
    rec_intelligence = impact_findings.get("recommendation_intelligence", {})

    # Calculated severity takes precedence from dynamic risk assessment if available
    calculated_severity = risk_assessment.get("classification") or final_state.get("detector_findings", {}).get("severity", "Medium")

    # Phase 4 Agent Execution Timeline
    execution_timeline = [
        {
            "step": 1,
            "agent": "Disruption Detection Agent",
            "status": "COMPLETED",
            "phase": "Detection & Triage",
            "findings_summary": f"Detected severity '{calculated_severity}' across shipment {shipment.get('id')} with +{shipment.get('delay_days', 0)}d delay."
        },
        {
            "step": 2,
            "agent": "Supplier Investigation Agent",
            "status": "COMPLETED",
            "phase": "Parallel Investigation",
            "findings_summary": f"Analyzed primary supplier ({shipment.get('supplier')}) & {final_state.get('supplier_findings', {}).get('alternative_suppliers_found', 0)} alternative vendors."
        },
        {
            "step": 3,
            "agent": "Inventory Shortage Agent",
            "status": "COMPLETED",
            "phase": "Parallel Investigation",
            "findings_summary": f"Available stock: {final_state.get('inventory_findings', {}).get('current_stock', 0)} units. Depletion timeline: {final_state.get('inventory_findings', {}).get('days_of_stock_remaining', 0)} days."
        },
        {
            "step": 4,
            "agent": "Logistics Routing Agent",
            "status": "COMPLETED",
            "phase": "Parallel Investigation",
            "findings_summary": f"Evaluated {final_state.get('logistics_findings', {}).get('available_routes_count', 0)} logistics transit routes and expedited alternatives."
        },
        {
            "step": 5,
            "agent": "Impact Analysis Agent",
            "status": "COMPLETED",
            "phase": "Business Impact Synthesis",
            "findings_summary": f"Projected revenue exposure: ${risk_assessment.get('revenue_at_risk_usd', 0):,.2f}. Formulated {len(impact_findings.get('recovery_options', []))} recovery playbooks."
        },
        {
            "step": 6,
            "agent": "Recovery Planning & Approval Supervisor",
            "status": "COMPLETED",
            "phase": "Decision Governance",
            "findings_summary": f"Primary recommendation: {impact_findings.get('recommended_plan')}. Sandboxed action simulation gated behind human sign-off."
        }
    ]

    return {
        "status": "success",
        "shipment_id": shipment.get("id"),
        "product": shipment.get("product"),
        "severity": calculated_severity,
        "risk_score": risk_assessment.get("risk_score", 0.0),
        "risk_assessment": risk_assessment,
        "recommendation_intelligence": rec_intelligence,
        "executive_summary": final_state.get("executive_summary"),
        "execution_mode": final_state.get("execution_mode"),
        "execution_timeline": execution_timeline,
        "llm_metadata": final_state.get("llm_synthesis"),
        "agent_findings": {
            "detection": final_state.get("detector_findings"),
            "supplier": final_state.get("supplier_findings"),
            "inventory": final_state.get("inventory_findings"),
            "logistics": final_state.get("logistics_findings"),
            "impact": impact_findings
        },
        "recovery_options": impact_findings.get("recovery_options", []),
        "recommended_plan": impact_findings.get("recommended_plan"),
        "assumptions": impact_findings.get("assumptions", []),
        "errors": final_state.get("errors", [])
    }
