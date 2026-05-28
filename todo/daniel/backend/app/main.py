from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import ai_etf_picks, ai_picks, backtest, etfs, fund_flow, portfolio, predictions, recommend, screener, stocks, strategies, verdict

app = FastAPI(
    title="Stock Simulator API",
    version="0.1.0",
    description="個人用股票模擬與分析平台 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    # 自動把缺名稱的股票補上
    from app.db import SessionLocal
    from app.data import listings

    with SessionLocal() as s:
        listings.enrich_names(s)


app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(screener.router, prefix="/api/screener", tags=["screener"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(recommend.router, prefix="/api/recommend", tags=["recommend"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(fund_flow.router, prefix="/api/fund-flow", tags=["fund-flow"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(etfs.router, prefix="/api/etfs", tags=["etfs"])
app.include_router(verdict.router, prefix="/api/verdict", tags=["verdict"])
app.include_router(ai_picks.router, prefix="/api/ai-picks", tags=["ai-picks"])
app.include_router(ai_etf_picks.router, prefix="/api/ai-etf-picks", tags=["ai-etf-picks"])


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": settings.app_mode}
