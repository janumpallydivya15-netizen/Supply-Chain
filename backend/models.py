"""
Supply Chain Disruption Command Center - Database Models
Phase 3 & Phase 4: Persistent Database, Recovery Plan Management, Human Approval, and Advanced Audit Trail
"""

import json
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def get_utc_now():
    """Return timezone-aware or standard UTC datetime."""
    return datetime.now(timezone.utc)


class DisruptionModel(db.Model):
    """Persisted Disruption Incidents."""
    __tablename__ = "disruptions"

    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    disruption_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(32), nullable=False)
    affected_item = db.Column(db.String(255), nullable=False)
    affected_shipment = db.Column(db.String(64), nullable=True, index=True)
    facility = db.Column(db.String(128), nullable=True)
    reported_date = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=True)
    impact_summary = db.Column(db.Text, nullable=True)
    future_agent_task = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now)

    # Relationships
    analysis_runs = db.relationship("AnalysisRunModel", backref="disruption", lazy=True, cascade="all, delete-orphan")
    recovery_plans = db.relationship("RecoveryPlanModel", backref="disruption", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "type": self.disruption_type,
            "severity": self.severity,
            "affected_item": self.affected_item,
            "affected_shipment": self.affected_shipment,
            "facility": self.facility,
            "reported_date": self.reported_date,
            "description": self.description,
            "impact_summary": self.impact_summary,
            "future_agent_task": self.future_agent_task,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AnalysisRunModel(db.Model):
    """Persisted Multi-Agent Analysis Runs."""
    __tablename__ = "analysis_runs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    shipment_id = db.Column(db.String(64), nullable=False, index=True)
    disruption_id = db.Column(db.String(64), db.ForeignKey("disruptions.id"), nullable=True)
    product = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(32), nullable=False)
    execution_mode = db.Column(db.String(64), nullable=False, default="deterministic_mock")
    executive_summary = db.Column(db.Text, nullable=True)
    agent_findings_json = db.Column(db.Text, nullable=True)
    llm_metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now)

    # Relationships
    recovery_plan = db.relationship("RecoveryPlanModel", backref="analysis_run", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "shipment_id": self.shipment_id,
            "disruption_id": self.disruption_id,
            "product": self.product,
            "severity": self.severity,
            "execution_mode": self.execution_mode,
            "executive_summary": self.executive_summary,
            "agent_findings": json.loads(self.agent_findings_json) if self.agent_findings_json else {},
            "llm_metadata": json.loads(self.llm_metadata_json) if self.llm_metadata_json else {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class RecoveryPlanModel(db.Model):
    """Persisted Mitigation Recovery Plans."""
    __tablename__ = "recovery_plans"

    id = db.Column(db.String(64), primary_key=True)  # e.g., PLAN-SH-101
    analysis_run_id = db.Column(db.Integer, db.ForeignKey("analysis_runs.id"), nullable=True)
    disruption_id = db.Column(db.String(64), db.ForeignKey("disruptions.id"), nullable=True)
    shipment_id = db.Column(db.String(64), nullable=False, index=True)
    product = db.Column(db.String(255), nullable=True)
    severity = db.Column(db.String(32), nullable=False)
    recommended_plan = db.Column(db.String(255), nullable=True)
    # Plan Statuses: Proposed, Awaiting Approval, Approved, Rejected, Simulated, Completed, Cancelled
    status = db.Column(db.String(32), nullable=False, default="Proposed")
    assumptions_json = db.Column(db.Text, nullable=True)
    # Phase 5: Risk & Impact intelligence fields
    risk_score = db.Column(db.Float, nullable=True, default=0.0)
    risk_assessment_json = db.Column(db.Text, nullable=True)
    recommendation_intelligence_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    options = db.relationship("RecoveryOptionModel", backref="recovery_plan", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "analysis_run_id": self.analysis_run_id,
            "disruption_id": self.disruption_id,
            "shipment_id": self.shipment_id,
            "product": self.product,
            "severity": self.severity,
            "recommended_plan": self.recommended_plan,
            "status": self.status,
            "risk_score": self.risk_score,
            "risk_assessment": json.loads(self.risk_assessment_json) if self.risk_assessment_json else {},
            "recommendation_intelligence": json.loads(self.recommendation_intelligence_json) if self.recommendation_intelligence_json else {},
            "assumptions": json.loads(self.assumptions_json) if self.assumptions_json else [],
            "options": [opt.to_dict() for opt in self.options],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class RecoveryOptionModel(db.Model):
    """Specific Actionable Options within a Recovery Plan."""
    __tablename__ = "recovery_plan_options"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recovery_plan_id = db.Column(db.String(64), db.ForeignKey("recovery_plans.id"), nullable=False, index=True)
    option_id = db.Column(db.String(32), nullable=False)  # e.g., OPT-1
    name = db.Column(db.String(255), nullable=False)
    option_type = db.Column(db.String(128), nullable=False)
    action = db.Column(db.Text, nullable=False)
    indicative_cost_usd = db.Column(db.Float, nullable=False, default=0.0)
    expected_time_to_resolve_days = db.Column(db.Integer, nullable=False, default=1)
    feasibility = db.Column(db.String(32), nullable=False, default="Medium")
    risk_mitigation = db.Column(db.Text, nullable=True)
    # Phase 5: Business Impact & Comparison Fields
    shortage_reduction_units = db.Column(db.Float, nullable=True, default=0.0)
    avoided_revenue_loss_usd = db.Column(db.Float, nullable=True, default=0.0)
    net_indicative_benefit_usd = db.Column(db.Float, nullable=True, default=0.0)
    residual_risk = db.Column(db.String(32), nullable=True, default="Medium")
    tradeoff_summary = db.Column(db.Text, nullable=True)
    # Statuses: Proposed, Awaiting Approval, Approved, Rejected, Simulated, Completed, Cancelled
    status = db.Column(db.String(32), nullable=False, default="Proposed")
    created_at = db.Column(db.DateTime, default=get_utc_now)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    approval_decisions = db.relationship("ApprovalDecisionModel", backref="recovery_option", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        latest_decision = self.approval_decisions[-1].to_dict() if self.approval_decisions else None
        return {
            "id": self.id,
            "recovery_plan_id": self.recovery_plan_id,
            "option_id": self.option_id,
            "name": self.name,
            "type": self.option_type,
            "action": self.action,
            "indicative_cost_usd": self.indicative_cost_usd,
            "expected_time_to_resolve_days": self.expected_time_to_resolve_days,
            "shortage_reduction_units": self.shortage_reduction_units,
            "avoided_revenue_loss_usd": self.avoided_revenue_loss_usd,
            "net_indicative_benefit_usd": self.net_indicative_benefit_usd,
            "residual_risk": self.residual_risk,
            "tradeoff_summary": self.tradeoff_summary,
            "feasibility": self.feasibility,
            "risk_mitigation": self.risk_mitigation,
            "status": self.status,
            "latest_decision": latest_decision,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ApprovalDecisionModel(db.Model):
    """Human Operator Sign-Off / Rejection Decisions."""
    __tablename__ = "approval_decisions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recovery_option_id = db.Column(db.Integer, db.ForeignKey("recovery_plan_options.id"), nullable=False, index=True)
    decision = db.Column(db.String(32), nullable=False)  # Approved, Rejected, Requested
    decided_by = db.Column(db.String(128), nullable=False, default="Simulated Operator (Supply Chain Director)")
    reason = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=get_utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "recovery_option_id": self.recovery_option_id,
            "decision": self.decision,
            "decided_by": self.decided_by,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


class AuditEventModel(db.Model):
    """
    Immutable Append-Only Audit Trail (Phase 4).
    Stores event metadata, previous/new statuses, structured JSON payloads, and actor details.
    """
    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=get_utc_now, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    associated_shipment = db.Column(db.String(64), nullable=True, index=True)
    associated_disruption = db.Column(db.String(64), nullable=True, index=True)
    associated_plan = db.Column(db.String(64), nullable=True, index=True)
    actor_type = db.Column(db.String(64), nullable=False, default="System / AI Agent")  # AI Agent, Human Operator, System
    actor_name = db.Column(db.String(128), nullable=False, default="Multi-Agent Fleet")
    description = db.Column(db.Text, nullable=False)
    previous_status = db.Column(db.String(64), nullable=True)
    new_status = db.Column(db.String(64), nullable=True)
    outcome = db.Column(db.String(32), nullable=False, default="SUCCESS")  # SUCCESS, FAILED, WARNING
    details_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_type": self.event_type,
            "associated_shipment": self.associated_shipment,
            "associated_disruption": self.associated_disruption,
            "associated_plan": self.associated_plan,
            "actor_type": self.actor_type,
            "actor_name": self.actor_name,
            "description": self.description,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "outcome": self.outcome,
            "details": json.loads(self.details_json) if self.details_json else {}
        }


def log_audit_event(
    event_type: str,
    description: str,
    shipment_id: str = None,
    disruption_id: str = None,
    plan_id: str = None,
    actor_type: str = "System / AI Agent",
    actor_name: str = "Multi-Agent Fleet",
    previous_status: str = None,
    new_status: str = None,
    outcome: str = "SUCCESS",
    details: dict = None
):
    """
    Append an immutable verifiable audit event record to SQLite.
    Never raises an uncaught exception to avoid suppressing original business errors.
    """
    try:
        event = AuditEventModel(
            event_type=event_type,
            associated_shipment=shipment_id,
            associated_disruption=disruption_id,
            associated_plan=plan_id,
            actor_type=actor_type,
            actor_name=actor_name,
            description=description,
            previous_status=previous_status,
            new_status=new_status,
            outcome=outcome,
            details_json=json.dumps(details) if details else None
        )
        db.session.add(event)
        db.session.commit()
        return event
    except Exception as exc:
        db.session.rollback()
        # Fallback print without crash
        print(f"[Audit Log Error] Could not write audit event '{event_type}': {exc}")
        return None
