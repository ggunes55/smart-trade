import numpy as np
import pandas as pd
from analysis.stat_tests import t_test_signal_vs_benchmark, confidence_interval

def test_t_test_signal_vs_benchmark():
    np.random.seed(42)
    signal = pd.Series(np.random.normal(0.01, 0.02, 100))
    benchmark = pd.Series(np.random.normal(0.005, 0.02, 100))
    p, stat, mean_signal, mean_bench = t_test_signal_vs_benchmark(signal, benchmark)
    assert p is not None
    print(f"t-test p: {p:.4f}, stat: {stat:.2f}, mean_signal: {mean_signal:.4f}, mean_bench: {mean_bench:.4f}")

def test_confidence_interval():
    np.random.seed(42)
    data = pd.Series(np.random.normal(0, 1, 100))
    lower, upper = confidence_interval(data)
    assert lower is not None and upper is not None
    print(f"95% CI: [{lower:.4f}, {upper:.4f}]")
