# ---- stage 1: build the React frontend ----
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# ---- stage 2: python backend serving the built frontend ----
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY api.py run_pipeline.py ./
COPY database/raw/ ./database/raw/
COPY --from=web /web/dist ./web/dist

# Build the harmonised data into the image so the container starts ready.
# --offline keeps the committed raw feeds and skips live API calls at build time.
RUN git clone --depth 1 --filter=blob:none --sparse \
      https://github.com/cdisc-org/sdtm-adam-pilot-project.git database/cdisc \
 && cd database/cdisc \
 && git sparse-checkout set "updated-pilot-submission-package/900172/m5/datasets/cdiscpilot01/tabulations/sdtm" \
 && cd /app \
 && python run_pipeline.py --offline \
 && rm -rf database/cdisc \
 || python run_pipeline.py --synthetic
 
ENV PORT=8080
EXPOSE 8080
CMD exec uvicorn api:app --host 0.0.0.0 --port ${PORT}
