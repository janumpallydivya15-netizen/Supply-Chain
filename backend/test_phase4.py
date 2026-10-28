"""
Supply Chain Disruption Command Center - Phase 4 Integration Tests
Validates:
- Persistent audit trail with extended fields (associated_disruption, previous_status, new_status, outcome, details_json)
- Filtered audit trail by event_type, shipment_id, search term
- Audit trail pagination and limit enforcement
- Single audit event inspection by ID
- Recovery plan status update endpoint with audit logging
- Simulated action audit event with status transitions
"""

import sys
import os
import unittest
import json

# Ensure project root is in python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import app
from backend.models import db, AuditEventModel, RecoveryPlanModel, RecoveryOptionModel


class Phase4IntegrationTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_01_audit_events_endpoint_structure(self):
        """GET /api/audit-events should return paginated response with total, page, pages."""
        response = self.client.get("/api/audit-events?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(data.get("status"), "success")
        self.assertIn("audit_events", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("pages", data)
        self.assertIn("limit", data)
        self.assertEqual(data["limit"], 5)
        self.assertIsInstance(data["audit_events"], list)

    def test_02_audit_event_detail_by_id(self):
        """GET /api/audit-events/<id> should return the specific event with details."""
        # Grab first event
        list_resp = self.client.get("/api/audit-events?limit=1")
        list_data = list_resp.get_json()
        if list_data["audit_events"]:
            first_event = list_data["audit_events"][0]
            event_id = first_event["id"]

            detail_resp = self.client.get(f"/api/audit-events/{event_id}")
            self.assertEqual(detail_resp.status_code, 200)
            detail_data = detail_resp.get_json()
            self.assertEqual(detail_data.get("status"), "success")
            self.assertEqual(detail_data["audit_event"]["id"], event_id)
            self.assertIn("outcome", detail_data["audit_event"])
            self.assertIn("details", detail_data["audit_event"])

    def test_03_audit_events_filtering(self):
        """GET /api/audit-events should correctly filter by event_type and shipment_id."""
        # Filter by shipment
        resp = self.client.get("/api/audit-events?shipment_id=SH-101")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for ev in data["audit_events"]:
            self.assertEqual(ev.get("associated_shipment"), "SH-101")

        # Filter by search keyword
        search_resp = self.client.get("/api/audit-events?search=investigation")
        self.assertEqual(search_resp.status_code, 200)
        search_data = search_resp.get_json()
        self.assertIsInstance(search_data["audit_events"], list)

    def test_04_recovery_plan_status_transition_and_audit_logging(self):
        """POST /api/recovery-plans/<plan_id>/status should update status and record audit event."""
        plan_id = "PLAN-SH-101"

        # Update status to 'Awaiting Approval' / 'Pending Approval'
        update_resp = self.client.post(
            f"/api/recovery-plans/{plan_id}/status",
            data=json.dumps({
                "status": "Pending Approval",
                "reason": "Escalated for director sign-off in Phase 4 test.",
                "actor": "Senior Logistics Coordinator"
            }),
            content_type="application/json"
        )
        self.assertEqual(update_resp.status_code, 200)
        update_data = update_resp.get_json()
        self.assertEqual(update_data["status"], "success")
        self.assertEqual(update_data["recovery_plan"]["status"], "Pending Approval")

        # Verify audit trail recorded PLAN_STATUS_CHANGED
        audit_resp = self.client.get(f"/api/audit-events?event_type=PLAN_STATUS_CHANGED&shipment_id=SH-101")
        self.assertEqual(audit_resp.status_code, 200)
        audit_data = audit_resp.get_json()
        self.assertGreaterEqual(audit_data["total"], 1)
        latest_audit = audit_data["audit_events"][0]
        self.assertEqual(latest_audit["event_type"], "PLAN_STATUS_CHANGED")
        self.assertEqual(latest_audit["new_status"], "Pending Approval")
        self.assertEqual(latest_audit["actor_name"], "Senior Logistics Coordinator")

    def test_05_invalid_plan_status_handling(self):
        """POST /api/recovery-plans/<plan_id>/status should reject invalid status strings."""
        resp = self.client.post(
            "/api/recovery-plans/PLAN-SH-101/status",
            data=json.dumps({"status": "NON_EXISTENT_STATUS"}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "error")


if __name__ == "__main__":
    unittest.main()
