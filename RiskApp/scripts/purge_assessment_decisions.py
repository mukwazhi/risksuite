"""
Run this script from the project root to permanently purge AssessmentDecision records
and related ActivityLog entries. Make sure you have a DB backup (db.sqlite3.bak).
"""
import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'db.sqlite3'))
print('Using DB:', DB_PATH)
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Delete ActivityLog entries with action prefix used for assessment decisions
print('Deleting ActivityLog entries where action LIKE "assessment_decision%"...')
cur.execute("DELETE FROM riskregister_activitylog WHERE action LIKE 'assessment_decision%';")
print('Deleted', cur.rowcount, 'rows')

# Try to delete ActivityLog entries referencing decision_id in JSON context
try:
    print('Attempting JSON_EXTRACT-based deletion (if supported)...')
    cur.execute("DELETE FROM riskregister_activitylog WHERE JSON_EXTRACT(context, '$.decision_id') IS NOT NULL;")
    print('Deleted', cur.rowcount, 'rows')
except Exception as e:
    print('JSON_EXTRACT deletion skipped or failed:', e)

# Delete AssessmentDecision records (if table exists)
try:
    print('Deleting AssessmentDecision records...')
    cur.execute('DELETE FROM riskregister_assessmentdecision;')
    print('Deleted', cur.rowcount, 'rows')
except Exception as e:
    print('Deleting assessmentdecision rows failed or table missing:', e)

conn.commit()
conn.close()
print('Purge script completed.')
