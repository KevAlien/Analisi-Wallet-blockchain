"""
SentryCage è open source e gratuito: tutte le feature sono sempre sbloccate.

Questo modulo esiste ancora solo per compatibilità con il resto del codice
(chi importava `get_active_features`/`get_trial_status` continua a funzionare),
ma non c'è più alcun gating Free/Pro, nessuna chiamata a server esterni e
nessun trial a tempo.
"""
from __future__ import annotations

from src.config.features import FeatureSet, get_pro_features
from src.database.sqlite import DB_PATH


def get_active_features(db_path: str = DB_PATH) -> FeatureSet:
    """Restituisce sempre il set completo di feature: SentryCage è gratuito per tutti."""
    return get_pro_features()


def get_trial_status(db_path: str = DB_PATH) -> dict:
    """Mantenuto per compatibilità: non esiste più alcun trial, tutto è già sbloccato."""
    return {
        "tier": "open-source",
        "trial_active": False,
        "trial_days_remaining": None,
        "is_pro": True,
    }
