"""
Test per il FeatureSet open source: nessun gating Free/Pro, tutto sbloccato.

SentryCage è ora 100% gratuito — questi test verificano che get_free_features(),
get_pro_features() e get_active_features() restituiscano sempre lo stesso set
completo di feature, senza distinzioni di tier o trial a tempo.
"""
from src.config.features import (
    get_free_features,
    get_pro_features,
    ALL_CHAINS,
    ALL_STRATEGIES,
)


# ============================================================
# FeatureSet — tutto sbloccato
# ============================================================

class TestOpenSourceFeatures:
    def test_ethereum_allowed(self):
        f = get_free_features()
        assert f.allows_chain("ethereum")

    def test_arbitrum_allowed(self):
        f = get_free_features()
        assert f.allows_chain("arbitrum")

    def test_all_chains_allowed(self):
        f = get_pro_features()
        for chain in ("ethereum", "arbitrum", "polygon", "base"):
            assert f.allows_chain(chain)

    def test_core_strategies_allowed(self):
        f = get_free_features()
        for s in ALL_STRATEGIES:
            assert f.allows_strategy(s), f"Strategia '{s}' dovrebbe essere sempre disponibile"

    def test_all_strategies_allowed(self):
        f = get_pro_features()
        for s in ALL_STRATEGIES:
            assert f.allows_strategy(s)

    def test_ai_reasoning_on(self):
        assert get_free_features().ai_reasoning
        assert get_pro_features().ai_reasoning

    def test_signal_history_unlimited(self):
        assert get_free_features().signal_history_days is None
        assert get_pro_features().signal_history_days is None

    def test_display_tier(self):
        assert "Open Source" in get_free_features().display_tier
        assert "Open Source" in get_pro_features().display_tier

    def test_free_and_pro_are_equivalent(self):
        """Nel modello open source, get_free_features() e get_pro_features()
        restituiscono lo stesso set completo di feature."""
        free = get_free_features()
        pro = get_pro_features()
        assert free.chains == pro.chains
        assert free.strategies == pro.strategies
        assert free.ai_reasoning == pro.ai_reasoning


# ============================================================
# get_active_features — sempre tutto sbloccato, nessun trial
# ============================================================

class TestActiveFeatures:
    def test_active_features_always_full(self, tmp_path):
        from src.database.sqlite import init_db
        from src.config.license import get_active_features

        db = str(tmp_path / "test.db")
        init_db(db)

        features = get_active_features(db_path=db)
        assert features.ai_reasoning is True
        assert features.signal_history_days is None
        for chain in ALL_CHAINS:
            assert features.allows_chain(chain)

    def test_trial_status_reports_no_trial(self, tmp_path):
        from src.database.sqlite import init_db
        from src.config.license import get_trial_status

        db = str(tmp_path / "test.db")
        init_db(db)

        status = get_trial_status(db_path=db)
        assert status["trial_active"] is False
        assert status["is_pro"] is True
