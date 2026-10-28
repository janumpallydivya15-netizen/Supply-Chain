"""
Supply Chain Disruption Command Center - Backend API
Phase 1, 2, & 3: Project Setup, Multi-Agent Intelligence, and Persistent Database with Human Approvals
"""

import os
import sys
import json
from datetime import datetime

# Ensure project root directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, jsonify, request, send_from_directory

from backend.data import (
    SHIPMENTS, INVENTORY, DISRUPTIONS,
    get_shipment_by_id, get_inventory_by_sku, get_disruptions_for_shipment,
    get_alternative_suppliers_for_sku, get_alternative_logistics_for_shipment
)
from backend.orchestrator import run_orchestration
from backend.models import (
    db, DisruptionModel, AnalysisRunModel, RecoveryPlanModel,
    RecoveryOptionModel, ApprovalDecisionModel, AuditEventModel,
    log_audit_event
)

# Configure paths for frontend assets and database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)
DB_PATH = os.path.join(INSTANCE_DIR, "supply_chain.db")

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)

# Configure SQLite Database with SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# -------------------------------------------------------------------------
# Database Initialization & Seed Function
# -------------------------------------------------------------------------
def initialize_database():
    """Create tables if they don't exist and seed baseline disruptions."""
    with app.app_context():
        db.create_all()

        # Seed initial disruptions if not already present
        for dis in DISRUPTIONS:
            existing = DisruptionModel.query.filter_by(id=dis["id"]).first()
            if not existing:
                new_dis = DisruptionModel(
                    id=dis["id"],
                    title=dis["title"],
                    disruption_type=dis["type"],
                    severity=dis["severity"],
                    affected_item=dis["affected_item"],
                    affected_shipment=dis.get("affected_shipment"),
                    facility=dis.get("facility"),
                    reported_date=dis.get("reported_date"),
                    description=dis.get("description"),
                    impact_summary=dis.get("impact_summary"),
                    future_agent_task=dis.get("future_agent_task")
                )
                db.session.add(new_dis)

        # Log system startup event if audit log is empty
        if AuditEventModel.query.count() == 0:
            log_audit_event(
                event_type="SYSTEM_INITIALIZED",
                description="Supply Chain Disruption Command Center initialized with SQLite persistent storage and audit logging.",
                actor_type="System",
                actor_name="Command Center Core"
            )

        db.session.commit()


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def calculate_metrics():
    """Derive summary metrics dynamically from the deterministic sample data and persisted database."""
    total_shipments = len(SHIPMENTS)
    delayed_shipments = sum(1 for s in SHIPMENTS if s["status"] == "Delayed")
    low_stock_items = sum(1 for i in INVENTORY if i["stock_status"] in ("Critical", "Low Stock"))
    open_disruptions = DisruptionModel.query.count() if db.session else len(DISRUPTIONS)

    return {
        "total_shipments": total_shipments,
        "delayed_shipments": delayed_shipments,
        "low_stock_items": low_stock_items,
        "open_disruptions": open_disruptions
    }


@app.after_request
def add_cors_headers(response):
    """Ensure CORS and no-cache headers are present on all responses."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    if request.path.startswith("/api/") or request.path.endswith(".js") or request.path.endswith(".html") or request.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# -------------------------------------------------------------------------
# Web & API Endpoints (Phase 1 & 2 Preserved)
# -------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Serve the single-page dashboard frontend with no-cache headers."""
    resp = send_from_directory(FRONTEND_DIR, "index.html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/<path:path>", methods=["GET"])
def static_proxy(path):
    """Serve frontend static assets (CSS, JS, assets) with no-cache headers for dev iteration."""
    resp = send_from_directory(FRONTEND_DIR, path)
    if path.endswith(".js") or path.endswith(".html"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


@app.route("/api/health", methods=["GET"])
def health():
    """Return backend operational status."""
    return jsonify({
        "status": "ok",
        "service": "supply-chain-command-center",
        "phase": 3,
        "database": "sqlite",
        "persistence": True
    }), 200


@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    """Return comprehensive dashboard data: summary metrics, shipments, disruptions, inventory."""
    try:
        metrics = calculate_metrics()
        # Retrieve disruptions from database to reflect persistence
        db_disruptions = [d.to_dict() for d in DisruptionModel.query.all()]
        raw_disruptions = db_disruptions if db_disruptions else [d.copy() for d in DISRUPTIONS]

        # Enrich disruptions with dynamic risk scoring
        enriched_disruptions = []
        for d in raw_disruptions:
            d_copy = dict(d)
            shipment_id = d_copy.get("affected_shipment")
            shipment = get_shipment_by_id(shipment_id) if shipment_id else {}
            sku = shipment.get("sku") if shipment else None
            inv = get_inventory_by_sku(sku) if sku else {}
            alt_sup = get_alternative_suppliers_for_sku(sku) if sku else []
            alt_log = get_alternative_logistics_for_shipment(shipment_id) if shipment_id else []

            score_data = calculate_risk_score(
                shipment=shipment,
                inventory=inv,
                disruptions=[d_copy],
                alt_suppliers=alt_sup,
                alt_logistics=alt_log
            )
            d_copy["risk_score"] = score_data["risk_score"]
            d_copy["calculated_severity"] = score_data["classification"]
            d_copy["days_to_stockout"] = score_data["days_to_stockout"]
            d_copy["revenue_at_risk_usd"] = score_data["revenue_at_risk_usd"]
            d_copy["top_contributing_factors"] = score_data["top_contributing_factors"]
            d_copy["scoring_formula"] = score_data["formula_documentation"]
            enriched_disruptions.append(d_copy)

        # Sort disruptions dynamically by descending risk score
        enriched_disruptions.sort(key=lambda x: float(x.get("risk_score") or 0.0), reverse=True)

        return jsonify({
            "status": "success",
            "metrics": metrics,
            "shipments": SHIPMENTS,
            "disruptions": enriched_disruptions,
            "inventory": INVENTORY,
            "metadata": {
                "dataset": "Phase 3 Hybrid Benchmark & Persisted SQLite Data",
                "is_mock": True
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve dashboard payload: {str(e)}"
        }), 500


@app.route("/api/shipments", methods=["GET"])
def get_shipments():
    """Return shipment records with optional status filtering."""
    status_filter = request.args.get("status")
    if status_filter and status_filter.strip() and status_filter.lower() != "all":
        filtered = [
            s for s in SHIPMENTS
            if s["status"].lower() == status_filter.strip().lower()
        ]
        return jsonify({
            "status": "success",
            "filter": status_filter,
            "count": len(filtered),
            "shipments": filtered
        }), 200

    return jsonify({
        "status": "success",
        "filter": "all",
        "count": len(SHIPMENTS),
        "shipments": SHIPMENTS
    }), 200


from backend.risk_service import calculate_risk_score

@app.route("/api/disruptions", methods=["GET"])
def get_disruptions():
    """
    Return current priority disruption records from database,
    enriched with dynamic risk scores (0-100) and top contributing factors.
    """
    try:
        records = DisruptionModel.query.all()
        disruptions = [r.to_dict() for r in records] if records else [d.copy() for d in DISRUPTIONS]

        # Enrich each disruption with dynamic risk scoring
        for d in disruptions:
            shipment_id = d.get("affected_shipment")
            shipment = get_shipment_by_id(shipment_id) if shipment_id else {}
            sku = shipment.get("sku") if shipment else None
            inv = get_inventory_by_sku(sku) if sku else {}
            alt_sup = get_alternative_suppliers_for_sku(sku) if sku else []
            alt_log = get_alternative_logistics_for_shipment(shipment_id) if shipment_id else []

            score_data = calculate_risk_score(
                shipment=shipment,
                inventory=inv,
                disruptions=[d],
                alt_suppliers=alt_sup,
                alt_logistics=alt_log
            )
            d["risk_score"] = score_data["risk_score"]
            d["calculated_severity"] = score_data["classification"]
            d["days_to_stockout"] = score_data["days_to_stockout"]
            d["revenue_at_risk_usd"] = score_data["revenue_at_risk_usd"]
            d["top_contributing_factors"] = score_data["top_contributing_factors"]
            d["scoring_formula"] = score_data["formula_documentation"]

        # Sort disruptions dynamically by descending risk score
        disruptions.sort(key=lambda x: float(x.get("risk_score") or 0.0), reverse=True)

        return jsonify({
            "status": "success",
            "count": len(disruptions),
            "disruptions": disruptions
        }), 200
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve disruptions: {str(exc)}"
        }), 500


@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    """Return current inventory health records."""
    return jsonify({
        "status": "success",
        "count": len(INVENTORY),
        "inventory": INVENTORY
    }), 200


@app.route("/api/analyze-disruption", methods=["POST"])
def analyze_disruption():
    """
    Phase 2 & 3 Multi-Agent Endpoint with SQLite Persistence:
    Receives shipment_id, coordinates multi-agent LangGraph investigation,
    persists analysis run and recovery plan to SQLite, logs audit events,
    and returns a structured recovery synthesis.
    """
    try:
        payload = request.get_json(silent=True)
        if not payload:
            return jsonify({
                "status": "error",
                "message": "Invalid JSON body. Expected {'shipment_id': 'SH-101'}."
            }), 400

        shipment_id = payload.get("shipment_id")
        if not shipment_id or not str(shipment_id).strip():
            return jsonify({
                "status": "error",
                "message": "Missing required field: 'shipment_id'."
            }), 400

        shipment_id = str(shipment_id).strip().upper()

        # Retrieve shipment record
        shipment = get_shipment_by_id(shipment_id)
        if not shipment:
            return jsonify({
                "status": "error",
                "message": f"Shipment with ID '{shipment_id}' was not found in active records."
            }), 404

        # Retrieve contextual records
        sku = shipment.get("sku", "")
        inventory = get_inventory_by_sku(sku)
        disruptions = get_disruptions_for_shipment(shipment["id"])
        alt_suppliers = get_alternative_suppliers_for_sku(sku)
        alt_logistics = get_alternative_logistics_for_shipment(shipment["id"])

        # Execute LangGraph Multi-Agent Orchestration
        result = run_orchestration(
            shipment=shipment,
            inventory=inventory,
            disruptions=disruptions,
            alternative_suppliers=alt_suppliers,
            alternative_logistics=alt_logistics
        )

        # -------------------------------------------------------------
        # Phase 3: Persist Analysis Run and Recovery Plan to Database
        # -------------------------------------------------------------
        associated_disruption_id = disruptions[0]["id"] if disruptions else None

        # 1. Save Analysis Run
        analysis_run = AnalysisRunModel(
            shipment_id=shipment_id,
            disruption_id=associated_disruption_id,
            product=shipment.get("product"),
            severity=result.get("severity", "Medium"),
            execution_mode=result.get("execution_mode", "deterministic_mock"),
            executive_summary=result.get("executive_summary"),
            agent_findings_json=json.dumps(result.get("agent_findings", {})),
            llm_metadata_json=json.dumps(result.get("llm_metadata", {}))
        )
        db.session.add(analysis_run)
        db.session.flush()

        # 2. Check if a recovery plan already exists for this shipment
        plan_id = f"PLAN-{shipment_id}"
        existing_plan = RecoveryPlanModel.query.filter_by(id=plan_id).first()

        prev_plan_status = None
        if existing_plan:
            plan = existing_plan
            prev_plan_status = plan.status
            plan.analysis_run_id = analysis_run.id
            plan.severity = result.get("severity", "Medium")
            plan.recommended_plan = result.get("recommended_plan")
            plan.status = "Proposed"
            plan.risk_score = result.get("risk_score", 0.0)
            plan.risk_assessment_json = json.dumps(result.get("risk_assessment", {}))
            plan.recommendation_intelligence_json = json.dumps(result.get("recommendation_intelligence", {}))
            plan.assumptions_json = json.dumps(result.get("assumptions", []))
            plan.updated_at = datetime.utcnow()
            # Clear old unapproved options on re-analysis
            for old_opt in plan.options:
                db.session.delete(old_opt)
            db.session.flush()
        else:
            plan = RecoveryPlanModel(
                id=plan_id,
                analysis_run_id=analysis_run.id,
                disruption_id=associated_disruption_id,
                shipment_id=shipment_id,
                product=shipment.get("product"),
                severity=result.get("severity", "Medium"),
                recommended_plan=result.get("recommended_plan"),
                status="Proposed",
                risk_score=result.get("risk_score", 0.0),
                risk_assessment_json=json.dumps(result.get("risk_assessment", {})),
                recommendation_intelligence_json=json.dumps(result.get("recommendation_intelligence", {})),
                assumptions_json=json.dumps(result.get("assumptions", []))
            )
            db.session.add(plan)
            db.session.flush()

        # 3. Create Option Records with Phase 5 Business Impact Fields
        persisted_options = []
        for opt in result.get("recovery_options", []):
            rec_opt = RecoveryOptionModel(
                recovery_plan_id=plan.id,
                option_id=opt.get("option_id", "OPT-1"),
                name=opt.get("name", "Mitigation Option"),
                option_type=opt.get("type", "Standard"),
                action=opt.get("action", ""),
                indicative_cost_usd=float(opt.get("indicative_cost_usd", 0.0)),
                expected_time_to_resolve_days=int(opt.get("expected_time_to_resolve_days", 1)),
                feasibility=opt.get("feasibility", "Medium"),
                risk_mitigation=opt.get("risk_mitigation", ""),
                shortage_reduction_units=float(opt.get("shortage_reduction_units", 0.0)),
                avoided_revenue_loss_usd=float(opt.get("avoided_revenue_loss_usd", 0.0)),
                net_indicative_benefit_usd=float(opt.get("net_indicative_benefit_usd", 0.0)),
                residual_risk=opt.get("residual_risk", "Medium"),
                tradeoff_summary=opt.get("tradeoff_summary", ""),
                status="Proposed"
            )
            db.session.add(rec_opt)
            persisted_options.append(rec_opt)

        db.session.commit()

        # 4. Log Audit Trail Events (Phase 4 & 5 enhanced)
        log_audit_event(
            event_type="DISRUPTION_ANALYSIS_CREATED",
            shipment_id=shipment_id,
            disruption_id=associated_disruption_id,
            plan_id=plan.id,
            actor_type="AI Agent",
            actor_name=f"LangGraph Orchestrator ({result.get('execution_mode')})",
            description=f"Multi-agent investigation completed for {shipment_id} ({shipment.get('product')}). Severity assigned: {result.get('severity')}.",
            outcome="SUCCESS",
            details={
                "severity": result.get("severity"),
                "product": shipment.get("product"),
                "execution_mode": result.get("execution_mode"),
                "options_count": len(persisted_options)
            }
        )

        log_audit_event(
            event_type="DISRUPTION_ANALYSIS_COMPLETED",
            shipment_id=shipment_id,
            disruption_id=associated_disruption_id,
            plan_id=plan.id,
            actor_type="AI Agent",
            actor_name=f"LangGraph Orchestrator ({result.get('execution_mode')})",
            description=f"Multi-agent investigation completed for {shipment_id} ({shipment.get('product')}). Severity assigned: {result.get('severity')}.",
            outcome="SUCCESS",
            details={
                "severity": result.get("severity"),
                "product": shipment.get("product"),
                "execution_mode": result.get("execution_mode"),
                "options_count": len(persisted_options)
            }
        )

        log_audit_event(
            event_type="RECOVERY_PLAN_CREATED",
            shipment_id=shipment_id,
            disruption_id=associated_disruption_id,
            plan_id=plan.id,
            actor_type="AI Agent",
            actor_name="Impact Analysis Agent",
            description=f"Formulated mitigation plan {plan.id} with {len(persisted_options)} recovery option(s). Primary recommendation: {plan.recommended_plan}.",
            previous_status=prev_plan_status,
            new_status="Proposed",
            outcome="SUCCESS",
            details={
                "recommended_plan": plan.recommended_plan,
                "options_count": len(persisted_options)
            }
        )

        # Enhance response with database plan metadata
        result["plan_id"] = plan.id
        result["plan_status"] = plan.status
        result["recovery_options"] = [opt.to_dict() for opt in plan.options]

        return jsonify(result), 200

    except Exception as exc:
        db.session.rollback()
        # Log failure audit event in Phase 4
        log_audit_event(
            event_type="ANALYSIS_FAILED",
            shipment_id=locals().get("shipment_id"),
            actor_type="System",
            actor_name="LangGraph Pipeline",
            description=f"Multi-agent investigation failed for shipment: {str(exc)}",
            outcome="FAILED",
            details={"error": str(exc)}
        )
        return jsonify({
            "status": "error",
            "message": f"Multi-agent investigation pipeline encountered an error: {str(exc)}"
        }), 500


# -------------------------------------------------------------------------
# Phase 3: Recovery Plan Management & Human Approval Endpoints
# -------------------------------------------------------------------------

@app.route("/api/recovery-plans", methods=["GET"])
def get_recovery_plans():
    """Retrieve all persisted recovery plans or filter by shipment_id."""
    try:
        shipment_id = request.args.get("shipment_id")
        query = RecoveryPlanModel.query
        if shipment_id and shipment_id.strip():
            query = query.filter_by(shipment_id=shipment_id.strip().upper())

        plans = query.order_by(RecoveryPlanModel.created_at.desc()).all()
        return jsonify({
            "status": "success",
            "count": len(plans),
            "recovery_plans": [p.to_dict() for p in plans]
        }), 200
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve recovery plans: {str(exc)}"
        }), 500


@app.route("/api/recovery-plans/<plan_id>", methods=["GET"])
def get_recovery_plan(plan_id):
    """Retrieve a single recovery plan and its associated options by plan_id."""
    try:
        plan = RecoveryPlanModel.query.filter_by(id=plan_id.strip().upper()).first()
        if not plan:
            return jsonify({
                "status": "error",
                "message": f"Recovery plan with ID '{plan_id}' was not found."
            }), 404

        return jsonify({
            "status": "success",
            "recovery_plan": plan.to_dict()
        }), 200
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve recovery plan: {str(exc)}"
        }), 500


@app.route("/api/recovery-options/<int:option_id>/decision", methods=["POST"])
def decide_recovery_option(option_id):
    """
    Human-in-the-Loop Approval Decision:
    Approve or reject a proposed recovery option.
    Payload: {"decision": "Approved" | "Rejected", "reason": "optional note", "decided_by": "Operator Name"}
    """
    try:
        payload = request.get_json(silent=True) or {}
        decision = payload.get("decision", "").strip().capitalize()
        reason = payload.get("reason", "").strip()
        decided_by = payload.get("decided_by", "").strip() or "Simulated Operator (Supply Chain Director)"

        if decision not in ("Approved", "Rejected"):
            return jsonify({
                "status": "error",
                "message": "Invalid decision. Must be 'Approved' or 'Rejected'."
            }), 400

        # Retrieve target recovery option
        option = RecoveryOptionModel.query.get(option_id)
        if not option:
            return jsonify({
                "status": "error",
                "message": f"Recovery option #{option_id} was not found."
            }), 404

        # Validate state transition: Cannot re-approve an already simulated or completed option
        if option.status in ("Simulated", "Completed"):
            return jsonify({
                "status": "error",
                "message": f"Cannot alter decision for option #{option_id} because its current status is '{option.status}'."
            }), 400

        prev_option_status = option.status

        # Record approval decision
        approval = ApprovalDecisionModel(
            recovery_option_id=option.id,
            decision=decision,
            decided_by=decided_by,
            reason=reason or f"Operator decision submitted via Command Center portal."
        )
        db.session.add(approval)

        # Update option status
        option.status = decision
        option.updated_at = datetime.utcnow()

        # Update overall plan status
        plan = option.recovery_plan
        prev_plan_status = plan.status
        if decision == "Approved":
            plan.status = "Approved"
        elif all(opt.status == "Rejected" for opt in plan.options):
            plan.status = "Rejected"
        else:
            plan.status = "Pending Approval"
        plan.updated_at = datetime.utcnow()

        db.session.commit()

        # Log audit trail event
        event_name = "OPTION_APPROVED" if decision == "Approved" else "OPTION_REJECTED"
        log_audit_event(
            event_type=event_name,
            shipment_id=plan.shipment_id,
            disruption_id=plan.disruption_id,
            plan_id=plan.id,
            actor_type="Human Operator",
            actor_name=decided_by,
            description=f"Human operator {decision.lower()} recovery option {option.option_id} ('{option.name}') with cost ${option.indicative_cost_usd:,.2f}. Reason: {reason or 'Standard sign-off'}.",
            previous_status=prev_option_status,
            new_status=decision,
            outcome="SUCCESS",
            details={
                "option_id": option.option_id,
                "option_name": option.name,
                "indicative_cost_usd": option.indicative_cost_usd,
                "plan_status": plan.status,
                "reason": reason or "Standard sign-off"
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Option #{option.id} successfully marked as {decision}.",
            "recovery_option": option.to_dict(),
            "plan_status": plan.status
        }), 200

    except Exception as exc:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Failed to record approval decision: {str(exc)}"
        }), 500


@app.route("/api/recovery-options/<int:option_id>/simulate", methods=["POST"])
def simulate_recovery_option(option_id):
    """
    Safe Action Simulation Endpoint:
    Simulates execution of an approved recovery playbook without executing real transactions.
    Rules:
    - Option MUST have status == 'Approved'.
    - Options with status 'Proposed', 'Rejected', or 'Pending Approval' cannot be simulated.
    - Idempotent: repeated simulation of an already 'Simulated' option returns validation message.
    """
    try:
        option = RecoveryOptionModel.query.get(option_id)
        if not option:
            return jsonify({
                "status": "error",
                "message": f"Recovery option #{option_id} was not found."
            }), 404

        # Validate state transition: Must be Approved
        if option.status == "Simulated":
            return jsonify({
                "status": "error",
                "message": f"Recovery option #{option_id} has already been simulated."
            }), 400

        if option.status != "Approved":
            return jsonify({
                "status": "error",
                "message": f"Action simulation requires human approval first. Current status is '{option.status}'. Please approve the option before simulating execution."
            }), 400

        # Execute safe simulation transition
        prev_option_status = option.status
        option.status = "Simulated"
        option.updated_at = datetime.utcnow()

        plan = option.recovery_plan
        prev_plan_status = plan.status
        plan.status = "Simulated"
        plan.updated_at = datetime.utcnow()

        db.session.commit()

        # Log audit trail event
        log_audit_event(
            event_type="ACTION_SIMULATION_EXECUTED",
            shipment_id=plan.shipment_id,
            disruption_id=plan.disruption_id,
            plan_id=plan.id,
            actor_type="System / Simulation Sandbox",
            actor_name="Recovery Dispatch Simulator",
            description=f"Simulated execution of playbook {option.option_id} ('{option.name}'). Indicative budget allocated: ${option.indicative_cost_usd:,.2f}. Turnaround: {option.expected_time_to_resolve_days} day(s). Zero real external transactions placed.",
            previous_status=prev_option_status,
            new_status="Simulated",
            outcome="SUCCESS",
            details={
                "option_id": option.option_id,
                "option_name": option.name,
                "indicative_cost_usd": option.indicative_cost_usd,
                "expected_turnaround_days": option.expected_time_to_resolve_days,
                "execution_sandbox": True
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Simulation executed successfully for option #{option_id} ('{option.name}').",
            "recovery_option": option.to_dict(),
            "plan_status": plan.status,
            "simulation_notice": "Action simulated safely in sandbox. No live purchase orders or carrier bookings were placed."
        }), 200

    except Exception as exc:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Simulation failed: {str(exc)}"
        }), 500


@app.route("/api/recovery-plans/<plan_id>/status", methods=["POST", "PATCH"])
def update_recovery_plan_status(plan_id):
    """
    Update the lifecycle status of a recovery plan.
    Supported statuses: Proposed, Pending Approval, Approved, Rejected, Simulated, In Progress, Completed, Cancelled
    """
    valid_statuses = {
        "Proposed", "Pending Approval", "Approved", "Rejected",
        "Simulated", "In Progress", "Completed", "Cancelled"
    }
    try:
        payload = request.get_json(silent=True) or {}
        new_status = payload.get("status", "").strip()
        reason = payload.get("reason", "").strip()
        actor = payload.get("actor", "").strip() or "Operations Supervisor"

        # Check case-insensitive match against valid statuses
        matched_status = next((s for s in valid_statuses if s.lower() == new_status.lower()), None)
        if not matched_status:
            return jsonify({
                "status": "error",
                "message": f"Invalid status '{new_status}'. Allowed statuses: {sorted(list(valid_statuses))}"
            }), 400

        plan = RecoveryPlanModel.query.filter_by(id=plan_id.strip().upper()).first()
        if not plan:
            return jsonify({
                "status": "error",
                "message": f"Recovery plan with ID '{plan_id}' was not found."
            }), 404

        previous_status = plan.status
        plan.status = matched_status
        plan.updated_at = datetime.utcnow()
        db.session.commit()

        # Log audit trail event
        log_audit_event(
            event_type="PLAN_STATUS_CHANGED",
            shipment_id=plan.shipment_id,
            disruption_id=plan.disruption_id,
            plan_id=plan.id,
            actor_type="Human Operator",
            actor_name=actor,
            description=f"Recovery plan {plan.id} status transitioned from '{previous_status}' to '{matched_status}'. Note: {reason or 'Manual status update'}.",
            previous_status=previous_status,
            new_status=matched_status,
            outcome="SUCCESS",
            details={
                "reason": reason or "Manual status update",
                "actor": actor
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Plan {plan.id} status updated to '{matched_status}'.",
            "recovery_plan": plan.to_dict()
        }), 200

    except Exception as exc:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"Failed to update recovery plan status: {str(exc)}"
        }), 500


@app.route("/api/audit-events", methods=["GET"])
def get_audit_events():
    """
    Retrieve audit events with filtering, full-text search, and pagination.
    Query Params:
      - page: int (default 1)
      - limit: int (default 20, max 100)
      - event_type: string
      - shipment_id: string
      - disruption_id: string
      - search: string
      - start_date: ISO date string
      - end_date: ISO date string
    """
    try:
        page = max(1, request.args.get("page", default=1, type=int))
        limit = min(100, max(1, request.args.get("limit", default=20, type=int)))
        event_type = request.args.get("event_type", "").strip()
        shipment_id = request.args.get("shipment_id", "").strip().upper()
        disruption_id = request.args.get("disruption_id", "").strip().upper()
        search = request.args.get("search", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()

        query = AuditEventModel.query

        if event_type:
            query = query.filter(AuditEventModel.event_type == event_type)

        if shipment_id:
            query = query.filter(AuditEventModel.associated_shipment == shipment_id)

        if disruption_id:
            query = query.filter(AuditEventModel.associated_disruption == disruption_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    AuditEventModel.description.ilike(search_pattern),
                    AuditEventModel.actor_name.ilike(search_pattern),
                    AuditEventModel.associated_shipment.ilike(search_pattern),
                    AuditEventModel.associated_plan.ilike(search_pattern),
                    AuditEventModel.details_json.ilike(search_pattern)
                )
            )

        if start_date:
            try:
                dt_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query = query.filter(AuditEventModel.timestamp >= dt_start)
            except Exception:
                pass

        if end_date:
            try:
                dt_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query = query.filter(AuditEventModel.timestamp <= dt_end)
            except Exception:
                pass

        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
        offset = (page - 1) * limit

        events = query.order_by(AuditEventModel.timestamp.desc()).offset(offset).limit(limit).all()

        return jsonify({
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total_count,
            "pages": total_pages,
            "count": len(events),
            "audit_events": [e.to_dict() for e in events]
        }), 200

    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve audit events: {str(exc)}"
        }), 500


@app.route("/api/audit-events/<int:event_id>", methods=["GET"])
def get_audit_event_detail(event_id):
    """Retrieve full detail for a single audit event."""
    try:
        event = AuditEventModel.query.get(event_id)
        if not event:
            return jsonify({
                "status": "error",
                "message": f"Audit event #{event_id} was not found."
            }), 404

        return jsonify({
            "status": "success",
            "audit_event": event.to_dict()
        }), 200

    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve audit event #{event_id}: {str(exc)}"
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 routes gracefully."""
    if request.path.startswith("/api/"):
        return jsonify({
            "status": "error",
            "message": f"API endpoint '{request.path}' was not found."
        }), 404
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.errorhandler(500)
def server_error(error):
    """Handle 500 internal errors."""
    return jsonify({
        "status": "error",
        "message": "Internal server error."
    }), 500


# Initialize SQLite tables and seed data upon module load
initialize_database()

if __name__ == "__main__":
    # Standard local development runner for Phase 1, 2, & 3
    app.run(host="127.0.0.1", port=5000, debug=True)
