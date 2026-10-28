"""
Phase 3 Test Suite: Persistent Database, Recovery Plan Management, Human Approval & Audit Trail
Tests SQLite persistence, approval workflows, simulation gating, audit event creation, and backward compatibility.
"""

import unittest
import os
import json
import backend.app as app_mod
from backend.models import (
    db, DisruptionModel, AnalysisRunModel, RecoveryPlanModel,
    RecoveryOptionModel, ApprovalDecisionModel, AuditEventModel
)


class TestPhase3Suite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app_mod.app.config["TESTING"] = True
        cls.client = app_mod.app.test_client()

    def test_01_database_initialization_and_seed(self):
        """Verify SQLite database initialized and seeded disruptions safely."""
        with app_mod.app.app_context():
            disruptions = DisruptionModel.query.all()
            self.assertGreaterEqual(len(disruptions), 3)
            # Verify SH-101 disruption exists
            dis_101 = DisruptionModel.query.filter_by(affected_shipment="SH-101").first()
            self.assertIsNotNone(dis_101)
            self.assertEqual(dis_101.severity, "Critical")

    def test_02_create_and_retrieve_recovery_plan(self):
        """Verify POST /api/analyze-disruption saves plan and options to SQLite."""
        res = self.client.post("/api/analyze-disruption", json={"shipment_id": "SH-101"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["plan_id"], "PLAN-SH-101")
        self.assertGreaterEqual(len(data["recovery_options"]), 3)

        # Retrieve plan from dedicated endpoint
        res_plan = self.client.get("/api/recovery-plans/PLAN-SH-101")
        self.assertEqual(res_plan.status_code, 200)
        plan_data = res_plan.get_json()["recovery_plan"]
        self.assertEqual(plan_data["shipment_id"], "SH-101")
        self.assertEqual(plan_data["status"], "Proposed")
        self.assertEqual(len(plan_data["options"]), len(data["recovery_options"]))

    def test_03_blocking_simulation_of_unapproved_option(self):
        """Verify unapproved option cannot be simulated (400 Bad Request)."""
        res_plan = self.client.get("/api/recovery-plans/PLAN-SH-101")
        options = res_plan.get_json()["recovery_plan"]["options"]
        opt_id = options[0]["id"]

        # Attempt simulation on Proposed option
        res_sim = self.client.post(f"/api/recovery-options/{opt_id}/simulate")
        self.assertEqual(res_sim.status_code, 400)
        self.assertIn("requires human approval first", res_sim.get_json()["message"])

    def test_04_human_approval_decision(self):
        """Verify human operator can approve a proposed recovery option."""
        res_plan = self.client.get("/api/recovery-plans/PLAN-SH-101")
        options = res_plan.get_json()["recovery_plan"]["options"]
        opt_id = options[0]["id"]

        res_app = self.client.post(f"/api/recovery-options/{opt_id}/decision", json={
            "decision": "Approved",
            "reason": "Expedited air-freight approved to avoid stockout.",
            "decided_by": "Director of Supply Chain"
        })
        self.assertEqual(res_app.status_code, 200)
        opt_data = res_app.get_json()["recovery_option"]
        self.assertEqual(opt_data["status"], "Approved")
        self.assertEqual(opt_data["latest_decision"]["decision"], "Approved")
        self.assertEqual(opt_data["latest_decision"]["decided_by"], "Director of Supply Chain")

    def test_05_safe_simulation_of_approved_option(self):
        """Verify approved option can be simulated successfully."""
        res_plan = self.client.get("/api/recovery-plans/PLAN-SH-101")
        options = res_plan.get_json()["recovery_plan"]["options"]
        opt_id = options[0]["id"]

        res_sim = self.client.post(f"/api/recovery-options/{opt_id}/simulate")
        self.assertEqual(res_sim.status_code, 200)
        data = res_sim.get_json()
        self.assertEqual(data["recovery_option"]["status"], "Simulated")
        self.assertIn("simulation_notice", data)

        # Idempotency / repeat simulation check
        res_sim_again = self.client.post(f"/api/recovery-options/{opt_id}/simulate")
        self.assertEqual(res_sim_again.status_code, 400)
        self.assertIn("has already been simulated", res_sim_again.get_json()["message"])

    def test_06_human_rejection_decision(self):
        """Verify human operator can reject an option."""
        res_plan = self.client.get("/api/recovery-plans/PLAN-SH-101")
        options = res_plan.get_json()["recovery_plan"]["options"]
        opt_id = options[1]["id"]  # Option 2

        res_rej = self.client.post(f"/api/recovery-options/{opt_id}/decision", json={
            "decision": "Rejected",
            "reason": "Secondary vendor procurement unit cost exceeds variance limit."
        })
        self.assertEqual(res_rej.status_code, 200)
        self.assertEqual(res_rej.get_json()["recovery_option"]["status"], "Rejected")

        # Rejected option cannot be simulated
        res_sim_rej = self.client.post(f"/api/recovery-options/{opt_id}/simulate")
        self.assertEqual(res_sim_rej.status_code, 400)

    def test_07_audit_event_creation_and_retrieval(self):
        """Verify immutable audit events logged for analysis, approval, and simulation."""
        res_audit = self.client.get("/api/audit-events")
        self.assertEqual(res_audit.status_code, 200)
        events = res_audit.get_json()["audit_events"]
        self.assertGreaterEqual(len(events), 4)

        event_types = [e["event_type"] for e in events]
        self.assertIn("DISRUPTION_ANALYSIS_CREATED", event_types)
        self.assertIn("RECOVERY_PLAN_CREATED", event_types)
        self.assertIn("OPTION_APPROVED", event_types)
        self.assertIn("ACTION_SIMULATION_EXECUTED", event_types)

    def test_08_invalid_ids_and_state_transitions(self):
        """Verify graceful error responses for nonexistent IDs and bad payloads."""
        # Nonexistent plan
        res_bad_plan = self.client.get("/api/recovery-plans/NONEXISTENT-999")
        self.assertEqual(res_bad_plan.status_code, 404)

        # Nonexistent option decision
        res_bad_opt = self.client.post("/api/recovery-options/99999/decision", json={"decision": "Approved"})
        self.assertEqual(res_bad_opt.status_code, 404)

        # Invalid decision payload
        res_invalid_dec = self.client.post("/api/recovery-options/1/decision", json={"decision": "UnknownDecision"})
        self.assertEqual(res_invalid_dec.status_code, 400)

    def test_09_backward_compatibility(self):
        """Ensure all Phase 1 and Phase 2 endpoints remain intact."""
        # Phase 1
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.get_json()["phase"], 3)
        self.assertTrue(r_health.get_json()["persistence"])

        r_dash = self.client.get("/api/dashboard")
        self.assertEqual(r_dash.status_code, 200)

        r_ship = self.client.get("/api/shipments")
        self.assertEqual(r_ship.status_code, 200)

        r_dis = self.client.get("/api/disruptions")
        self.assertEqual(r_dis.status_code, 200)

        r_inv = self.client.get("/api/inventory")
        self.assertEqual(r_inv.status_code, 200)


if __name__ == "__main__":
    unittest.main()
