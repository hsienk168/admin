import numpy as np
from typing import List, Tuple, Optional

class VolatilityAnalyzer:
    def __init__(self, threshold_pct: float = 5.0, std_multiplier: float = 2.0):
        self.threshold_pct = threshold_pct
        self.std_multiplier = std_multiplier

    def check_volatility(
        self,
        current_price: float,
        price_5min_ago: float,
        price_24h_ago: float,
        rolling_24h_prices: List[float]
    ) -> Tuple[bool, dict]:
        # Guard against price_5min_ago == 0
        if price_5min_ago == 0:
            return False, {"error": "price_5min_ago is zero", "change_pct": 0, "std_devs": 0}

        change_pct = ((current_price - price_5min_ago) / price_5min_ago) * 100

        if len(rolling_24h_prices) < 2:
            std_devs = 0.0
        else:
            # Guard against zero prices in rolling_24h_prices
            prices_arr = np.array(rolling_24h_prices)
            nonzero_mask = prices_arr[:-1] != 0
            if not np.any(nonzero_mask):
                std_devs = 0.0
            else:
                # Compute diff only for nonzero elements, then divide by corresponding prices
                diffs = np.diff(prices_arr)
                returns = diffs[nonzero_mask] / prices_arr[:-1][nonzero_mask] * 100
                if len(returns) == 0:
                    std_devs = 0.0
                else:
                    mean_ret = np.mean(returns)
                    std_ret = np.std(returns)
                    if std_ret == 0:
                        std_devs = 0.0
                    else:
                        std_devs = abs(change_pct - mean_ret) / std_ret

        threshold_met = abs(change_pct) >= self.threshold_pct
        std_met = std_devs > self.std_multiplier

        info = {
            "change_pct": round(change_pct, 4),
            "std_devs": round(float(std_devs), 2),
            "threshold_met": threshold_met,
            "std_met": std_met
        }

        triggered = bool(threshold_met and std_met)
        return triggered, info


class FundingRateChecker:
    def __init__(self, threshold: float = -1.0):
        # threshold is in percentage units, e.g. -1.0 = -1%
        self.threshold = threshold

    def check(self, funding_rate: float) -> Tuple[bool, dict]:
        # Binance API returns rate as decimal (e.g. -0.00392175 = -0.392175%)
        # Convert to percentage for consistent comparison with user-set threshold
        rate_pct = funding_rate * 100
        info = {
            "funding_rate": funding_rate,
            "funding_rate_pct": rate_pct,
            "threshold": self.threshold,
            "meets_threshold": rate_pct < self.threshold
        }
        return rate_pct < self.threshold, info