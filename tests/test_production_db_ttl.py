"""Production: conversation_history must have TTL index (30 days)."""
import pytest


def test_setup_indexes_documents_ttl():
    """Database.setup_indexes must create TTL on history for 30-day retention."""
    from src.db import database
    source = open(database.__file__).read()
    assert "expireAfterSeconds" in source or "2592000" in source, \
        "setup_indexes must create TTL index on conversation_history (30 days = 2592000 seconds)"
