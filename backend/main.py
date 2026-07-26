import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from .routers import market_data, dos
except ImportError:
    from routers import market_data, dos

app = FastAPI(title="AlgoLabs F&O API")

# Scoped CORS origins per security spec
raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
if raw_origins:
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
else:
    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3002",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3002",
        "https://algolabs-fno.vercel.app",
    ]

    frontend_env = os.environ.get("FRONTEND_URL", "").strip()
    if frontend_env:
        origins.append(frontend_env)

# Enable CORS middleware with scoped origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include Routers
app.include_router(market_data.router)
app.include_router(dos.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
