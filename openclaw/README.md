# OpenClaw Agents

OpenClaw agents implement public-source extraction only:
- business websites
- public directories
- public listing text

No private inventory, transaction logs, or behavior data is ingested.

## Run

```bash
python run_openclaw.py
```

This executes:
- fetch + extract text from configured public sources
- embedding generation
- ontology capability mapping
- upsert into PostgreSQL/pgvector
