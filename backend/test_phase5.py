"""
Supply Chain Disruption Command Center - Phase 5 Integration Tests
Validates:
- Dynamic risk scoring formula (0-100) and normalization
- Risk score sensitivity when input parameters change (delays, stock levels)
- Accurate prioritization of critical disruptions
- Business impact calculations (days to stockout, revenue at risk, avoided loss, net benefit)
- Side-by-side recovery option comparisons with net benefit sorting
- Explainable recommendation engine with rationale and trade-off analysis
- Transparent handling of missing/invalid inputs
- End-to-end integration through /api/analyze-disruption and SQLite persistence of Phase 5 fields
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
from backend.models import db, RecoveryPlanModel, RecoveryOptionModel
from backend.risk_service import (
    calculate_risk_score,
    analyze_recovery_options_impact,
    formulate_explainable_recommendation
)


class Phase5IntegrationTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_01_risk_scoring_calculation_and_bounds(self):
        """Dynamic risk score must be bounded between 0 and 100 with documented factors."""
        shipment = {
            "id": "SH-101",
            "quantity": 50,
            "delay_days": 3,
            "risk_level": "Critical"
        }
        inventory = {
            "available_stock": 14,
            "reorder_threshold": 60,
            "daily_burn_rate": 8,
            "unit_cost_usd": 850
        }
        alt_suppliers = [{"name": "Alt 1"}]
        alt_logistics = [{"carrier": "Carrier 1"}]

        result = calculate_risk_score(shipment, inventory, alt_suppliers=alt_suppliers, alt_logistics=alt_logistics)

        self.assertIn("risk_score", result)
        self.assertIn("classification", result)
        self.assertIn("top_contributing_factors", result)
        self.assertGreaterEqual(result["risk_score"], 0.0)
        self.assertLessEqual(result["risk_score"], 100.0)
        # With high shortage and critical status, score should be High or Critical
        self.assertIn(result["classification"], ["High", "Critical"])
        self.assertEqual(len(result["top_contributing_factors"]), 3)

    def test_02_risk_score_changes_with_input_delays(self):
        """Risk score must respond dynamically when delays and stock levels change."""
        shipment_low_delay = {"quantity": 50, "delay_days": 1, "risk_level": "Low"}
        shipment_high_delay = {"quantity": 50, "delay_days": 6, "risk_level": "Critical"}
        inventory = {"available_stock": 10, "reorder_threshold": 50, "daily_burn_rate": 5, "unit_cost_usd": 200}

        score_low = calculate_risk_score(shipment_low_delay, inventory)["risk_score"]
        score_high = calculate_risk_score(shipment_high_delay, inventory)["risk_score"]

        self.assertGreater(score_high, score_low)

    def test_03_missing_or_invalid_inputs_handled_safely(self):
        """Scoring function must handle None/empty inputs without raising exceptions."""
        result = calculate_risk_score(None, None)
        self.assertIsInstance(result["risk_score"], float)
        self.assertIn(result["classification"], ["Low", "Medium", "High", "Critical"])

    def test_04_business_impact_and_option_comparison(self):
        """Recovery options must calculate shortage reduction, avoided loss, and net benefit."""
        shipment = {"id": "SH-101", "quantity": 50, "delay_days": 3}
        inventory = {
            "available_stock": 14,
            "reorder_threshold": 60,
            "daily_burn_rate": 8,
            "unit_cost_usd": 850,
            "target_stock": 80
        }
        risk_assessment = {
            "days_to_stockout": 1.75,
            "revenue_at_risk_usd": 15937.5,
            "classification": "Critical"
        }
        raw_options = [
            {
                "option_id": "OPT-1",
                "name": "Expedited Air Freight",
                "type": "Carrier Intercept / Air Freight",
                "indicative_cost_usd": 1850,
                "expected_time_to_resolve_days": 1,
                "feasibility": "High"
            },
            {
                "option_id": "OPT-3",
                "name": "Passive Monitoring",
                "type": "No Active Intervention",
                "indicative_cost_usd": 0,
                "expected_time_to_resolve_days": 3,
                "feasibility": "High"
            }
        ]

        compared = analyze_recovery_options_impact(shipment, inventory, raw_options, risk_assessment)
        self.assertEqual(len(compared), 2)
        # Option 1 should have positive net indicative benefit
        opt1 = next(o for o in compared if o["option_id"] == "OPT-1")
        self.assertGreater(opt1["avoided_revenue_loss_usd"], 0)
        self.assertGreater(opt1["net_indicative_benefit_usd"], 0)
        # Compared options should be sorted by net benefit descending
        self.assertEqual(compared[0]["option_id"], "OPT-1")

    def test_05_explainable_recommendation_rationale(self):
        """Recommendation engine must provide transparent rationale, trade-offs, and assumptions."""
        ranked_options = [
            {
                "option_id": "OPT-1",
                "name": "Expedited Air Freight",
                "type": "Carrier Intercept / Air Freight",
                "indicative_cost_usd": 1850,
                "expected_time_to_resolve_days": 1,
                "shortage_reduction_units": 16.0,
                "avoided_revenue_loss_usd": 20400.0,
                "net_indicative_benefit_usd": 18550.0,
                "residual_risk": "Low",
                "feasibility": "High"
            },
            {
                "option_id": "OPT-2",
                "name": "Emergency Secondary PO",
                "type": "Alternative Supplier Sourcing",
                "indicative_cost_usd": 17800,
                "expected_time_to_resolve_days": 2,
                "shortage_reduction_units": 50.0,
                "avoided_revenue_loss_usd": 10200.0,
                "net_indicative_benefit_usd": -7600.0,
                "residual_risk": "Medium",
                "feasibility": "High"
            }
        ]
        risk_assessment = {"revenue_at_risk_usd": 20400.0, "classification": "Critical"}
        shipment = {"id": "SH-101"}

        rec = formulate_explainable_recommendation(ranked_options, risk_assessment, shipment)
        self.assertEqual(rec["recommended_option_id"], "OPT-1")
        self.assertIn("selection_rationale", rec)
        self.assertIn("considered_alternatives", rec)
        self.assertGreaterEqual(len(rec["assumptions"]), 2)
        self.assertGreaterEqual(len(rec["data_limitations"]), 2)

    def test_06_end_to_end_analysis_api_persistence(self):
        """POST /api/analyze-disruption must persist risk score, impact metrics, and intel to SQLite."""
        resp = self.client.post(
            "/api/analyze-disruption",
            data=json.dumps({"shipment_id": "SH-101"}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("risk_score", data)
        self.assertIn("risk_assessment", data)
        self.assertIn("recommendation_intelligence", data)
        self.assertGreater(data["risk_score"], 0)

        # Verify persisted recovery plan has Phase 5 fields within app context
        with self.app.app_context():
            plan = RecoveryPlanModel.query.filter_by(id="PLAN-SH-101").first()
            self.assertIsNotNone(plan)
            self.assertGreater(plan.risk_score, 0)
            plan_dict = plan.to_dict()
            self.assertIn("risk_assessment", plan_dict)
            self.assertIn("recommendation_intelligence", plan_dict)

            # Verify options have Phase 5 business impact fields
            self.assertGreater(len(plan.options), 0)
            first_opt = plan.options[0].to_dict()
            self.assertIn("avoided_revenue_loss_usd", first_opt)
            self.assertIn("net_indicative_benefit_usd", first_opt)
            self.assertIn("shortage_reduction_units", first_opt)

    def test_07_disruptions_descending_risk_sorting(self):
        """GET /api/disruptions and /api/dashboard must return disruptions sorted by risk score descending."""
        # Check /api/disruptions
        resp_disruptions = self.client.get("/api/disruptions")
        self.assertEqual(resp_disruptions.status_code, 200)
        disruptions = resp_disruptions.get_json().get("disruptions", [])
        self.assertGreater(len(disruptions), 1)

        scores = [d.get("risk_score", 0.0) for d in disruptions]
        self.assertEqual(scores, sorted(scores, reverse=True), "Disruptions must be sorted by risk_score descending")

        # Check /api/dashboard
        resp_dash = self.client.get("/api/dashboard")
        self.assertEqual(resp_dash.status_code, 200)
        dash_disruptions = resp_dash.get_json().get("disruptions", [])
        dash_scores = [d.get("risk_score", 0.0) for d in dash_disruptions]
        self.assertEqual(dash_scores, sorted(dash_scores, reverse=True), "Dashboard disruptions must be sorted by risk_score descending")

    def test_08_disruptions_top_contributing_factors_payload(self):
        """Disruptions must return transparent top contributing factors and formula documentation."""
        resp = self.client.get("/api/disruptions")
        self.assertEqual(resp.status_code, 200)
        disruptions = resp.get_json().get("disruptions", [])

        for d in disruptions:
            self.assertIn("risk_score", d)
            self.assertIn("calculated_severity", d)
            self.assertIn("top_contributing_factors", d)
            self.assertIn("scoring_formula", d)
            self.assertIsInstance(d["top_contributing_factors"], list)
            self.assertGreater(len(d["top_contributing_factors"]), 0)

            # Verify factor structure
            first_factor = d["top_contributing_factors"][0]
            self.assertIn("factor", first_factor)
            self.assertIn("score", first_factor)
            self.assertIn("max", first_factor)
            self.assertIn("detail", first_factor)

    def test_09_frontend_modal_and_sorting_integration(self):
        """Frontend app.js must include risk sorting, factor rendering, and Phase 5 modal notice."""
        app_js_path = os.path.join(PROJECT_ROOT, "frontend", "js", "app.js")
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js_content = f.read()

        # Verify sorting function exists and handles descending order
        self.assertIn("function sortDisruptionsByRisk", app_js_content)
        self.assertIn("function getNumericRiskScore", app_js_content)
        self.assertIn("function generateDisruptionRiskExplanation", app_js_content)

        # Verify modal elements
        self.assertIn("Dynamic Disruption Risk Score", app_js_content)
        self.assertIn("Contributing Risk Factors", app_js_content)
        self.assertIn("Prioritization Rationale", app_js_content)
        self.assertIn("Dynamic Risk Intelligence & Prioritization (Phase 5 Active)", app_js_content)


if __name__ == "__main__":
    unittest.main()
