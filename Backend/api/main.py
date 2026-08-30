from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.commerce import router as commerce_router
from api.routes.webhook import router as webhook_router
from api.routes.chat import router as chat_router

app = FastAPI(
    title="AgentCommerce OS",
    description="AI-powered Agentic Commerce Platform",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTES
# ============================================================

app.include_router(
    commerce_router,
    prefix="/commerce",
    tags=["Commerce"],
)

app.include_router(
    webhook_router,
    prefix="/webhooks",
    tags=["Webhooks"],
)

app.include_router(
    chat_router,
    prefix="/commerce",
    tags=["Chat"],
)

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "AgentCommerce OS",
        "message": "API is running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "AgentCommerce OS",
    }