"""
SentryCage è open source e gratuito: nessun feature gating, nessun tier Pro.

Questo modulo definisce un unico FeatureSet con tutto sbloccato, ed è mantenuto
per compatibilità con il resto del codice che importa `FeatureSet`/`get_pro_features`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ============================================================
# Chain e strategie supportate — tutte disponibili per tutti
# ============================================================

ALL_CHAINS = {
    "ethereum", "arbitrum", "optimism", "base", "polygon",
    "bnb", "avalanche", "fantom", "zksync", "linea",
    # + tutte le chain Etherscan V2 — estendibile liberamente
}

ALL_STRATEGIES = {
    "accumulation",         # whale accumula su wallet noto
    "distribution",         # whale distribuisce / vende
    "exchange_deposit",     # deposito verso exchange (potenziale sell)
    "exchange_withdrawal",  # prelievo da exchange (potenziale buy)
    "transfer",             # large transfer tra wallet
    "unusual_activity",     # pattern anomalo rilevato
}

SIGNAL_HISTORY_DAYS = None  # illimitato per tutti


# ============================================================
# Feature set unico (nessun gating)
# ============================================================

@dataclass(frozen=True)
class FeatureSet:
    tier: str
    chains: set[str]
    strategies: set[str]
    ai_reasoning: bool
    custom_thresholds: bool
    signal_history_days: Optional[int]   # None = illimitato
    is_trial: bool = False
    trial_days_remaining: Optional[int] = None

    def allows_chain(self, chain: str) -> bool:
        return chain.lower() in self.chains

    def allows_strategy(self, strategy: str) -> bool:
        return strategy.lower() in self.strategies

    @property
    def display_tier(self) -> str:
        return "Open Source (tutto sbloccato)"


def get_free_features() -> FeatureSet:
    """Mantenuto per compatibilità: restituisce lo stesso set completo di get_pro_features()."""
    return get_pro_features()


def get_pro_features(
    is_trial: bool = False,
    trial_days_remaining: Optional[int] = None,
) -> FeatureSet:
    return FeatureSet(
        tier="open-source",
        chains=ALL_CHAINS,
        strategies=ALL_STRATEGIES,
        ai_reasoning=True,
        custom_thresholds=True,
        signal_history_days=SIGNAL_HISTORY_DAYS,
    )
