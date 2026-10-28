"""
Phase 2 Test Suite: Multi-Agent Supply Chain Disruption Intelligence
Tests agent logic, LangGraph orchestration, API request validation, and error handling.
"""

import unittest
from backend.data import (
    get_shipment_by_id, get_inventory_by_sku, get_disruptions_for_shipment,
    get_alternative_suppliers_for_sku, get_alternative_logistics_for_shipment
)
from backend.agents.detector import run_disruption_detector
from backend.agents.supplier import run_supplier_investigation
from backend.agents.inventory import run_inventory_analysis
from backend.agents.logistics import run_logistics_analysis
from backend.agents.impact import run_impact_analysis
from backend.orchestrator import run_orchestration
import backend.app as app_mod


class TestMultiAgentSystem(unittest.TestCase):

    def setUp(self):
        self.app = app_mod.app.test_client()

    def test_01_detector_agent(self):
        shipment = get_shipment_by_id("SH-101")
        inv = get_inventory_by_sku("SKU-LAP-1001")
        dis = get_disruptions_for_shipment("SH-101")
        findings = run_disruption_detector(shipment, inv, dis)
        self.assertEqual(findings["severity"], "Critical")
        self.assertTrue(findings["is_disrupted"])
        self.assertGreaterEqual(len(findings["detected_issues"]), 2)

    def test_02_supplier_agent(self):
        shipment = get_shipment_by_id("SH-101")
        alts = get_alternative_suppliers_for_sku("SKU-LAP-1001")
        findings = run_supplier_investigation(shipment, alts)
        self.assertEqual(findings["primary_supplier"], "Apex Electronics Ltd.")
        self.assertEqual(findings["alternative_suppliers_found"], 2)
        self.assertIsNotNone(findings["recommended_alternative"])
        self.assertEqual(findings["recommended_alternative"]["supplier_name"], "Bharat Micro Systems Ltd.")

    def test_03_inventory_agent(self):
        shipment = get_shipment_by_id("SH-101")
        inv = get_inventory_by_sku("SKU-LAP-1001")
        findings = run_inventory_analysis(shipment, inv)
        self.assertEqual(findings["current_stock"], 14)
        self.assertEqual(findings["reorder_threshold"], 60)
        self.assertEqual(findings["shortage_to_threshold"], 46)
        self.assertTrue(findings["will_stockout_before_arrival"])

    def test_04_logistics_agent(self):
        shipment = get_shipment_by_id("SH-101")
        alts = get_alternative_logistics_for_shipment("SH-101")
        findings = run_logistics_analysis(shipment, alts)
        self.assertTrue(findings["has_alternative_routes"])
        self.assertEqual(findings["available_routes_count"], 2)
        self.assertIsNotNone(findings["recommended_route"])
        self.assertEqual(findings["recommended_route"]["carrier"], "BlueDart Aero Priority")

    def test_05_impact_agent(self):
        shipment = get_shipment_by_id("SH-101")
        inv = get_inventory_by_sku("SKU-LAP-1001")
        sup = run_supplier_investigation(shipment, get_alternative_suppliers_for_sku("SKU-LAP-1001"))
        inv_f = run_inventory_analysis(shipment, inv)
        log_f = run_logistics_analysis(shipment, get_alternative_logistics_for_shipment("SH-101"))

        findings = run_impact_analysis(shipment, inv, sup, inv_f, log_f)
        self.assertGreater(findings["revenue_at_risk_usd"], 0)
        self.assertGreaterEqual(len(findings["recovery_options"]), 3)
        self.assertGreater(len(findings["assumptions"]), 0)

    def test_06_orchestrator_pipeline(self):
        shipment = get_shipment_by_id("SH-101")
        inv = get_inventory_by_sku("SKU-LAP-1001")
        dis = get_disruptions_for_shipment("SH-101")
        alts = get_alternative_suppliers_for_sku("SKU-LAP-1001")
        log_alts = get_alternative_logistics_for_shipment("SH-101")

        result = run_orchestration(shipment, inv, dis, alts, log_alts)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["severity"], "Critical")
        self.assertIn("agent_findings", result)
        self.assertIn("recovery_options", result)
        self.assertEqual(result["execution_mode"], "deterministic_mock")

    def test_07_api_analyze_valid(self):
        res = self.app.post("/api/analyze-disruption", json={"shipment_id": "SH-101"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["shipment_id"], "SH-101")
        self.assertEqual(data["severity"], "Critical")

    def test_08_api_analyze_missing_body(self):
        res = self.app.post("/api/analyze-disruption", json={})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["status"], "error")

    def test_09_api_analyze_not_found(self):
        res = self.app.post("/api/analyze-disruption", json={"shipment_id": "SH-9999"})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.get_json()["status"], "error")

    def test_10_existing_routes_preserved(self):
        r_health = self.app.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertGreaterEqual(r_health.get_json()["phase"], 2)

        r_dash = self.app.get("/api/dashboard")
        self.assertEqual(r_dash.status_code, 200)

        r_ship = self.app.get("/api/shipments?status=Delayed")
        self.assertEqual(r_ship.status_code, 200)
        self.assertEqual(r_ship.get_json()["count"], 2)

    def test_11_analyze_button_event_wiring_and_cache_prevention(self):
        """Verify that frontend assets declare type=button, cache busting, and no-cache headers."""
        # 1. HTML button attributes
        r_html = self.app.get("/")
        self.assertEqual(r_html.status_code, 200)
        html_content = r_html.get_data(as_text=True)
        self.assertIn('id="modalAnalyzeBtn"', html_content)
        self.assertIn('type="button"', html_content)
        self.assertIn('js/app.js?v=', html_content)
        self.assertIn("no-cache", r_html.headers.get("Cache-Control", ""))

        # 2. JavaScript event handler wiring
        r_js = self.app.get("/js/app.js")
        self.assertEqual(r_js.status_code, 200)
        js_content = r_js.get_data(as_text=True)
        self.assertIn("handleAnalyzeDisruption", js_content)
        self.assertIn("elements.modalAnalyzeBtn.addEventListener('click', handleAnalyzeDisruption)", js_content)
        self.assertIn("e.preventDefault()", js_content)
        self.assertIn("e.stopPropagation()", js_content)
        # Verify modal dismissal is decoupled from analyze click
        self.assertNotIn("modalAnalyzeBtn.addEventListener('click', closeModal)", js_content)
        self.assertIn("no-cache", r_js.headers.get("Cache-Control", ""))


if __name__ == "__main__":
    unittest.main()
