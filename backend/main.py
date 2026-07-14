from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from .routers import market_data, dos
except ImportError:
    from routers import market_data, dos

app = FastAPI(title="AlgoLabs F&O API")

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
