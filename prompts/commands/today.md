# /today — Daily Dashboard

Run the dashboard script and display its output to the user:

```
python scripts/dashboard.py today
```

Display the full output as-is — it is already formatted as markdown. Do not summarize or modify it.

The script automatically saves a snapshot to `reports/daily/YYYY/YYYY-MM-DD.md`. Mention the saved file path to the user.

If the output shows no tasks at all, mention that the vault has no open tasks yet.
