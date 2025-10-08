"""Secrets management for Muse Protocol.

Supports multiple backends:
- Environment variables (default)
- Azure Key Vault
- AWS Secrets Manager
- Doppler
"""

import logging
import os
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class SecretsBackend(Enum):
    """Supported secrets backends."""
    ENV = "env"
    AZURE_KEYVAULT = "azure_keyvault"
    AWS_SECRETS = "aws_secrets"
    DOPPLER = "doppler"


class SecretsManager:
    """Unified secrets manager."""

    def __init__(self, backend: Optional[SecretsBackend] = None):
        """Initialize secrets manager.

        Args:
            backend: Secrets backend to use (default: ENV)
        """
        self.backend = backend or SecretsBackend.ENV
        self._client = None
        self._init_backend()

    def _init_backend(self):
        """Initialize the secrets backend."""
        if self.backend == SecretsBackend.AZURE_KEYVAULT:
            self._init_azure()
        elif self.backend == SecretsBackend.AWS_SECRETS:
            self._init_aws()
        elif self.backend == SecretsBackend.DOPPLER:
            self._init_doppler()
        else:
            logger.info("Using environment variables for secrets")

    def _init_azure(self):
        """Initialize Azure Key Vault client."""
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential

            vault_url = os.getenv("AZURE_KEYVAULT_URL")
            if not vault_url:
                raise ValueError("AZURE_KEYVAULT_URL not set")

            credential = DefaultAzureCredential()
            self._client = SecretClient(
                vault_url=vault_url,
                credential=credential
            )
            logger.info(f"Initialized Azure Key Vault: {vault_url}")

        except ImportError:
            logger.error(
                "Azure SDK not installed. "
                "Install: pip install azure-keyvault-secrets azure-identity"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault: {e}")
            raise

    def _init_aws(self):
        """Initialize AWS Secrets Manager client."""
        try:
            import boto3

            region = os.getenv("AWS_REGION", "us-east-1")
            self._client = boto3.client(
                "secretsmanager",
                region_name=region
            )
            logger.info(f"Initialized AWS Secrets Manager: {region}")

        except ImportError:
            logger.error(
                "AWS SDK not installed. Install: pip install boto3"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager: {e}")
            raise

    def _init_doppler(self):
        """Initialize Doppler client."""
        try:
            import requests

            self.doppler_token = os.getenv("DOPPLER_TOKEN")
            if not self.doppler_token:
                raise ValueError("DOPPLER_TOKEN not set")

            self._client = {
                "base_url": "https://api.doppler.com/v3",
                "token": self.doppler_token
            }
            logger.info("Initialized Doppler secrets")

        except ImportError:
            logger.error("requests not installed. Install: pip install requests")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Doppler: {e}")
            raise

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value.

        Args:
            key: Secret key/name
            default: Default value if not found

        Returns:
            Secret value or default
        """
        try:
            if self.backend == SecretsBackend.AZURE_KEYVAULT:
                return self._get_azure_secret(key, default)
            elif self.backend == SecretsBackend.AWS_SECRETS:
                return self._get_aws_secret(key, default)
            elif self.backend == SecretsBackend.DOPPLER:
                return self._get_doppler_secret(key, default)
            else:
                return os.getenv(key, default)

        except Exception as e:
            logger.error(f"Failed to get secret {key}: {e}")
            return default

    def _get_azure_secret(self, key: str, default: Optional[str]) -> Optional[str]:
        """Get secret from Azure Key Vault."""
        try:
            secret = self._client.get_secret(key)
            return secret.value
        except Exception as e:
            logger.warning(f"Azure secret {key} not found: {e}")
            return default

    def _get_aws_secret(self, key: str, default: Optional[str]) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            response = self._client.get_secret_value(SecretId=key)
            return response["SecretString"]
        except Exception as e:
            logger.warning(f"AWS secret {key} not found: {e}")
            return default

    def _get_doppler_secret(self, key: str, default: Optional[str]) -> Optional[str]:
        """Get secret from Doppler."""
        try:
            import requests

            response = requests.get(
                f"{self._client['base_url']}/configs/config/secrets",
                headers={"Authorization": f"Bearer {self._client['token']}"},
                params={"project": os.getenv("DOPPLER_PROJECT", "muse")}
            )
            response.raise_for_status()

            secrets = response.json()
            return secrets.get(key, default)

        except Exception as e:
            logger.warning(f"Doppler secret {key} not found: {e}")
            return default

    def get_all_secrets(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with optional prefix filter.

        Args:
            prefix: Optional prefix to filter secrets

        Returns:
            Dictionary of secret key-value pairs
        """
        if self.backend == SecretsBackend.ENV:
            return {
                k: v for k, v in os.environ.items()
                if k.startswith(prefix)
            }
        else:
            logger.warning(
                "get_all_secrets not implemented for "
                f"{self.backend.value}"
            )
            return {}


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def init_secrets(backend: Optional[SecretsBackend] = None):
    """Initialize global secrets manager.

    Args:
        backend: Secrets backend to use
    """
    global _secrets_manager
    _secrets_manager = SecretsManager(backend)


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a secret from the global secrets manager.

    Args:
        key: Secret key
        default: Default value if not found

    Returns:
        Secret value or default
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager.get_secret(key, default)
