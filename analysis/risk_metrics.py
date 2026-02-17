import numpy as np
import pandas as pd
from typing import Dict, Optional

def calculate_risk_metrics(df: pd.DataFrame, window: int = 252) -> Dict[str, float]:
    """
    Advanced Risk Metrics Calculation for Swing Trading
    
    Calculates:
    - Sharpe Ratio (Risk-adjusted return)
    - Sortino Ratio (Downside risk-adjusted return)
    - Calmar Ratio (Return / Max Drawdown)
    - Maximum Drawdown (MDD)
    - Volatility Score (Normalized 0-100)
    
    Args:
        df: DataFrame with 'close' column
        window: Lookback window for calculations (default 252 for annual)
        
    Returns:
        Dictionary containing calculated metrics
    """
    if df is None or len(df) < 30:
        return {
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility_score": 0.0,
            "volatility_annualized": 0.0
        }
        
    try:
        # Prepare returns
        prices = df['close']
        returns = prices.pct_change().dropna()
        
        # 1. Maximum Drawdown (MDD)
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        max_drawdown = drawdown.min() # This is negative, e.g. -0.15 for 15% drop
        max_drawdown_pct = abs(max_drawdown * 100)
        
        # 2. Annualized Metrics
        # Assuming daily data
        annual_factor = 252
        avg_return = returns.mean() * annual_factor
        std_dev = returns.std() * np.sqrt(annual_factor)
        
        # Risk-free rate assumption (e.g., 30% for TR or 0% for simplicity of relative scoring)
        # Using 0 for relative scoring between stocks is cleaner for scanners
        risk_free_rate = 0.0 
        
        # 3. Sharpe Ratio
        if std_dev > 0:
            sharpe = (avg_return - risk_free_rate) / std_dev
        else:
            sharpe = 0.0
            
        # 4. Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(annual_factor)
        
        if downside_std > 0:
            sortino = (avg_return - risk_free_rate) / downside_std
        else:
            # If no downside deviation (perfect stock?), give it a high score or calc based on std
            sortino = sharpe * 1.5 if sharpe > 0 else 0.0
            
        # 5. Calmar Ratio
        if max_drawdown_pct > 0:
            calmar = avg_return / (max_drawdown_pct / 100)
        else:
            calmar = 0.0
            
        # 6. Volatility Score (0-100 Normalized)
        # We need a reference max volatility to normalize. 
        # For a single stock, we can look at its rolling volatility vs its own history/recent history.
        # Or provide a raw volatility number.
        
        # Here we calculate a score based on recent volatility vs long term avg
        recent_vol = returns.tail(20).std() * np.sqrt(annual_factor)
        
        # Normalize: Lower volatility is better for "Stability", but for Swing we want some movement.
        # However, usually "Volatility Score" implies "How volatile is it".
        # Let's return the raw annualized volatility, and a score where 0 = crazy, 100 = stable.
        # OR 0-100 representing the volatility level itself.
        # The user's formula: (volatility / max_vol) * 100.
        # Let's use the user's logic roughly: Relative Volatility.
        
        volatility_score = min((std_dev * 100), 100) # Simple cap at 100% vol
        
        return {
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "max_drawdown": round(max_drawdown_pct, 2),
            "volatility_score": round(volatility_score, 2), # Raw Volatility % basically
            "volatility_annualized": round(std_dev * 100, 2)
        }
        
    except Exception as e:
        print(f"Error calculating risk metrics: {e}")
        return {
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown": 0.0,
            "volatility_score": 0.0,
            "volatility_annualized": 0.0
        }
