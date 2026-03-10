# /today — Daily Dashboard

Before running the script, check if the `data/` directory exists. If it does not, inform the user that the data directory needs to be created first (use `/new-task` or create it manually — see `CLAUDE.md` for details).

Run the dashboard script and display its output to the user:

```
python scripts/dashboard.py today
```

Display the full output as-is — it is already formatted as markdown. Do not summarize or modify it.

The script automatically saves a snapshot to `data/reports/daily/YYYY/MM/YYYY-MM-DD-daily.md`. Mention the saved file path to the user.

If the output shows no tasks at all, mention that there are no open tasks yet.
