# -*- coding: utf-8 -*-
"""
GUI State Manager - Merkezi veri yönetimi
Sekmeler arası veri senkronizasyonu ve state tracking
"""

from typing import Any, Callable, Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GUIStateManager:
    """
    Merkezi state yönetim sistemi - Observer pattern kullanır
    Tüm tablar bu manager'dan state bilgisini alır ve güncellemesi
    """

    def __init__(self):
        """State manager'ı başlat"""
        self._state = {
            # Tarama ayarları
            'selected_symbols': [],
            'selected_exchanges': [],
            'scan_criteria': {},
            
            # Tarama sonuçları
            'scan_results': [],
            'active_result': None,
            
            # Detaylı analiz
            'analysis_data': None,
            'analysis_symbol': None,
            
            # Backtest
            'backtest_config': {},
            'backtest_results': None,
            'backtest_trades': [],
            
            # Piyasa analizi
            'market_analysis': None,
            'market_regime': None,
            
            # Portfolio
            'portfolio_positions': [],
            'portfolio_metrics': None,
            'portfolio_live_pnl': None,  # WebSocket canlı P&L güncellemesi
            
            # Real-time (WebSocket)
            'real_time_signals': [],
            
            # ML/AI
            'ml_models': [],
            'active_ml_model': None,
            'ml_metrics': None,
            
            # Watchlist
            'watchlist_items': [],
            'watchlist_updates': {},
            
            # Ayarlar
            'settings': {},
            'theme': 'light',
            
            # UI State
            'active_tab': 0,
            'window_geometry': None,
        }
        
        # History for undo/redo
        self._history = []
        self._history_index = -1
        self._max_history = 50
        
        # Observers (tabs) - key: observer_name, value: callback
        self._observers = {}
        
        # Subscription groups - belirli state key'le subscribe olmak
        self._subscriptions = {}

    def subscribe(self, observer_name: str, callback: Callable, 
                 keys: Optional[List[str]] = None):
        """
        Observer'ı subscribe et
        
        Args:
            observer_name: Observer'ın adı (ex: 'PortfolioTab')
            callback: state değiştiğinde çağrılacak fonksiyon
                     Signature: callback(changed_key, new_value, old_value)
            keys: Sadece bu key'lerdeki değişiklikleri dinle (None=tümü)
        """
        if observer_name not in self._observers:
            self._observers[observer_name] = []
        
        self._observers[observer_name].append({
            'callback': callback,
            'keys': keys  # None = tüm key'ler
        })
        logger.debug(f"Observer '{observer_name}' subscribed")

    def unsubscribe(self, observer_name: str, callback: Callable):
        """Observer'ı unsubscribe et"""
        if observer_name in self._observers:
            self._observers[observer_name] = [
                obs for obs in self._observers[observer_name]
                if obs['callback'] != callback
            ]

    def get(self, key: str) -> Any:
        """State değerini getir"""
        return self._state.get(key)

    def set(self, key: str, value: Any, skip_history: bool = False) -> bool:
        """
        State değerini ayarla ve observers'i bilgilendir
        
        Args:
            key: State key'i
            value: Yeni değer
            skip_history: History'ye ekleme (internal updates için)
        
        Returns:
            bool: State değişti mi?
        """
        if key not in self._state:
            logger.warning(f"Unknown state key: {key}")
            return False
        
        old_value = self._state[key]
        
        # Deep equality check (lists, dicts)
        if self._equals(old_value, value):
            return False
        
        self._state[key] = value
        
        # History ekle (undo/redo)
        if not skip_history:
            self._add_to_history(key, old_value, value)
        
        # Observers'i notifique et
        self._notify_observers(key, value, old_value)
        
        logger.debug(f"State updated: {key}")
        return True

    def update_nested(self, key: str, nested_key: str, value: Any,
                     skip_history: bool = False) -> bool:
        """
        Nested state value'yu güncelle (dict içindeki değer)
        
        Args:
            key: Dict state key'i
            nested_key: Dict içindeki key
            value: Yeni değer
        
        Returns:
            bool: State değişti mi?
        """
        if key not in self._state:
            logger.warning(f"Unknown state key: {key}")
            return False
        
        if not isinstance(self._state[key], dict):
            logger.error(f"State[{key}] is not a dict")
            return False
        
        old_value = self._state[key].get(nested_key)
        
        if self._equals(old_value, value):
            return False
        
        self._state[key][nested_key] = value
        
        if not skip_history:
            self._add_to_history(f"{key}.{nested_key}", old_value, value)
        
        self._notify_observers(key, self._state[key], {"changed": nested_key})
        return True

    def batch_update(self, updates: Dict[str, Any], skip_history: bool = False):
        """
        Birden fazla state'i bir seferde güncelle
        
        Args:
            updates: {key: value, ...} dict'i
            skip_history: History'ye ekleme
        """
        changed_keys = []
        for key, value in updates.items():
            if self.set(key, value, skip_history=True):
                changed_keys.append(key)
        
        if not skip_history and changed_keys:
            self._add_to_history("batch_update", None, updates)
        
        # Observers'i bir sefer bilgilendir
        for key in changed_keys:
            self._notify_observers(key, self._state[key], None)

    def append_to_list(self, key: str, item: Any) -> bool:
        """
        List state'e item ekle
        
        Args:
            key: List state key'i
            item: Eklenecek item
        """
        if key not in self._state:
            logger.warning(f"Unknown state key: {key}")
            return False
        
        if not isinstance(self._state[key], list):
            logger.error(f"State[{key}] is not a list")
            return False
        
        old_list = self._state[key].copy()
        self._state[key].append(item)
        
        self._add_to_history(f"{key}.append", old_list, self._state[key].copy())
        self._notify_observers(key, self._state[key], old_list)
        
        return True

    def remove_from_list(self, key: str, index: int) -> bool:
        """
        List state'den item çıkar
        
        Args:
            key: List state key'i
            index: Silinecek index
        """
        if key not in self._state:
            logger.warning(f"Unknown state key: {key}")
            return False
        
        if not isinstance(self._state[key], list) or index >= len(self._state[key]):
            return False
        
        old_list = self._state[key].copy()
        removed_item = self._state[key].pop(index)
        
        self._add_to_history(f"{key}.remove", old_list, self._state[key].copy())
        self._notify_observers(key, self._state[key], old_list)
        
        return True

    def clear_list(self, key: str) -> bool:
        """List state'i temizle"""
        if key not in self._state or not isinstance(self._state[key], list):
            return False
        
        old_list = self._state[key].copy()
        self._state[key] = []
        
        self._add_to_history(f"{key}.clear", old_list, [])
        self._notify_observers(key, [], old_list)
        
        return True

    def undo(self) -> bool:
        """Önceki state'e geri dön"""
        if self._history_index <= 0:
            return False
        
        self._history_index -= 1
        self._restore_from_history()
        return True

    def redo(self) -> bool:
        """Sonraki state'e ileri git"""
        if self._history_index >= len(self._history) - 1:
            return False
        
        self._history_index += 1
        self._restore_from_history()
        return True

    def can_undo(self) -> bool:
        """Undo mümkün mü?"""
        return self._history_index > 0

    def can_redo(self) -> bool:
        """Redo mümkün mü?"""
        return self._history_index < len(self._history) - 1

    def reset(self):
        """State'i sıfırla"""
        self._state = {
            'selected_symbols': [],
            'selected_exchanges': [],
            'scan_criteria': {},
            'scan_results': [],
            'active_result': None,
            'analysis_data': None,
            'analysis_symbol': None,
            'backtest_config': {},
            'backtest_results': None,
            'backtest_trades': [],
            'market_analysis': None,
            'market_regime': None,
            'portfolio_positions': [],
            'portfolio_metrics': None,
            'portfolio_live_pnl': None,
            'real_time_signals': [],
            'ml_models': [],
            'active_ml_model': None,
            'ml_metrics': None,
            'watchlist_items': [],
            'watchlist_updates': {},
            'settings': {},
            'theme': 'light',
            'active_tab': 0,
            'window_geometry': None,
        }
        self._history = []
        self._history_index = -1
        
        for observer_name in self._observers:
            self._notify_observer(observer_name, '__reset__', None, None)

    def save_to_file(self, filepath: str) -> bool:
        """State'i JSON dosyasına kaydet"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, default=str, ensure_ascii=False)
            logger.info(f"State saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False

    def load_from_file(self, filepath: str) -> bool:
        """State'i JSON dosyasından yükle"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_state = json.load(f)
            
            self._state.update(loaded_state)
            self._history = []
            self._history_index = -1
            
            logger.info(f"State loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return False

    def export_state(self) -> Dict[str, Any]:
        """Mevcut state'i dict olarak döndür"""
        return {k: v for k, v in self._state.items()}

    # ==================== PRIVATE METHODS ====================

    def _equals(self, a: Any, b: Any) -> bool:
        """Derin eşitlik kontrolü"""
        if type(a) != type(b):
            return False
        
        if isinstance(a, (list, dict)):
            return json.dumps(a, sort_keys=True, default=str) == \
                   json.dumps(b, sort_keys=True, default=str)
        
        return a == b

    def _add_to_history(self, key: str, old_value: Any, new_value: Any):
        """History'ye ekleme"""
        # Eğer redo geçmişi varsa sil
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        
        # History entry ekle
        self._history.append({
            'key': key,
            'old_value': old_value,
            'new_value': new_value,
            'timestamp': datetime.now().isoformat(),
        })
        
        # Max history kontrol
        if len(self._history) > self._max_history:
            self._history.pop(0)
        else:
            self._history_index += 1

    def _restore_from_history(self):
        """History'den state restore et"""
        if not (0 <= self._history_index < len(self._history)):
            return
        
        entry = self._history[self._history_index]
        key = entry['key']
        
        if key == 'batch_update':
            # Batch update restore
            for update_key, value in entry['new_value'].items():
                self._state[update_key] = value
        elif key.endswith('.append'):
            # List append restore
            list_key = key.replace('.append', '')
            self._state[list_key] = entry['new_value']
        elif key.endswith('.remove'):
            # List remove restore
            list_key = key.replace('.remove', '')
            self._state[list_key] = entry['new_value']
        elif key.endswith('.clear'):
            # List clear restore
            list_key = key.replace('.clear', '')
            self._state[list_key] = entry['new_value']
        elif '.' in key:
            # Nested update restore
            parent_key, nested_key = key.split('.', 1)
            self._state[parent_key][nested_key] = entry['new_value']
        else:
            # Normal update
            self._state[key] = entry['new_value']
        
        self._notify_observers(key, entry['new_value'], entry['old_value'])

    def _notify_observers(self, key: str, new_value: Any, old_value: Any):
        """Tüm observers'i bilgilendir"""
        for observer_name in self._observers:
            self._notify_observer(observer_name, key, new_value, old_value)

    def _notify_observer(self, observer_name: str, key: str, 
                        new_value: Any, old_value: Any):
        """Belirli observer'i bilgilendir"""
        if observer_name not in self._observers:
            return
        
        for observer_info in self._observers[observer_name]:
            callback = observer_info['callback']
            keys = observer_info['keys']
            
            # Eğer belirli key'ler dinleniyorsa kontrol et
            if keys is not None and key not in keys:
                continue
            
            try:
                callback(key, new_value, old_value)
            except Exception as e:
                logger.error(f"Error calling observer {observer_name}: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """State manager istatistikleri"""
        return {
            'total_state_keys': len(self._state),
            'history_depth': len(self._history),
            'history_index': self._history_index,
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo(),
            'active_observers': len(self._observers),
            'registered_keys': list(self._state.keys()),
        }
