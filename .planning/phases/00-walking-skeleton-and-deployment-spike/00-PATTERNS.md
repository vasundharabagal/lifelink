# Phase 0: Walking skeleton and deployment spike - Patterns

**Phase:** 0 - Walking skeleton and deployment spike  
**Status:** Canonical architectural patterns for greenfield initialization

## Greenfield Architectural Foundation

This phase establishes the foundational codebase patterns that all subsequent phases will build upon.

### 1. Monorepo Structure & Separation of Concerns

```
/
├── apps/
│   └── web/                   # Vite 6 + React 19 + TypeScript + Tailwind CSS
├── backend/
│   ├── app/
│   │   ├── api/v1/            # Versioned API routes
│   │   ├── core/              # Config, DB engine, security, error envelopes
│   │   └── main.py            # FastAPI application factory and middleware
│   ├── tests/                 # Pytest test suite
│   └── requirements.txt
├── api/
│   └── index.py               # Vercel Serverless Function entrypoint
├── docs/                      # Architectural specifications and ADRs
├── docker-compose.yml         # Local containerized infrastructure
├── package.json               # Root monorepo scripts
└── vercel.json                # Production deployment and routing rewrites
```

### 2. FastAPI Error Envelope Pattern

All endpoints (including error conditions) must conform to the unified error envelope defined in Section 4.4 of `docs/LIFELINK_MASTER_SPEC.md`:

```python
from pydantic import BaseModel
from typing import Any, Dict, Optional

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

### 3. Environment-Aware Database Engine Pattern

`backend/app/core/db.py` must dynamically select connection pooling based on execution environment:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from app.core.config import settings

if settings.APP_ENV in ("production", "preview"):
    # Serverless Vercel function: disable persistent pooling
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={"connect_timeout": 5}
    )
else:
    # Local development: retain standard connection pool
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 4. Health Check Response Contract

`GET /api/v1/health` response schema:

```python
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str       # "ok" | "error"
    db: str           # "ok" | "error"
    version: str      # "1.0"
    demo_mode: bool   # from settings.DEMO_MODE_ENABLED
```

### 5. Client Polling Pattern (`apps/web/src/lib/usePolling.ts`)

```typescript
import { useEffect, useRef, useState } from 'react';

interface PollingOptions<T> {
  intervalMs: number;
  stopWhen?: (data: T) => boolean;
}

export function usePolling<T>(fetcher: () => Promise<T>, options: PollingOptions<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [pollCount, setPollCount] = useState(0);

  // Poll loop implementation with exponential backoff on failure
}
```

### 6. Vercel Serverless ASGI Entrypoint (`api/index.py`)

```python
import sys
import os

# Add backend directory to sys.path for serverless resolution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # ASGI entrypoint
```
