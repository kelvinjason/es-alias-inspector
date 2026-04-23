# ES Alias Inspector

A lightweight tool to cross-check Elasticsearch alias routing between **PROD** and **PRE-PROD** environments.

## Architecture

```
browser  →  FastAPI (backend/)  →  Elasticsearch
```

The FastAPI backend acts as a proxy — it forwards requests to Elasticsearch server-side, so there are **no CORS issues** regardless of your ES configuration.

## Project Structure

```
├── backend/
│   ├── main.py           # FastAPI app + proxy logic
│   └── requirements.txt
├── frontend/
│   └── index.html        # UI (served by FastAPI)
└── README.md
```

## Quick Start

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Start the server
uvicorn main:app --reload --port 8000

# 3. Open browser
open http://localhost:8000
```

## API

### `POST /api/inspect`

Request body:
```json
{
  "env1": { "url": "http://es-prod:9200", "auth_type": "Bearer", "token": "xxx" },
  "env2": { "url": "http://es-preprod:9200", "auth_type": "None", "token": "" },
  "aliases": ["fa-mvp_all", "fa-efrat_input"],
  "date": "20260424"
}
```

Response:
```json
{
  "results": [
    {
      "alias": "fa-mvp_all",
      "expected_index": "fa-mvp_all_20260424",
      "env1": { "skipped": false, "index_exists": true, "doc_count": 12345, "alias_ok": true, "actual_index": "fa-mvp_all_20260424", "error": null },
      "env2": { "skipped": false, "index_exists": false, "doc_count": 0, "alias_ok": false, "actual_index": null, "error": null }
    }
  ]
}
```

### Auth types supported

| Type | Header sent |
|---|---|
| `Bearer` | `Authorization: Bearer <token>` |
| `ApiKey` | `Authorization: ApiKey <key>` |
| `Basic` | `Authorization: Basic <base64(user:pass)>` |
| `None` | *(no auth header)* |

## Interactive API Docs

Visit `http://localhost:8000/docs` for the Swagger UI.
