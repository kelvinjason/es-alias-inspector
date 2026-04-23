from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import asyncio

app = FastAPI(title="ES Alias Inspector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class HeaderPair(BaseModel):
    key: str = ""
    value: str = ""


class EnvConfig(BaseModel):
    url: str
    header1: Optional[HeaderPair] = None
    header2: Optional[HeaderPair] = None


class InspectRequest(BaseModel):
    env1: Optional[EnvConfig] = None
    env2: Optional[EnvConfig] = None
    aliases: list[str]
    date: str


def build_headers(cfg: EnvConfig) -> dict:
    headers = {"Content-Type": "application/json"}
    for pair in [cfg.header1, cfg.header2]:
        if pair and pair.key.strip():
            headers[pair.key.strip()] = (pair.value or "").strip()
    return headers


async def query_env(cfg: EnvConfig, base_name: str, expected_index: str) -> dict:
    if not cfg or not cfg.url:
        return {"skipped": True}

    base = cfg.url.rstrip("/")
    headers = build_headers(cfg)
    result = {
        "skipped": False,
        "error": None,
        "index_exists": False,
        "doc_count": 0,
        "actual_index": None,
        "alias_ok": False,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            r1 = await client.get(f"{base}/{expected_index}/_count", headers=headers)
            if r1.status_code == 200:
                result["index_exists"] = True
                result["doc_count"] = r1.json().get("count", 0)
            elif r1.status_code in (401, 403):
                result["error"] = f"Auth failed (HTTP {r1.status_code})"
                return result
            elif r1.status_code != 404:
                result["error"] = f"HTTP {r1.status_code}"
                return result

            r2 = await client.get(f"{base}/_alias/{base_name}", headers=headers)
            if r2.status_code == 200:
                keys = list(r2.json().keys())
                if keys:
                    result["actual_index"] = keys[0]
                    result["alias_ok"] = keys[0] == expected_index

    except httpx.ConnectError:
        result["error"] = "Connection failed (unreachable)"
    except httpx.TimeoutException:
        result["error"] = "Request timed out"
    except Exception as e:
        result["error"] = str(e)

    return result


@app.post("/api/inspect")
async def inspect(req: InspectRequest):
    results = []
    for alias in req.aliases:
        alias = alias.strip()
        if not alias:
            continue
        expected = f"{alias}_{req.date}"
        r1, r2 = await asyncio.gather(
            query_env(req.env1, alias, expected) if req.env1 else asyncio.sleep(0, result={"skipped": True}),
            query_env(req.env2, alias, expected) if req.env2 else asyncio.sleep(0, result={"skipped": True}),
        )
        results.append({
            "alias": alias,
            "expected_index": expected,
            "env1": r1,
            "env2": r2,
        })
    return {"results": results}


@app.get("/health")
def health():
    return {"status": "ok"}


frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
