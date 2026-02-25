# /this_week — Weekly Dashboard

Before running the script, check if the `data/` directory exists. If it does not, inform the user that the data directory needs to be created first (use `/new-task` or create it manually — see `CLAUDE.md` for details).

Run the dashboard script and display its output to the user:

```
python scripts/dashboard.py this_week
```

Display the full output as-is — it is already formatted as markdown. Do not summarize or modify it.

The script automatically saves a snapshot to `data/reports/weekly/YYYY/YYYY-MM-DD.md` (dated to Monday of the week). Mention the saved file path to the user.

If the output shows no projects, mention that no projects have been created yet.
