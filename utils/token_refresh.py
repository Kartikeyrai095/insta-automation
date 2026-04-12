"""
Instagram access token auto-refresh utility.
Long-lived tokens expire every 60 days; this refreshes them at day 50.
Optionally updates the GitHub Actions secret.
"""

from __future__ import annotations

import os
import requests
from datetime import datetime, timezone

from config.settings import (
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_API_VERSION,
    GH_TOKEN,
    GH_REPO,
)
from utils.logger import get_logger

logger = get_logger("token_refresh")


def refresh_instagram_token() -> str | None:
    """
    Refresh the Instagram long-lived access token.

    Returns:
        New access token string, or None on failure.
    """
    if not INSTAGRAM_ACCESS_TOKEN:
        logger.warning("No Instagram access token configured, skipping refresh")
        return None

    url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "ig_exchange_token",
        "client_secret": os.environ.get("INSTAGRAM_APP_SECRET", ""),
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        new_token = data.get("access_token")
        expires_in = data.get("expires_in", 0)

        if new_token:
            logger.info(f"Token refreshed successfully, expires in {expires_in // 86400} days")
            return new_token
        else:
            logger.error(f"Token refresh response missing access_token: {data}")
            return None

    except requests.RequestException as e:
        logger.error(f"Token refresh failed: {e}")
        return None


def update_github_secret(secret_name: str, secret_value: str) -> bool:
    """
    Update a GitHub Actions secret.
    Requires GH_TOKEN with 'repo' scope and the PyNaCl library.

    Args:
        secret_name: Name of the secret to update.
        secret_value: New value for the secret.

    Returns:
        True if update was successful.
    """
    if not GH_TOKEN or not GH_REPO:
        logger.warning("GitHub token or repo not configured, cannot update secret")
        return False

    try:
        from nacl import encoding, public as nacl_public

        headers = {
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Get the repo public key
        key_url = f"https://api.github.com/repos/{GH_REPO}/actions/secrets/public-key"
        key_response = requests.get(key_url, headers=headers, timeout=30)
        key_response.raise_for_status()
        key_data = key_response.json()

        public_key = nacl_public.PublicKey(
            key_data["key"].encode("utf-8"),
            encoding.Base64Encoder,
        )
        sealed_box = nacl_public.SealedBox(public_key)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_b64 = encoding.Base64Encoder.encode(encrypted).decode("utf-8")

        # Update the secret
        secret_url = f"https://api.github.com/repos/{GH_REPO}/actions/secrets/{secret_name}"
        payload = {
            "encrypted_value": encrypted_b64,
            "key_id": key_data["key_id"],
        }
        put_response = requests.put(
            secret_url, headers=headers, json=payload, timeout=30
        )
        put_response.raise_for_status()
        logger.info(f"GitHub secret '{secret_name}' updated successfully")
        return True

    except ImportError:
        logger.warning("PyNaCl not installed, cannot encrypt GitHub secrets")
        return False
    except Exception as e:
        logger.error(f"Failed to update GitHub secret: {e}")
        return False


def auto_refresh_if_needed() -> None:
    """Check if token needs refresh and do it automatically."""
    new_token = refresh_instagram_token()
    if new_token and new_token != INSTAGRAM_ACCESS_TOKEN:
        update_github_secret("INSTAGRAM_ACCESS_TOKEN", new_token)
        # Also update in current environment
        os.environ["INSTAGRAM_ACCESS_TOKEN"] = new_token
        logger.info("Token refreshed and environment updated")
