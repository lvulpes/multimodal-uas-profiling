# data/ (git-ignored)

```
raw/<run_id>/   append-only: manifest.json, net.pcap, phy.parquet, events.jsonl, flight.*
interim/        derived, regenerable
processed/      feature tables and model inputs, regenerable from raw + code
```

Never commit data. Never edit or overwrite a finished run; rerun under a new attempt suffix.
