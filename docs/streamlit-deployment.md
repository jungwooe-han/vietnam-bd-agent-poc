# Streamlit deployment

The BD analysis history must use a shared PostgreSQL database in hosted environments.
Local SQLite is retained only for local development.

Add these values to Streamlit Community Cloud **Advanced settings → Secrets**:

```toml
OPENAI_API_KEY = "..."
FIRECRAWL_API_KEY = "..."
BD_HISTORY_DATABASE_URL = "postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
```

Before the first deployment, migrate the existing local history:

```powershell
$env:BD_HISTORY_DATABASE_URL = "postgresql://..."
python scripts/migrate_bd_history.py
```

The migration is idempotent: rerunning it skips records that already exist.
