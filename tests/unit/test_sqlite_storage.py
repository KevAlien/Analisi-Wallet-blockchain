"""
Test per src/database/sqlite.py — storage locale self-hosted.
Tutti i test usano un DB in-memory (:memory:) tramite override del DB_PATH.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

# Override DB_PATH prima di importare il modulo
_TEMP_DB = tempfile.mktemp(suffix=".db")
os.environ["DB_PATH"] = _TEMP_DB

from src.database.sqlite import (
    init_db,
    save_signal,
    get_signals,
    count_signals,
    add_wallet,
    remove_wallet,
    get_wallets,
    count_wallets,
    is_tx_processed,
    mark_tx_processed,
    cleanup_old_transactions,
    get_config,
    set_config,
    get_license_tier,
)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Ogni test parte da un DB vuoto e temporaneo."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    # Override globale: tutti i test della classe usano questo path
    import src.database.sqlite as _mod
    original = _mod.DB_PATH
    _mod.DB_PATH = db_path

    # Monkey-patch tutte le funzioni esportate con il db_path corretto
    _funcs = [
        save_signal, get_signals, count_signals,
        add_wallet, remove_wallet, get_wallets, count_wallets,
        is_tx_processed, mark_tx_processed, cleanup_old_transactions,
        get_config, set_config, get_license_tier,
    ]

    yield db_path

    _mod.DB_PATH = original


# Helper per passare db_path esplicitamente ai test
def _db(tmp_db):
    return tmp_db


class TestSignals:
    def test_save_and_retrieve(self, fresh_db):
        db = fresh_db
        save_signal({
            "signal_type": "accumulation",
            "source": "whale_tracker",
            "strength": "high",
            "confidence": 0.85,
            "chain": "ethereum",
            "wallet_address": "0xabc",
            "transaction_hash": "0xhash1",
            "value_eth": 100.0,
        }, db_path=db)

        signals = get_signals(db_path=db)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "accumulation"
        assert signals[0]["strength"] == "high"
        assert signals[0]["confidence"] == pytest.approx(0.85)

    def test_count(self, fresh_db):
        db = fresh_db
        assert count_signals(db_path=db) == 0
        save_signal({"signal_type": "distribution", "source": "whale_tracker", "strength": "low"}, db_path=db)
        save_signal({"signal_type": "accumulation", "source": "whale_tracker", "strength": "medium"}, db_path=db)
        assert count_signals(db_path=db) == 2

    def test_filter_by_type(self, fresh_db):
        db = fresh_db
        save_signal({"signal_type": "accumulation", "source": "whale_tracker", "strength": "high"}, db_path=db)
        save_signal({"signal_type": "distribution", "source": "whale_tracker", "strength": "high"}, db_path=db)

        results = get_signals(signal_type="accumulation", db_path=db)
        assert len(results) == 1
        assert results[0]["signal_type"] == "accumulation"

    def test_filter_by_chain(self, fresh_db):
        db = fresh_db
        save_signal({"signal_type": "accumulation", "source": "whale_tracker", "strength": "high", "chain": "ethereum"}, db_path=db)
        save_signal({"signal_type": "accumulation", "source": "whale_tracker", "strength": "high", "chain": "arbitrum"}, db_path=db)

        results = get_signals(chain="arbitrum", db_path=db)
        assert len(results) == 1
        assert results[0]["chain"] == "arbitrum"

    def test_filter_by_min_strength(self, fresh_db):
        db = fresh_db
        for strength in ("low", "medium", "high", "very_high"):
            save_signal({"signal_type": "accumulation", "source": "whale_tracker", "strength": strength}, db_path=db)

        results = get_signals(min_strength="high", db_path=db)
        assert len(results) == 2
        assert all(s["strength"] in ("high", "very_high") for s in results)

    def test_filter_by_since(self, fresh_db):
        db = fresh_db
        save_signal({"signal_type": "accumulation", "source": "whale_tracker", "strength": "high"}, db_path=db)
        future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        results = get_signals(since=future, db_path=db)
        assert len(results) == 0

    def test_reasoning_chain_serialized_as_list(self, fresh_db):
        db = fresh_db
        save_signal({
            "signal_type": "accumulation",
            "source": "ai_reasoning",
            "strength": "high",
            "reasoning_chain": ["step1", "step2", "step3"],
        }, db_path=db)
        results = get_signals(db_path=db)
        assert results[0]["reasoning_chain"] == ["step1", "step2", "step3"]

    def test_duplicate_id_ignored(self, fresh_db):
        db = fresh_db
        sig = {"id": "fixed-id-001", "signal_type": "accumulation", "source": "whale_tracker", "strength": "low"}
        save_signal(sig, db_path=db)
        save_signal(sig, db_path=db)  # INSERT OR IGNORE
        assert count_signals(db_path=db) == 1


class TestTrackedWallets:
    def test_add_and_list(self, fresh_db):
        db = fresh_db
        add_wallet("0xabc123", "ethereum", label="Binance Hot", db_path=db)
        wallets = get_wallets(db_path=db)
        assert len(wallets) == 1
        assert wallets[0]["address"] == "0xabc123"
        assert wallets[0]["label"] == "Binance Hot"

    def test_address_stored_lowercase(self, fresh_db):
        db = fresh_db
        add_wallet("0xABC123", "ethereum", db_path=db)
        wallets = get_wallets(db_path=db)
        assert wallets[0]["address"] == "0xabc123"

    def test_count(self, fresh_db):
        db = fresh_db
        assert count_wallets(db_path=db) == 0
        add_wallet("0x111", "ethereum", db_path=db)
        add_wallet("0x222", "arbitrum", db_path=db)
        assert count_wallets(db_path=db) == 2

    def test_remove(self, fresh_db):
        db = fresh_db
        add_wallet("0xaaa", "ethereum", db_path=db)
        remove_wallet("0xaaa", "ethereum", db_path=db)
        assert count_wallets(db_path=db) == 0

    def test_duplicate_ignored(self, fresh_db):
        db = fresh_db
        add_wallet("0xaaa", "ethereum", db_path=db)
        add_wallet("0xaaa", "ethereum", db_path=db)  # INSERT OR IGNORE
        assert count_wallets(db_path=db) == 1

    def test_filter_by_chain(self, fresh_db):
        db = fresh_db
        add_wallet("0x111", "ethereum", db_path=db)
        add_wallet("0x222", "arbitrum", db_path=db)
        results = get_wallets(chain="ethereum", db_path=db)
        assert len(results) == 1
        assert results[0]["chain"] == "ethereum"


class TestProcessedTransactions:
    def test_not_processed_initially(self, fresh_db):
        db = fresh_db
        assert not is_tx_processed("0xhash", "ethereum", db_path=db)

    def test_mark_and_check(self, fresh_db):
        db = fresh_db
        mark_tx_processed("0xhash", "ethereum", db_path=db)
        assert is_tx_processed("0xhash", "ethereum", db_path=db)

    def test_same_hash_different_chain(self, fresh_db):
        db = fresh_db
        mark_tx_processed("0xhash", "ethereum", db_path=db)
        assert not is_tx_processed("0xhash", "arbitrum", db_path=db)

    def test_duplicate_mark_ignored(self, fresh_db):
        db = fresh_db
        mark_tx_processed("0xhash", "ethereum", db_path=db)
        mark_tx_processed("0xhash", "ethereum", db_path=db)  # INSERT OR IGNORE
        assert is_tx_processed("0xhash", "ethereum", db_path=db)

    def test_cleanup_removes_old(self, fresh_db):
        db = fresh_db
        # Inserisci una transazione con data passata
        from src.database.sqlite import get_connection
        with get_connection(db) as con:
            con.execute(
                "INSERT INTO processed_transactions (tx_hash, chain, processed_at) VALUES (?,?,?)",
                ("0xold", "ethereum", (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=31)).isoformat()),
            )
        mark_tx_processed("0xnew", "ethereum", db_path=db)

        deleted = cleanup_old_transactions(days=30, db_path=db)
        assert deleted == 1
        assert not is_tx_processed("0xold", "ethereum", db_path=db)
        assert is_tx_processed("0xnew", "ethereum", db_path=db)


class TestUserConfig:
    def test_default_values_exist(self, fresh_db):
        db = fresh_db
        val = get_config("dry_run", db_path=db)
        assert val == "true"

    def test_set_and_get(self, fresh_db):
        db = fresh_db
        set_config("my_key", "my_value", db_path=db)
        assert get_config("my_key", db_path=db) == "my_value"

    def test_override(self, fresh_db):
        db = fresh_db
        set_config("dry_run", "false", db_path=db)
        assert get_config("dry_run", db_path=db) == "false"

    def test_missing_key_returns_default(self, fresh_db):
        db = fresh_db
        val = get_config("nonexistent", default="fallback", db_path=db)
        assert val == "fallback"


class TestLicense:
    def test_default_tier_is_free(self, fresh_db):
        db = fresh_db
        assert get_license_tier(db_path=db) == "free"

    def test_pro_license_activates(self, fresh_db):
        db = fresh_db
        from src.database.sqlite import get_connection
        with get_connection(db) as con:
            con.execute(
                "INSERT INTO license (key_hash, tier, activated_at) VALUES (?,?,?)",
                ("abc123hash", "pro", datetime.now(timezone.utc).replace(tzinfo=None).isoformat()),
            )
        assert get_license_tier(db_path=db) == "pro"

    def test_expired_license_ignored(self, fresh_db):
        db = fresh_db
        from src.database.sqlite import get_connection
        with get_connection(db) as con:
            con.execute(
                "INSERT INTO license (key_hash, tier, activated_at, expires_at) VALUES (?,?,?,?)",
                (
                    "expired_hash", "pro",
                    (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=60)).isoformat(),
                    (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).isoformat(),
                ),
            )
        assert get_license_tier(db_path=db) == "free"
