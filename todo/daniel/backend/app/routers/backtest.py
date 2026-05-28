from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, HTTPException

from app.backtest import runner, strategies
from app.models.schemas import BacktestRequest, MultiBacktestRequest

router = APIRouter()


@router.get("/strategies")
def list_strategies() -> list[dict]:
    return [
        {"key": m.key, "name": m.name, "description": m.description, "params": m.params}
        for m in strategies.list_strategies()
    ]


@router.post("/run")
def run_backtest(req: BacktestRequest) -> dict:
    try:
        result = runner.run(
            symbol=req.symbol,
            strategy_key=req.strategy,
            params=req.params,
            start=req.start,
            end=req.end,
            init_cash=req.init_cash,
            fees=req.fees,
            slippage=req.slippage,
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


def _run_one_safe(req: MultiBacktestRequest, symbol: str) -> dict:
    try:
        r = runner.run(
            symbol=symbol,
            strategy_key=req.strategy,
            params=req.params,
            start=req.start,
            end=req.end,
            init_cash=req.init_cash,
            fees=req.fees,
            slippage=req.slippage,
        )
        m = r["metrics"]
        return {
            "symbol": symbol,
            "ok": True,
            "total_return": m.get("total_return"),
            "annual_return": m.get("annual_return"),
            "max_drawdown": m.get("max_drawdown"),
            "sharpe": m.get("sharpe"),
            "win_rate": m.get("win_rate"),
            "trades": m.get("trades"),
            "start": r["start"],
            "end": r["end"],
        }
    except Exception as e:
        return {"symbol": symbol, "ok": False, "error": str(e)[:200]}


@router.post("/run-multi")
def run_multi_backtest(req: MultiBacktestRequest) -> dict:
    if not req.symbols:
        raise HTTPException(status_code=400, detail="symbols is empty")
    if len(req.symbols) > 200:
        raise HTTPException(status_code=400, detail="too many symbols (max 200)")

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_run_one_safe, req, s): s for s in req.symbols}
        for fut in as_completed(futures):
            results.append(fut.result())

    ok = [r for r in results if r["ok"]]
    if ok:
        avg_return = sum((r["total_return"] or 0) for r in ok) / len(ok)
        avg_sharpe = sum((r["sharpe"] or 0) for r in ok) / len(ok)
        avg_dd = sum((r["max_drawdown"] or 0) for r in ok) / len(ok)
        wins = sum(1 for r in ok if (r["total_return"] or 0) > 0)
    else:
        avg_return = avg_sharpe = avg_dd = 0.0
        wins = 0

    ok.sort(key=lambda r: (r["total_return"] or 0), reverse=True)
    failed = [r for r in results if not r["ok"]]

    return {
        "strategy": req.strategy,
        "params": req.params,
        "scanned": len(req.symbols),
        "succeeded": len(ok),
        "failed": len(failed),
        "summary": {
            "avg_total_return": round(avg_return, 4),
            "avg_sharpe": round(avg_sharpe, 4),
            "avg_max_drawdown": round(avg_dd, 4),
            "profit_ratio": round(wins / len(ok) * 100, 2) if ok else 0.0,
        },
        "results": ok,
        "failures": failed,
    }
