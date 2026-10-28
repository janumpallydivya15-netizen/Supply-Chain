import sqlite3

conn = sqlite3.connect('instance/supply_chain.db')
cur = conn.cursor()

# Check and add columns to recovery_plans
cur.execute('PRAGMA table_info(recovery_plans)')
cols = [r[1] for r in cur.fetchall()]
if 'risk_score' not in cols:
    cur.execute('ALTER TABLE recovery_plans ADD COLUMN risk_score REAL DEFAULT 0.0')
if 'risk_assessment_json' not in cols:
    cur.execute('ALTER TABLE recovery_plans ADD COLUMN risk_assessment_json TEXT')
if 'recommendation_intelligence_json' not in cols:
    cur.execute('ALTER TABLE recovery_plans ADD COLUMN recommendation_intelligence_json TEXT')

# Check and add columns to recovery_plan_options
cur.execute('PRAGMA table_info(recovery_plan_options)')
opt_cols = [r[1] for r in cur.fetchall()]
if 'shortage_reduction_units' not in opt_cols:
    cur.execute('ALTER TABLE recovery_plan_options ADD COLUMN shortage_reduction_units REAL DEFAULT 0.0')
if 'avoided_revenue_loss_usd' not in opt_cols:
    cur.execute('ALTER TABLE recovery_plan_options ADD COLUMN avoided_revenue_loss_usd REAL DEFAULT 0.0')
if 'net_indicative_benefit_usd' not in opt_cols:
    cur.execute('ALTER TABLE recovery_plan_options ADD COLUMN net_indicative_benefit_usd REAL DEFAULT 0.0')
if 'residual_risk' not in opt_cols:
    cur.execute("ALTER TABLE recovery_plan_options ADD COLUMN residual_risk VARCHAR(32) DEFAULT 'Medium'")
if 'tradeoff_summary' not in opt_cols:
    cur.execute('ALTER TABLE recovery_plan_options ADD COLUMN tradeoff_summary TEXT')

conn.commit()
conn.close()
print("Migration completed successfully.")
