"""
Volume Profile - Hacim profili hesaplamaları
"""

import numpy as np
import pandas as pd


class VolumeProfile:
    """
    Volume Profile hesaplayıcı
    - POC (Point of Control)
    - VAH (Value Area High)
    - VAL (Value Area Low)
    - Cache mekanizması
    """

    _cache = {}

    @staticmethod
    def calculate(df: pd.DataFrame, num_bins: int = 50) -> dict:
        """
        Volume Profile hesapla

        Args:
            df: OHLCV DataFrame
            num_bins: Fiyat aralığı sayısı

        Returns:
            {
                'bins': Fiyat aralıkları,
                'volume_at_price': Her fiyattaki hacim,
                'poc': Point of Control (en yüksek hacim),
                'vah': Value Area High,
                'val': Value Area Low
            }
        """
        # Cache kontrolü
        cache_key = f"{len(df)}_{df['close'].iloc[-1]}_{num_bins}"

        if cache_key in VolumeProfile._cache:
            return VolumeProfile._cache[cache_key]

        prices = df["close"].values
        volumes = df["volume"].values

        price_min, price_max = prices.min(), prices.max()
        bins = np.linspace(price_min, price_max, num_bins)

        volume_at_price = np.zeros(num_bins - 1)

        # Her fiyat aralığındaki hacmi topla
        for i in range(len(prices)):
            bin_idx = np.digitize(prices[i], bins) - 1
            if 0 <= bin_idx < len(volume_at_price):
                volume_at_price[bin_idx] += volumes[i]

        # POC (Point of Control) - En yüksek hacimli fiyat
        poc_idx = np.argmax(volume_at_price)
        poc_price = (bins[poc_idx] + bins[poc_idx + 1]) / 2

        # Value Area (toplam hacmin %70'ini içeren alan)
        total_vol = volume_at_price.sum()
        target_vol = total_vol * 0.70

        sorted_indices = np.argsort(volume_at_price)[::-1]
        cumulative = 0
        value_area_indices = []

        for idx in sorted_indices:
            cumulative += volume_at_price[idx]
            value_area_indices.append(idx)
            if cumulative >= target_vol:
                break

        vah = bins[max(value_area_indices) + 1]
        val = bins[min(value_area_indices)]

        result = {
            "bins": bins,
            "volume_at_price": volume_at_price,
            "poc": poc_price,
            "vah": vah,
            "val": val,
        }

        # Cache'e kaydet
        VolumeProfile._cache[cache_key] = result
        return result


class FixedRangeVolumeProfile:
    """
    Sabit aralıklı hacim profili
    Grafiği eşit zaman aralıklarına böl ve her aralık için VP hesapla
    """

    @staticmethod
    def calculate(df: pd.DataFrame, num_ranges: int = 3) -> list:
        """
        Grafiği eşit zaman aralıklarına böl ve her aralık için VP hesapla

        Args:
            df: OHLCV DataFrame
            num_ranges: Kaç aralığa bölünsün (örn: 3 = son 3 bölüm)

        Returns:
            [
                {
                    'start_idx': Başlangıç index,
                    'end_idx': Bitiş index,
                    'vp_data': VolumeProfile.calculate() çıktısı,
                    'x_offset': X pozisyonu
                },
                ...
            ]
        """
        if len(df) < num_ranges * 20:
            return []

        range_size = len(df) // num_ranges
        profiles = []

        for i in range(num_ranges):
            start_idx = i * range_size
            end_idx = start_idx + range_size if i < num_ranges - 1 else len(df)

            range_df = df.iloc[start_idx:end_idx]

            if len(range_df) < 10:
                continue

            # Bu aralık için VP hesapla
            vp_data = VolumeProfile.calculate(range_df, num_bins=30)

            profiles.append(
                {
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                    "vp_data": vp_data,
                    "x_offset": start_idx,
                }
            )

        return profiles
