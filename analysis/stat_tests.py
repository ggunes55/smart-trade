import numpy as np
import pandas as pd
from scipy import stats

def t_test_signal_vs_benchmark(signal: pd.Series, benchmark: pd.Series):
    """
    Sinyal getirisi ile benchmark getirisi arasında t-testi uygular.
    Dönüş: p-değeri, istatistik, ortalamalar
    """
    signal = signal.dropna()
    benchmark = benchmark.dropna()
    if len(signal) < 10 or len(benchmark) < 10:
        return None, None, None, None
    stat, p = stats.ttest_ind(signal, benchmark, nan_policy='omit')
    return p, stat, signal.mean(), benchmark.mean()

def confidence_interval(series: pd.Series, confidence=0.95):
    """
    Bir serinin güven aralığını hesaplar.
    """
    a = series.dropna().values
    n = len(a)
    if n < 2:
        return None, None
    m, se = np.mean(a), stats.sem(a)
    h = se * stats.t.ppf((1 + confidence) / 2., n-1)
    return m - h, m + h
