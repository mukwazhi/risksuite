Run the purge script to permanently remove AssessmentDecision records and related ActivityLog entries.

1. Backup the SQLite DB:

```powershell
copy db.sqlite3 db.sqlite3.bak
```

2. Run the SQL script using sqlite3 (Windows):

```powershell
sqlite3 db.sqlite3 < scripts/delete_assessment_decisions.sql
```

If you use PostgreSQL or MySQL, adapt the SQL accordingly and ensure you run it after creating a code migration that removes the `AssessmentDecision` model.

Note: Deleting audit history is destructive. Keep a backup and ensure compliance with your governance policies before proceeding.
