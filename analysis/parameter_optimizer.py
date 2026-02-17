# -*- coding: utf-8 -*-
"""
Parameter Optimizer - FAZA 2: Genetik Algoritma ile Integration Engine Ağırlıklarını Optimize Et

Integration Engine'in ağırlıklarını (0.25, 0.25, 0.30, 0.20) optimize etmek için
Genetic Algorithm kullanarak piyasa koşullarına göre dinamik parametre ayarlama.

Tarih: 12 Şubat 2026
Versiyon: 2.0 (FAZA 2 - GeneticAlgorithmOptimizer eklendi)
"""
import logging
import random
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
from indicators.ta_manager import calculate_indicators

logger = logging.getLogger(__name__)


# ============================================================================
# FAZA 2: Genetic Algorithm Parameter Optimization
# ============================================================================

@dataclass
class GeneticAlgorithmConfig:
    """Genetic Algorithm parametreleri"""
    population_size: int = 50
    generations: int = 100
    mutation_rate: float = 0.15
    crossover_rate: float = 0.8
    elite_ratio: float = 0.1  # En iyi %10'unu koru
    min_weight: float = 0.10  # En düşük ağırlık
    max_weight: float = 0.40  # En yüksek ağırlık
    weight_precision: float = 0.05  # 5'er adımlar (0.05, 0.10, 0.15, ...)


class GeneticAlgorithmOptimizer:
    """
    Integration Engine ağırlıklarını optimize etmek için Genetic Algorithm
    
    Amaç:
    - Base signal, confirmation, ML confidence, entry timing ağırlıklarını optimize et
    - Backtest win rate'i maksimize et
    - Piyasa rejimi bazında farklı weight set'leri oluştur
    """
    
    def __init__(self, cfg: Optional[GeneticAlgorithmConfig] = None):
        self.cfg = cfg or GeneticAlgorithmConfig()
        self.population = []
        self.fitness_scores = []
        self.best_individual = None
        self.best_fitness = -np.inf
        self.fitness_history = []
        logger.info(f"✅ GeneticAlgorithmOptimizer initialized (FAZA 2)")
    
    def create_population(self, size: Optional[int] = None) -> List[Dict]:
        """Rastgele weight kombinasyonlarından population oluştur"""
        size = size or self.cfg.population_size
        population = []
        
        initial_weights = {
            'base_signal': 0.25,
            'confirmation': 0.25,
            'ml_confidence': 0.30,
            'entry_timing': 0.20
        }
        
        for i in range(size):
            if i == 0:
                weights = initial_weights.copy()
            else:
                raw_weights = np.random.uniform(
                    self.cfg.min_weight,
                    self.cfg.max_weight,
                    4
                )
                total = raw_weights.sum()
                raw_weights = raw_weights / total
                raw_weights = np.round(raw_weights / self.cfg.weight_precision) * self.cfg.weight_precision
                total = raw_weights.sum()
                if total > 0:
                    raw_weights = raw_weights / total
                
                weights = {
                    'base_signal': float(raw_weights[0]),
                    'confirmation': float(raw_weights[1]),
                    'ml_confidence': float(raw_weights[2]),
                    'entry_timing': float(raw_weights[3])
                }
            population.append(weights)
        
        self.population = population
        logger.info(f"✅ Population created: {len(population)} individuals")
        return population
    
    def evaluate_fitness(self, weights: Dict[str, float], backtest_results: pd.DataFrame) -> float:
        """Ağırlık kombinasyonu için fitness (win rate) hesapla"""
        try:
            if len(backtest_results) == 0:
                return 0.0
            
            wins = (backtest_results.get('profit_pct', backtest_results.get('win', [0])) > 0).sum()
            total = len(backtest_results)
            win_rate = wins / total if total > 0 else 0
            
            try:
                returns = backtest_results.get('profit_pct', [0])
                if len(returns) > 1:
                    sharpe_bonus = np.std(returns) / (np.mean(returns) + 1e-6)
                    fitness = win_rate * 0.7 + (1 - min(1, sharpe_bonus)) * 0.3
                else:
                    fitness = win_rate
            except:
                fitness = win_rate
            
            return max(0.0, min(1.0, fitness))
        except Exception as e:
            logger.warning(f"Fitness calculation error: {e}")
            return 0.0
    
    def evaluate_population(self, backtest_results: pd.DataFrame) -> List[float]:
        """Tüm populasyon için fitness hesapla"""
        self.fitness_scores = []
        
        for individual in self.population:
            fitness = self.evaluate_fitness(individual, backtest_results)
            self.fitness_scores.append(fitness)
        
        best_idx = np.argmax(self.fitness_scores)
        if self.fitness_scores[best_idx] > self.best_fitness:
            self.best_fitness = self.fitness_scores[best_idx]
            self.best_individual = self.population[best_idx].copy()
        
        self.fitness_history.append(self.best_fitness)
        logger.debug(f"  Best fitness: {self.best_fitness:.3f}")
        return self.fitness_scores
    
    def selection(self, k: int = 2) -> Tuple[Dict, Dict]:
        """Tournament selection"""
        def tournament():
            idx = np.random.choice(len(self.population), k, replace=False)
            best_idx = idx[np.argmax([self.fitness_scores[i] for i in idx])]
            return self.population[best_idx]
        
        return tournament(), tournament()
    
    def crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Uniform crossover"""
        if np.random.random() > self.cfg.crossover_rate:
            return parent1.copy() if np.random.random() > 0.5 else parent2.copy()
        
        child = {}
        keys = ['base_signal', 'confirmation', 'ml_confidence', 'entry_timing']
        
        for key in keys:
            child[key] = parent1[key] if np.random.random() < 0.5 else parent2[key]
        
        total = sum(child.values())
        for key in keys:
            child[key] = child[key] / total if total > 0 else 0.25
        
        return child
    
    def mutate(self, individual: Dict) -> Dict:
        """Mutation: Rastgele weight'leri değiştir"""
        if np.random.random() > self.cfg.mutation_rate:
            return individual.copy()
        
        mutant = individual.copy()
        keys = ['base_signal', 'confirmation', 'ml_confidence', 'entry_timing']
        key_to_mutate = np.random.choice(keys)
        mutation_amount = np.random.uniform(-0.1, 0.1)
        
        mutant[key_to_mutate] = np.clip(
            mutant[key_to_mutate] + mutation_amount,
            self.cfg.min_weight,
            self.cfg.max_weight
        )
        
        total = sum(mutant.values())
        for key in keys:
            mutant[key] = mutant[key] / total if total > 0 else 0.25
        
        return mutant
    
    def evolve(self, backtest_results: pd.DataFrame, 
               generations: Optional[int] = None) -> Dict:
        """Genetic algorithm evolution"""
        generations = generations or self.cfg.generations
        self.create_population()
        logger.info(f"🧬 Starting GA evolution: {generations} generations")
        
        for gen in range(generations):
            self.evaluate_population(backtest_results)
            elite_size = max(1, int(len(self.population) * self.cfg.elite_ratio))
            new_population = []
            
            elite_indices = np.argsort(self.fitness_scores)[-elite_size:]
            for idx in sorted(elite_indices, reverse=True):
                new_population.append(self.population[idx].copy())
            
            while len(new_population) < len(self.population):
                parent1, parent2 = self.selection(k=3)
                child = self.crossover(parent1, parent2)
                child = self.mutate(child)
                new_population.append(child)
            
            self.population = new_population[:len(self.population)]
            
            if (gen + 1) % 10 == 0:
                logger.info(f"  Generation {gen+1}/{generations}: Best fitness = {self.best_fitness:.3f}")
        
        logger.info(f"✅ Evolution complete!")
        logger.info(f"   - Best fitness: {self.best_fitness:.3f}")
        logger.info(f"   - Best weights:")
        for k, v in sorted(self.best_individual.items()):
            logger.info(f"     - {k}: {v:.3f}")
        
        return self.best_individual.copy()
    
    def save_results(self, filepath: str) -> bool:
        """Optimize edilmiş ağırlıkları dosyaya kaydet"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            results = {
                'best_weights': self.best_individual,
                'best_fitness': float(self.best_fitness),
                'fitness_history': [float(f) for f in self.fitness_history],
                'config': {
                    'population_size': self.cfg.population_size,
                    'generations': self.cfg.generations,
                    'mutation_rate': self.cfg.mutation_rate
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"✅ Results saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
            return False


# ============================================================================
# ORİJİNAL: Parameter Optimizer - Genetik Algoritma ile İndikatör Ayarlarını Optimize Et
# ============================================================================

class ParameterOptimizer:
    """
    Genetik Algoritma (GA) kullanarak trading parametrelerini optimize eder.
    """
    
    def __init__(self, population_size: int = 20, generations: int = 5):
        self.pop_size = population_size
        self.generations = generations
        
        # Gen Uzayı (Gene Space) - Optimize edilecek parametrelerin aralıkları
        self.gene_space = {
            'rsi_period': (7, 30),
            'macd_fast': (8, 20),
            'macd_slow': (21, 40),
            'macd_signal': (5, 15),
            'ema_fast': (5, 20),
            'ema_slow': (20, 200),
            'stop_loss_atr': (1.0, 5.0), # ATR çarpanı olarak
            'take_profit_atr': (2.0, 10.0) # ATR çarpanı olarak
        }

    def _generate_individual(self) -> Dict:
        """Rastgele bir birey (parametre seti) oluştur"""
        individual = {}
        for param, (min_val, max_val) in self.gene_space.items():
            if isinstance(min_val, int):
                individual[param] = random.randint(min_val, max_val)
            else:
                individual[param] = random.uniform(min_val, max_val)
        return individual

    def _fitness_function(self, params: Dict, df: pd.DataFrame) -> float:
        """
        Uygunluk fonksiyonu (Fitness Function)
        Verilen parametrelerle basit bir backtest çalıştırır ve skoru (Total Profit) döndürür.
        """
        # Burada indikatörleri tekrar hesaplamak maliyetli olabilir. 
        # Optimize edilmiş bir yöntem parametreleri dinamik değiştirebilen bir backtest motorudur.
        # Basitlik için burada çok basit bir simülasyon yapıyoruz.
        
        try:
            # NOT: Gerçek bir implementasyonda indikatörleri her adımda hesaplamak yerine,
            # önceden hesaplanmış cache veya daha hızlı bir yöntem kullanılmalı.
            # Ancak parametreler (örn RSI periyodu) değiştiği için mecbur hesaplayacağız.
            
            # DataFrame kopyası üzerinde çalış
            temp_df = df.copy()
            
            # Sadece gerekli indikatörleri hesapla (Optimized calculation)
            # RSI
            delta = temp_df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
            rs = gain / loss.replace(0, 0.001)
            temp_df['rsi_opt'] = 100 - (100 / (1 + rs))
            
            # EMA
            temp_df['ema_fast_opt'] = temp_df['close'].ewm(span=params['ema_fast']).mean()
            temp_df['ema_slow_opt'] = temp_df['close'].ewm(span=params['ema_slow']).mean()
            
            # ATR (Stop loss için)
            tr = pd.concat([
                temp_df['high'] - temp_df['low'],
                abs(temp_df['high'] - temp_df['close'].shift()),
                abs(temp_df['low'] - temp_df['close'].shift())
            ], axis=1).max(axis=1)
            temp_df['atr_opt'] = tr.rolling(14).mean()
            
            # Basit Strateji: EMA Cross + RSI Filter
            # AL: EMA_Fast > EMA_Slow AND RSI < 70
            # SAT: Stop Loss or Take Profit
            
            balance = 10000
            position = 0
            entry_price = 0
            entry_idx = 0
            trades = 0
            wins = 0
            
            prices = temp_df['close'].values
            rsi = temp_df['rsi_opt'].values
            ema_f = temp_df['ema_fast_opt'].values
            ema_s = temp_df['ema_slow_opt'].values
            atr = temp_df['atr_opt'].values
            lows = temp_df['low'].values
            highs = temp_df['high'].values
            
            for i in range(50, len(temp_df)):
                current_price = prices[i]
                
                if position == 0:
                    # Alım Sinyali
                    if ema_f[i] > ema_s[i] and ema_f[i-1] <= ema_s[i-1] and rsi[i] < 70:
                        position = balance / current_price
                        entry_price = current_price
                        entry_idx = i
                        sl_price = entry_price - (atr[i] * params['stop_loss_atr'])
                        tp_price = entry_price + (atr[i] * params['take_profit_atr'])
                
                elif position > 0:
                    # Satış Kontrolü (SL / TP)
                    # Low, SL'e değdi mi?
                    if lows[i] <= sl_price:
                        # Stop Loss
                        balance = position * sl_price
                        position = 0
                        trades += 1
                        # Loss
                    elif highs[i] >= tp_price:
                        # Take Profit
                        balance = position * tp_price
                        position = 0
                        trades += 1
                        wins += 1
                    # Trend dönüşü (Opsiyonel çıkış)
                    elif ema_f[i] < ema_s[i]:
                        balance = position * current_price
                        position = 0
                        trades += 1
                        if current_price > entry_price:
                            wins += 1
                            
            if position > 0:
                balance = position * prices[-1]

            # Fitness Score: Net Profit * Win Rate (Penalize inactivity)
            profit_pct = (balance - 10000) / 10000 * 100
            win_rate = (wins / trades) if trades > 0 else 0
            
            # Eğer hiç trade yoksa kötü skor
            if trades < 3:
                return -100
                
            score = profit_pct * (1 + win_rate)
            return score
            
        except Exception as e:
            # logger.error(f"Optimization fitness error: {e}")
            return -999

    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """İki ebeveynden çocuk üret"""
        child = {}
        for param in self.gene_space:
            # %50 şansla anneden veya babadan gen al
            if random.random() < 0.5:
                child[param] = parent1[param]
            else:
                child[param] = parent2[param]
        return child

    def _mutate(self, individual: Dict, mutation_rate: float = 0.1) -> Dict:
        """Mutasyon uygula"""
        mutated = individual.copy()
        for param, (min_val, max_val) in self.gene_space.items():
            if random.random() < mutation_rate:
                # Geni rastgele değiştir
                if isinstance(min_val, int):
                    mutated[param] = random.randint(min_val, max_val)
                else:
                    mutated[param] = random.uniform(min_val, max_val)
        return mutated

    def optimize(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Genetik algoritmayı çalıştır ve en iyi parametreleri bul
        """
        logger.info(f"Optimizing parameters for {symbol} (Pop: {self.pop_size}, Gen: {self.generations})")
        
        # 1. Başlangıç Popülasyonu
        population = [self._generate_individual() for _ in range(self.pop_size)]
        
        best_overall = None
        best_score_overall = -float('inf')
        
        for gen in range(self.generations):
            # 2. Fitness Hesapla
            scores = [(ind, self._fitness_function(ind, df)) for ind in population]
            scores.sort(key=lambda x: x[1], reverse=True)
            
            best_gen = scores[0][0]
            best_score_gen = scores[0][1]
            
            if best_score_gen > best_score_overall:
                best_score_overall = best_score_gen
                best_overall = best_gen
                
            logger.debug(f"Gen {gen+1}: Best Score = {best_score_gen:.2f}")
            
            # Elitism: En iyi %20 direk geçer
            elite_count = int(self.pop_size * 0.2)
            next_generation = [x[0] for x in scores[:elite_count]]
            
            # 3. Yeni Nesil Oluştur
            while len(next_generation) < self.pop_size:
                # Tournament Selection
                parent1 = random.choice(scores[:self.pop_size//2])[0]
                parent2 = random.choice(scores[:self.pop_size//2])[0]
                
                child = self._crossover(parent1, parent2)
                child = self._mutate(child)
                next_generation.append(child)
                
            population = next_generation
            
        logger.info(f"Optimization finished. Best Score: {best_score_overall:.2f}")
        logger.info(f"Best Params: {best_overall}")
        
        return best_overall
