"""
Verification Test Suite for Phase 4 Multi-Agent Orchestration
Validates:
1. LangGraph workflow topology, node registration, and fan-out/fan-in structure
2. Data propagation: Agents utilize actual shipment and inventory database records
3. Consistency: Stockout risk, revenue at risk, cost, and net benefit calculations
4. LLM failure and fallback to deterministic reasoning
5. End-to-end trace from Flask API to SQLite persistence (AnalysisRun & RecoveryPlan)
6. Human approval gating and sandboxed action simulation (zero live transactions)
"""

import os
import sys
import json
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import app
from backend.models import db, AnalysisRunModel, RecoveryPlanModel, RecoveryOptionModel, AuditEventModel
from backend.orchestrator import ORCHESTRATOR_GRAPH, run_orchestration, OrchestratorState
from backend.data import get_shipment_by_id, get_inventory_by_sku, get_disruptions_for_shipment, get_alternative_suppliers_for_sku, get_alternative_logistics_for_shipment


class OrchestrationVerificationTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_01_langgraph_workflow_topology(self):
        """Verify that LangGraph coordinates the workflow with required nodes and edges."""
        graph = ORCHESTRATOR_GRAPH.get_graph()
        node_names = set(graph.nodes.keys())
        expected_nodes = {"__start__", "detect", "supplier", "inventory", "logistics", "impact", "synthesize", "__end__"}
        self.assertTrue(expected_nodes.issubset(node_names), f"Missing nodes: {expected_nodes - node_names}")

        # Verify edge topology
        edges = [(e.source, e.target) for e in graph.edges]
        # Start -> detect
        self.assertIn(("__start__", "detect"), edges)
        # detect fans out to supplier, inventory, logistics
        self.assertIn(("detect", "supplier"), edges)
        self.assertIn(("detect", "inventory"), edges)
        self.assertIn(("detect", "logistics"), edges)
        # supplier, inventory, logistics fan in to impact
        self.assertIn(("supplier", "impact"), edges)
        self.assertIn(("inventory", "impact"), edges)
        self.assertIn(("logistics", "impact"), edges)
        # impact -> synthesize -> __end__
        self.assertIn(("impact", "synthesize"), edges)
        self.assertIn(("synthesize", "__end__"), edges)

    def test_02_actual_shipment_data_propagation(self):
        """Verify that agents execute using actual shipment and inventory data."""
        shipment = get_shipment_by_id("SH-101")
        self.assertIsNotNone(shipment)
        self.assertEqual(shipment["id"], "SH-101")
        self.assertEqual(shipment["sku"], "SKU-LAP-1001")

        inventory = get_inventory_by_sku("SKU-LAP-1001")
        disruptions = get_disruptions_for_shipment("SH-101")
        alt_suppliers = get_alternative_suppliers_for_sku("SKU-LAP-1001")
        alt_logistics = get_alternative_logistics_for_shipment("SH-101")

        result = run_orchestration(
            shipment=shipment,
            inventory=inventory,
            disruptions=disruptions,
            alternative_suppliers=alt_suppliers,
            alternative_logistics=alt_logistics
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["shipment_id"], "SH-101")
        self.assertEqual(result["product"], shipment["product"])

        # Check inventory agent findings reflect actual stock
        inv_findings = result["agent_findings"]["inventory"]
        self.assertEqual(inv_findings["current_stock"], inventory["available_stock"])
        self.assertEqual(inv_findings["reorder_threshold"], inventory["reorder_threshold"])
        self.assertEqual(inv_findings["daily_burn_rate"], inventory["daily_burn_rate"])

        # Check supplier agent findings reflect actual supplier
        sup_findings = result["agent_findings"]["supplier"]
        self.assertEqual(sup_findings["primary_supplier"], shipment["supplier"])
        self.assertGreater(sup_findings["alternative_suppliers_found"], 0)

        # Check logistics agent findings reflect actual routes
        log_findings = result["agent_findings"]["logistics"]
        self.assertGreater(log_findings["available_routes_count"], 0)

    def test_03_calculation_consistency_across_recommendations(self):
        """Verify mathematical consistency: net benefit = avoided revenue loss - indicative cost."""
        shipment = get_shipment_by_id("SH-101")
        inventory = get_inventory_by_sku(shipment["sku"])
        disruptions = get_disruptions_for_shipment(shipment["id"])
        alt_suppliers = get_alternative_suppliers_for_sku(shipment["sku"])
        alt_logistics = get_alternative_logistics_for_shipment(shipment["id"])

        result = run_orchestration(shipment, inventory, disruptions, alt_suppliers, alt_logistics)
        options = result.get("recovery_options", [])
        self.assertGreaterEqual(len(options), 2)

        for opt in options:
            cost = opt.get("indicative_cost_usd", 0.0)
            avoided_loss = opt.get("avoided_revenue_loss_usd", 0.0)
            net_benefit = opt.get("net_indicative_benefit_usd", 0.0)
            expected_net = round(avoided_loss - cost, 2)
            self.assertAlmostEqual(net_benefit, expected_net, places=2)

    def test_04_llm_failure_triggers_deterministic_fallback(self):
        """Verify that when the LLM throws an exception, orchestration falls back deterministically."""
        shipment = get_shipment_by_id("SH-101")
        inventory = get_inventory_by_sku(shipment["sku"])
        disruptions = get_disruptions_for_shipment(shipment["id"])
        alt_suppliers = get_alternative_suppliers_for_sku(shipment["sku"])
        alt_logistics = get_alternative_logistics_for_shipment(shipment["id"])

        # Patch call_llm to simulate an API failure/timeout
        with patch("backend.orchestrator.call_llm", side_effect=RuntimeError("Simulated LLM API timeout")):
            with patch("backend.orchestrator.get_llm_configuration", return_value={"mode": "live_llm", "provider": "mock_test", "model": "test-model"}):
                result = run_orchestration(shipment, inventory, disruptions, alt_suppliers, alt_logistics)

                # Orchestration must succeed and not crash
                self.assertEqual(result["status"], "success")
                self.assertIsNotNone(result["executive_summary"])
                self.assertIn("SH-101", result["executive_summary"])
                self.assertIn("Assigned severity", result["executive_summary"])

    def test_05_api_trace_and_persistence(self):
        """Trace POST /api/analyze-disruption through orchestrator and into SQLite."""
        resp = self.client.post(
            "/api/analyze-disruption",
            data=json.dumps({"shipment_id": "SH-101"}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertEqual(data["status"], "success")
        self.assertEqual(data["shipment_id"], "SH-101")
        self.assertIn("plan_id", data)
        self.assertIn("execution_timeline", data)
        self.assertEqual(len(data["execution_timeline"]), 6)

        with self.app.app_context():
            # Verify AnalysisRun persisted in SQLite
            latest_run = AnalysisRunModel.query.filter_by(shipment_id="SH-101").order_by(AnalysisRunModel.id.desc()).first()
            self.assertIsNotNone(latest_run)
            self.assertEqual(latest_run.shipment_id, "SH-101")

            # Verify RecoveryPlan persisted in SQLite
            plan = RecoveryPlanModel.query.filter_by(id="PLAN-SH-101").first()
            self.assertIsNotNone(plan)
            self.assertGreater(len(plan.options), 0)

            # Verify Audit Events logged
            recent_events = AuditEventModel.query.filter_by(associated_shipment="SH-101").order_by(AuditEventModel.id.desc()).limit(5).all()
            event_types = [e.event_type for e in recent_events]
            self.assertIn("DISRUPTION_ANALYSIS_COMPLETED", event_types)
            self.assertIn("RECOVERY_PLAN_CREATED", event_types)

    def test_06_approval_gated_action_simulation(self):
        """Verify that simulation is strictly gated behind human approval and executes safely in sandbox."""
        # Step 1: Analyze disruption to get fresh recovery options
        self.client.post(
            "/api/analyze-disruption",
            data=json.dumps({"shipment_id": "SH-101"}),
            content_type="application/json"
        )
        with self.app.app_context():
            plan = RecoveryPlanModel.query.filter_by(id="PLAN-SH-101").first()
            target_option = plan.options[0]
            target_option_id = target_option.id

            # Reset option status to Proposed if previously approved
            target_option.status = "Proposed"
            db.session.commit()

        # Step 2: Attempt simulation before approval -> must fail with 400
        sim_resp_blocked = self.client.post(f"/api/recovery-options/{target_option_id}/simulate")
        self.assertEqual(sim_resp_blocked.status_code, 400)
        sim_data = sim_resp_blocked.get_json()
        self.assertIn("requires human approval first", sim_data["message"])

        # Step 3: Approve option
        approve_resp = self.client.post(
            f"/api/recovery-options/{target_option_id}/decision",
            data=json.dumps({"decision": "Approved", "decided_by": "Supply Chain Director", "reason": "Authorized for sandbox simulation."}),
            content_type="application/json"
        )
        self.assertEqual(approve_resp.status_code, 200)

        # Step 4: Simulate approved option -> must succeed with sandbox notice
        sim_resp_success = self.client.post(f"/api/recovery-options/{target_option_id}/simulate")
        self.assertEqual(sim_resp_success.status_code, 200)
        sim_success_data = sim_resp_success.get_json()
        self.assertEqual(sim_success_data["status"], "success")
        self.assertEqual(sim_success_data["recovery_option"]["status"], "Simulated")
        self.assertIn("simulation_notice", sim_success_data)
        self.assertIn("sandbox", sim_success_data["simulation_notice"].lower())

        # Step 5: Verify audit event records ACTION_SIMULATION_EXECUTED
        with self.app.app_context():
            sim_event = AuditEventModel.query.filter_by(
                event_type="ACTION_SIMULATION_EXECUTED",
                associated_shipment="SH-101"
            ).order_by(AuditEventModel.id.desc()).first()
            self.assertIsNotNone(sim_event)
            self.assertEqual(sim_event.outcome, "SUCCESS")
            details = json.loads(sim_event.details_json)
            self.assertTrue(details.get("execution_sandbox"))


if __name__ == "__main__":
    unittest.main()
