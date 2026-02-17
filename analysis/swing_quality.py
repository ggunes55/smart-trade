import numpy as np
import pandas as pd
from typing import Dict, Optional

def calculate_swing_quality(df: pd.DataFrame, trend_direction: str = "UP") -> Dict[str, float]:
    """
    Calculates Swing Quality Metrics
    
    1. Swing Efficiency Ratio (Kaufman Efficiency Ratio):
       Measures how "clean" the trend is. 
       Efficiency = Net Move / Total Distance
       1.0 = Straight line (Perfect efficiency)
       0.0 = Pure noise
       
    2. Pullback Strength Score:
       Evaluates the quality of a pullback if one is detected.
    """
    if df is None or len(df) < 20:
        return {
            "efficiency_ratio": 0.0,
            "pullback_score": 0.0,
            "pullback_depth": 0.0
        }
    
    try:
        # 1. Swing Efficiency Ratio
        # window = 10 for short term swing efficiency
        window = 10
        closes = df['close']
        
        # Net change over window
        change = closes.diff(window).abs().iloc[-1]
        
        # Sum of absolute changes (Path length)
        # We need the last 'window' changes
        volatility = closes.diff().abs().tail(window).sum()
        
        if volatility > 0:
            efficiency_ratio = change / volatility
        else:
            efficiency_ratio = 0.0
            
        # User's suggested metric: Close-to-Close vs High-Low Range
        # "Noise Ratio" can be a secondary metric
        
        # 2. Pullback Strength Score
        # First, are we in a pullback?
        # A pullback in an uptrend means Price < Max(Last N) but Price > Moving Average
        
        score_pullback = 0.0
        depth_fib = 0.0
        
        current_price = closes.iloc[-1]
        highest_20 = df['high'].tail(20).max()
        lowest_20 = df['low'].tail(20).min()
        
        range_20 = highest_20 - lowest_20
        
        if range_20 > 0:
            # Depth from High
            pullback_depth = (highest_20 - current_price) / range_20
        else:
            pullback_depth = 0
            
        # Logic: Best pullbacks are 38.2% to 61.8% of the move
        # Here we calculated depth relative to the 20-day range. 
        # A full fib retracement calculation would require identifying the last swing low.
        # For efficiency, we use the 20-day range as a proxy for the 'swing'.
        
        is_pullback = False
        if 0.1 < pullback_depth < 0.8: # Must be somewhat down from high
            is_pullback = True
            
        if is_pullback and trend_direction == "UP":
            # Depth Score
            if 0.3 <= pullback_depth <= 0.6: # Sweet spot
                depth_score = 80
            elif 0.15 <= pullback_depth <= 0.7: # Acceptable
                depth_score = 60
            else:
                depth_score = 30
                
            # Volume Score
            # Volume should be lower during pullback
            avg_vol = df['volume'].tail(20).mean()
            curr_vol = df['volume'].iloc[-1]
            
            if curr_vol < avg_vol:
                vol_score = 80
            else:
                vol_score = 40
                
            score_pullback = (depth_score * 0.6) + (vol_score * 0.4)
        else:
            # If not in pullback or not uptrend
            score_pullback = 0.0
        
        return {
            "efficiency_ratio": round(efficiency_ratio, 2),
            "pullback_score": round(score_pullback, 1),
            "pullback_depth_pct": round(pullback_depth * 100, 1)
        }
        
    except Exception as e:
        print(f"Error calculating swing quality: {e}")
        return {
            "efficiency_ratio": 0.0,
            "pullback_score": 0.0,
            "pullback_depth_pct": 0.0
        }
