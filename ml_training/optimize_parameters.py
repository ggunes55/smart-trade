# -*- coding: utf-8 -*-
"""
Parameter Optimization Runner
Bu script, watchlist'teki veya belirtilen hisseler için genetik algoritma çalıştırır
ve bulunan en iyi parametreleri kaydeder.

Kullanım:
    python optimize_parameters.py --symbol THYAO
    python optimize_parameters.py --all --limit 10
"""
import logging
import argparse
import pandas as pd
import json
import os
import sys

# Proje kök dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.parameter_optimizer import ParameterOptimizer
from scanner.data_handler import DataHandler
from core.utils import load_config

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Swing Trade Parameter Optimizer")
    parser.add_argument("--symbol", type=str, help="Tek bir hisse için çalıştır")
    parser.add_argument("--all", action="store_true", help="Tüm watchlist için çalıştır (DB'den)")
    parser.add_argument("--limit", type=int, default=5, help="Tüm modunda kaç hisse optimize edilsin")
    parser.add_argument("--pop_size", type=int, default=20, help="GA popülasyon boyutu")
    parser.add_argument("--generations", type=int, default=5, help="GA jenerasyon sayısı")
    
    args = parser.parse_args()
    
    # Config ve DataHandler
    cfg = load_config("swing_config.json")
    data_handler = DataHandler(cfg)
    optimizer = ParameterOptimizer(population_size=args.pop_size, generations=args.generations)
    
    symbols_to_process = []
    
    if args.symbol:
        symbols_to_process.append(args.symbol.upper())
    elif args.all:
        # Watchlist'ten al (Örnek implementasyon - DB bağlantısı gerekebilir veya configden)
        # Basitlik için config'deki default symbolleri veya data_cache'tekileri alalım
        cache_dir = "data_cache"
        if os.path.exists(cache_dir):
            files = [f for f in os.listdir(cache_dir) if f.endswith('.parquet')]
            symbols_to_process = [f.split('_')[0] for f in files][:args.limit]
            logger.info(f"Found {len(symbols_to_process)} symbols in cache.")
        else:
            logger.warning("Cache directory not found. Please specify symbol.")
            return

    results = {}
    
    # Sonuç dosyasını yükle (varsa)
    output_file = "optimized_params.json"
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                results = json.load(f)
        except:
            pass
            
    for symbol in symbols_to_process:
        try:
            logger.info(f"Fetching data for {symbol}...")
            df = data_handler.get_daily_data(symbol, cfg.get("exchange", "BIST"))
            
            if df is None or len(df) < 100:
                logger.warning(f"Not enough data for {symbol}, skipping.")
                continue
                
            logger.info(f"Optimizing {symbol}...")
            best_params = optimizer.optimize(df, symbol)
            
            # Sonuçları kaydet
            results[symbol] = best_params
            
            # Her adımda dosyaya yaz (crash durumunda veri kaybını önle)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=4)
                
            logger.info(f"Saved optimized params for {symbol}")
            
        except Exception as e:
            logger.error(f"Error optimizing {symbol}: {e}")
            
    logger.info("Optimization complete.")

if __name__ == "__main__":
    main()
