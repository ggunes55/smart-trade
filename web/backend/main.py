# -*- coding: utf-8 -*-
"""
Swing Trade Scanner - Web API Backend
FastAPI ile güçlendirilmiş modern backend.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import logging
import sys
import os
import json
import asyncio

# Proje kök dizinini ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from core.utils import load_config
from scanner.data_handler import DataHandler
from scanner.symbol_analyzer import SymbolAnalyzer
from scanner.market_analyzer import MarketAnalyzer
from smart_filter.smart_filter import SmartFilterSystem

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebAPI")

app = FastAPI(title="Swing Trade Scanner API", version="3.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
scanner_system = {
    "cfg": None,
    "data_handler": None,
    "market_analyzer": None,
    "symbol_analyzer": None,
    "smart_filter": None
}

def init_scanner():
    """Scanner bileşenlerini başlat"""
    logger.info("Initializing scanner components...")
    cfg = load_config("swing_config.json")
    data_handler = DataHandler(cfg)
    market_analyzer = MarketAnalyzer(cfg, data_handler)
    
    exchange = cfg.get("exchange", "BIST")
    smart_filter = SmartFilterSystem(cfg, exchange=exchange)
    
    symbol_analyzer = SymbolAnalyzer(cfg, data_handler, market_analyzer, smart_filter)
    
    scanner_system["cfg"] = cfg
    scanner_system["data_handler"] = data_handler
    scanner_system["market_analyzer"] = market_analyzer
    scanner_system["symbol_analyzer"] = symbol_analyzer
    scanner_system["smart_filter"] = smart_filter
    logger.info("Scanner initialized successfully.")

# Başlangıçta inite et
@app.on_event("startup")
async def startup_event():
    init_scanner()

# Models
class ScanRequest(BaseModel):
    symbols: List[str]
    exchange: Optional[str] = "BIST"

class ScanResponse(BaseModel):
    symbol: str
    score: float
    signal: str
    price: float
    details: Dict

# API Endpoints
@app.get("/api/status")
async def get_status():
    """Sistem durumu"""
    if scanner_system["symbol_analyzer"]:
        return {"status": "active", "version": "3.0.0", "message": "System ready"}
    return {"status": "initializing", "message": "Scanner loading..."}

@app.get("/api/scan/{symbol}")
async def scan_symbol(symbol: str):
    """Tekil sembol analizi"""
    analyzer = scanner_system["symbol_analyzer"]
    if not analyzer:
        raise HTTPException(status_code=503, detail="Scanner not initialized")
        
    try:
        # Senkron fonksiyonu asenkron çalıştır
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyzer.analyze_symbol, symbol.upper())
        
        if result:
            return result
        else:
            return {"symbol": symbol, "status": "no_signal", "message": "Signal not found or filtered"}
            
    except Exception as e:
        logger.error(f"Scan error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan/batch")
async def scan_batch(request: ScanRequest, background_tasks: BackgroundTasks):
    """Batch tarama (Arka planda)"""
    # Bu basit bir implementasyon. Gerçekte bir job queue (Celery/Redis) gerekebilir.
    # Şimdilik anlık cevap verelim.
    return {"message": "Batch scan feature coming soon. Use single scan endpoints."}

@app.get("/api/watchlist")
async def get_watchlist():
    """Config'deki watchlist'i getir"""
    if scanner_system["cfg"]:
        return scanner_system["cfg"].get("symbols", [])
    return []

# Statik dosyalar (Frontend)
frontend_path = os.path.join(os.path.dirname(__file__), '../frontend')
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
