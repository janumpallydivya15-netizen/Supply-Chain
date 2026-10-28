"""
End-to-End Recovery Workflow Verification Script
Tests:
1. Investigation trigger for SH-101
2. Verification that simulation fails (HTTP 400) when option is unapproved
3. Rejection of option with reason
4. Approval of option with reason
5. Safe sandbox action simulation of approved option
6. Audit trail verification ensuring all actions are logged
"""

import urllib.request
import urllib.error
import json

base = 'http://127.0.0.1:5000'

def post_json(path, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(base + path, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

print('=== 1. RUN INVESTIGATION FOR SH-101 ===')
status, res = post_json('/api/analyze-disruption', {'shipment_id': 'SH-101'})
assert status == 200, f'Analysis failed: {res}'
print('Analysis Success: Plan ID:', res['plan_id'], 'Severity:', res['severity'], 'Options:', len(res['recovery_options']))
options = res['recovery_options']
opt1 = options[0] # OPT-1
opt2 = options[-1] # OPT-2 (or last option)

print('\n=== 2. ATTEMPT SIMULATION BEFORE APPROVAL ===')
status, sim_err = post_json(f"/api/recovery-options/{opt1['id']}/simulate", {})
print('Simulation Status:', status, 'Message:', sim_err.get('message'))
assert status == 400, 'Unapproved simulation should return 400!'

print('\n=== 3. REJECT OPTION 2 WITH REASON ===')
status, rej_res = post_json(f"/api/recovery-options/{opt2['id']}/decision", {
    'decision': 'Rejected',
    'reason': 'Procurement premium exceeds contingency reserve margin',
    'decided_by': 'Supply Chain VP'
})
assert status == 200, f'Rejection failed: {rej_res}'
print('Option 2 Status:', rej_res['recovery_option']['status'])

print('\n=== 4. APPROVE OPTION 1 WITH REASON ===')
status, app_res = post_json(f"/api/recovery-options/{opt1['id']}/decision", {
    'decision': 'Approved',
    'reason': 'Fastest turnaround and highest net financial benefit ($10,390)',
    'decided_by': 'Supply Chain Director'
})
assert status == 200, f'Approval failed: {app_res}'
print('Option 1 Status:', app_res['recovery_option']['status'])

print('\n=== 5. SIMULATE APPROVED OPTION 1 ===')
status, sim_res = post_json(f"/api/recovery-options/{opt1['id']}/simulate", {})
assert status == 200, f'Simulation failed: {sim_res}'
print('Simulation Status:', status, 'New Option Status:', sim_res['recovery_option']['status'])
print('Sandbox notice:', sim_res.get('simulation_notice'))

print('\n=== 6. VERIFY AUDIT LOG TRAIL ===')
with urllib.request.urlopen(base + '/api/audit-events?shipment_id=SH-101&limit=10') as resp:
    audit_data = json.loads(resp.read().decode('utf-8'))
    recent_events = [e['event_type'] for e in audit_data['audit_events']]
    print('Recent Audit Event Types for SH-101:', recent_events[:6])
    assert 'ACTION_SIMULATION_EXECUTED' in recent_events
    assert 'OPTION_APPROVED' in recent_events
    assert 'OPTION_REJECTED' in recent_events
    assert 'RECOVERY_PLAN_CREATED' in recent_events

print('\nALL RECOVERY WORKFLOW TESTS PASSED CLEANLY!')
