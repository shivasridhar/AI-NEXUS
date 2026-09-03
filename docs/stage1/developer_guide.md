# Stage 1 Developer Guide

This guide covers local environment setup and execution of the SentinelAI Stage 1 system.

## Prerequisites
- Node.js v18+ (Frontend)
- Python 3.12+ (Backend)
- PostgreSQL (Backend DB)
- Neo4j (Graph DB)

## Local Setup

### 1. Backend (`sentinel_backend`)

Navigate to the backend directory and set up the virtual environment:
```bash
cd sentinel_backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file (never commit real secrets!). Safe mock values:
```ini
# .env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sentinel
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
SECRET_KEY=dev_secret_key
ENVIRONMENT=development
```

Run the backend server:
```bash
fastapi dev app/main.py
```
The API will be available at `http://localhost:8000`.

### 2. Frontend (`sentinel_frontend`)

Navigate to the frontend directory:
```bash
cd sentinel_frontend
npm install
```

Create a `.env.local` file:
```ini
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Run the frontend server:
```bash
npm run dev
```
The UI will be available at `http://localhost:3000`.

## Working with Connectors locally
When developing or testing connectors locally, you can use mock APIs (e.g. `json-server`) to simulate the external third-party sources or point to sandbox instances of AWS/Wazuh. Avoid hardcoding test credentials in the code; use the Connector UI in the dashboard to inject configuration parameters.
