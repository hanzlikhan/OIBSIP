"""
Local Encrypted Credentials Vault for Nova 2.1.
Protects user passwords and logins using AES-256 Fernet encryption.
Stores credentials in a local user profile file (~/.nova/vault.json)
so they are only accessible to the active operating system user.
"""

import os
import json
import sys
from pathlib import Path
from cryptography.fernet import Fernet

from config.settings import settings

def _get_vault_dir() -> Path:
    return settings.VAULT_DIR

def _get_vault_key_path() -> Path:
    return _get_vault_dir() / "vault.key"

def _get_vault_data_path() -> Path:
    return _get_vault_dir() / "vault.json"


def _ensure_vault_setup():
    """Ensure the vault folder, key, and data file exist with safe permissions."""
    vault_dir = _get_vault_dir()
    key_path = _get_vault_key_path()
    data_path = _get_vault_data_path()
    try:
        vault_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure only the owner can read/write the directory (Unix/Mac compatibility)
        if hasattr(os, "chmod"):
            os.chmod(str(vault_dir), 0o700)

        # Generate encryption key if not exists
        if not key_path.exists():
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            if hasattr(os, "chmod"):
                os.chmod(str(key_path), 0o600)
        
        # Initialize empty vault file if not exists
        if not data_path.exists():
            _write_raw_vault({})
            if hasattr(os, "chmod"):
                os.chmod(str(data_path), 0o600)
    except Exception as e:
        print(f"[Vault] Setup error: {e}", file=sys.stderr)


def _get_fernet() -> Fernet:
    """Load the encryption key and initialize the Fernet engine."""
    _ensure_vault_setup()
    key_path = _get_vault_key_path()
    try:
        key = key_path.read_bytes()
        return Fernet(key)
    except Exception as e:
        # Fallback key generation if there's a file error
        print(f"[Vault] Key loading error: {e}. Re-generating key.", file=sys.stderr)
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        return Fernet(key)


def _read_raw_vault() -> dict:
    """Read and decrypt the vault file."""
    _ensure_vault_setup()
    data_path = _get_vault_data_path()
    if not data_path.exists():
        return {}

    try:
        encrypted_data = data_path.read_bytes()
        if not encrypted_data:
            return {}
        
        f = _get_fernet()
        decrypted_data = f.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode("utf-8"))
    except Exception as e:
        # If decryption fails (e.g. invalid key/corrupted file), start clean
        print(f"[Vault] Decryption failed: {e}. Initializing fresh vault.", file=sys.stderr)
        return {}


def _write_raw_vault(data: dict):
    """Encrypt and write data to the vault file."""
    _ensure_vault_setup()
    data_path = _get_vault_data_path()
    try:
        f = _get_fernet()
        bytes_data = json.dumps(data).encode("utf-8")
        encrypted_data = f.encrypt(bytes_data)
        data_path.write_bytes(encrypted_data)
    except Exception as e:
        print(f"[Vault] Write error: {e}", file=sys.stderr)


# ── Public APIs ─────────────────────────────────────────────────────────────

def save_credentials(site: str, username: str, password: str) -> str:
    """Save or update login credentials for a specific site."""
    site_key = site.strip().lower()
    if not site_key or not username or not password:
        return "Failed: Site name, username, and password are required."
    
    vault = _read_raw_vault()
    vault[site_key] = {
        "username": username.strip(),
        "password": password
    }
    _write_raw_vault(vault)
    return f"Successfully saved credentials for '{site}' to local vault."


def get_credentials(site: str) -> dict:
    """
    Retrieve credentials for a specific site.
    Returns: {"username": "...", "password": "..."} or None if not found.
    """
    site_key = site.strip().lower()
    vault = _read_raw_vault()
    return vault.get(site_key, None)


def delete_credentials(site: str) -> str:
    """Remove credentials for a specific site."""
    site_key = site.strip().lower()
    vault = _read_raw_vault()
    
    if site_key in vault:
        del vault[site_key]
        _write_raw_vault(vault)
        return f"Successfully removed credentials for '{site}' from vault."
    return f"No credentials found for '{site}' in vault."


def list_credentials() -> list:
    """Return a list of registered sites (usernames visible, passwords hidden)."""
    vault = _read_raw_vault()
    result = []
    for site, info in vault.items():
        result.append({
            "site": site,
            "username": info.get("username", "Unknown")
        })
    return result
