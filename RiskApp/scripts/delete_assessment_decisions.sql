-- Backup your database before running this script.
-- This will permanently delete AssessmentDecision records and related ActivityLog entries.
-- Intended for SQLite (db.sqlite3). Adjust syntax for other DB backends as needed.

BEGIN TRANSACTION;

-- Delete ActivityLog entries with action prefix used for assessment decisions
DELETE FROM riskregister_activitylog WHERE action LIKE 'assessment_decision%';

-- Delete ActivityLog entries that reference a decision_id in their JSON context
-- (Requires SQLite JSON1 extension). If your DB does not support JSON_EXTRACT,
-- skip this step or adapt for your DB.
DELETE FROM riskregister_activitylog WHERE JSON_EXTRACT(context, '$.decision_id') IS NOT NULL;

-- Finally delete the AssessmentDecision records
DELETE FROM riskregister_assessmentdecision;

COMMIT;
