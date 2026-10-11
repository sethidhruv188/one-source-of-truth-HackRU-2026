# Deploying

One container. React is built to static files and served by FastAPI, so there is
a single service, a single URL, and no cross-origin request in production.

## Google Cloud Run

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

gcloud run deploy one-source-of-truth \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars "GEMINI_API_KEY=your_key"
```

The build takes a few minutes: it installs npm packages, builds the frontend,
installs Python packages, and runs the pipeline so the image ships with the
harmonised data already in it. The URL is printed at the end.

### With Tiger Data instead of files

```bash
gcloud run deploy one-source-of-truth \
  --source . --region us-east1 --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=your_key,OST_STORE=postgres,DATABASE_URL=postgres://..."
```

## Local container test

```bash
docker build -t ost .
docker run -p 8080:8080 -e GEMINI_API_KEY=your_key ost
# open http://localhost:8080
```

## Tiger Data setup

1. Create a free service at console.cloud.timescale.com and copy the connection string.
2. `pip install "psycopg[binary]" sqlalchemy`
3. ```bash
   export DATABASE_URL="postgres://tsdbadmin:...@....tsdb.cloud.timescale.com:PORT/tsdb?sslmode=require"
   python3 run_pipeline.py
   python3 -m backend.pipeline.load_to_tiger
   ```
4. Run the app against it:
   ```bash
   export OST_STORE=postgres
   uvicorn api:app --reload --port 8000
   ```

`OST_STORE=files` (the default) reads the pipeline output directly.
`OST_STORE=postgres` reads the same tables from Tiger Data. Only
`backend/core/repository.py` knows the difference — the service layer, the API
and the frontend are identical either way.
