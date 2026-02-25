# /weekly-report — Weekly Summary Report

Before running the script, check if the `data/` directory exists. If it does not, inform the user that the data directory needs to be created first (use `/new-task` or create it manually — see `CLAUDE.md` for details).

Run the dashboard script and display its output to the user:

```
python scripts/dashboard.py weekly_report
```

Display the full output as-is — it is already formatted as markdown. Do not summarize or modify it.

The script automatically saves a snapshot to `data/reports/weekly-report/YYYY/MM/YYYY-MM-DD.md` (dated to Monday of the week). Mention the saved file path to the user.

If the output summary shows all zeros, mention that no task activity was recorded this week.
