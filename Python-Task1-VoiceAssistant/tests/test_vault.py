"""
Unit Tests for Local Encrypted Credentials Vault.
Verifies secure read, write, list, and delete actions.
"""

import os
import pytest
from pathlib import Path
from config.settings import settings
from core import vault


@pytest.fixture(autouse=True)
def setup_test_vault(tmp_path):
    """Overrides the global VAULT_DIR setting to prevent tests from modifying real keys."""
    original_vault_dir = settings.VAULT_DIR
    settings.VAULT_DIR = tmp_path / "test_nova_vault"
    yield
    settings.VAULT_DIR = original_vault_dir


def test_vault_basic_flow():
    # Save credential
    res = vault.save_credentials("test_site", "user123", "passwordABC")
    assert "saved credentials" in res

    # Retrieve credential
    creds = vault.get_credentials("test_site")
    assert creds is not None
    assert creds["username"] == "user123"
    assert creds["password"] == "passwordABC"

    # List credentials
    lst = vault.list_credentials()
    assert any(c["site"] == "test_site" for c in lst)

    # Delete credential
    del_res = vault.delete_credentials("test_site")
    assert "removed credentials" in del_res

    # Try retrieving again
    assert vault.get_credentials("test_site") is None
