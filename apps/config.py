"""Configuration management for Muse Protocol."""

import os
from typing import Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class ClickHouseConfig(BaseModel):
    """ClickHouse connection configuration."""
    host: str = Field(..., description="ClickHouse host")
    port: int = Field(default=9000, description="ClickHouse port")
    user: str = Field(..., description="ClickHouse username")
    password: str = Field(default="", description="ClickHouse password")
    database: str = Field(..., description="ClickHouse database name")


class DatadogConfig(BaseModel):
    """Datadog API configuration."""
    api_key: str = Field(..., description="Datadog API key")
    app_key: str = Field(..., description="Datadog application key")
    site: str = Field(default="datadoghq.com", description="Datadog site")


class DeepLConfig(BaseModel):
    """DeepL translation API configuration."""
    api_key: str = Field(..., description="DeepL API key")
    api_url: str = Field(default="https://api-free.deepl.com/v2", description="DeepL API URL")


class RepoConfig(BaseModel):
    """Repository configuration."""
    path: str = Field(default=".", description="Repository path")
    branch: str = Field(default="main", description="Git branch")
    author_name: str = Field(..., description="Git author name")
    author_email: str = Field(..., description="Git author email")


class AgentConfig(BaseModel):
    """Agent configuration."""
    model: str = Field(default="gpt-4", description="LLM model name")
    max_tokens: int = Field(default=4000, description="Maximum tokens")
    temperature: float = Field(default=0.7, description="Model temperature")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format")


class Config(BaseModel):
    """Main configuration class."""
    clickhouse: ClickHouseConfig
    datadog: DatadogConfig
    deepl: DeepLConfig
    repo: RepoConfig
    agent: AgentConfig
    logging: LoggingConfig

    @validator('logging')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v.level}")
        return v


def load_config(env_file: Optional[str] = None) -> Config:
    """Load configuration from environment variables.

    Args:
        env_file: Optional path to .env file

    Returns:
        Config: Validated configuration object

    Raises:
        ValueError: If required environment variables are missing
    """
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    try:
        return Config(
            clickhouse=ClickHouseConfig(
                host=os.getenv("CH_HOST", ""),
                port=int(os.getenv("CH_PORT", "9000")),
                user=os.getenv("CH_USER", ""),
                password=os.getenv("CH_PASSWORD", ""),
                database=os.getenv("CH_DATABASE", "")
            ),
            datadog=DatadogConfig(
                api_key=os.getenv("DD_API_KEY", ""),
                app_key=os.getenv("DD_APP_KEY", ""),
                site=os.getenv("DD_SITE", "datadoghq.com")
            ),
            deepl=DeepLConfig(
                api_key=os.getenv("DEEPL_API_KEY", ""),
                api_url=os.getenv("DEEPL_API_URL", "https://api-free.deepl.com/v2")
            ),
            repo=RepoConfig(
                path=os.getenv("REPO_PATH", "."),
                branch=os.getenv("REPO_BRANCH", "main"),
                author_name=os.getenv("REPO_AUTHOR_NAME", ""),
                author_email=os.getenv("REPO_AUTHOR_EMAIL", "")
            ),
            agent=AgentConfig(
                model=os.getenv("AGENT_MODEL", "gpt-4"),
                max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("AGENT_TEMPERATURE", "0.7"))
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "json")
            )
        )
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def validate_required_env_vars() -> None:
    """Validate that all required environment variables are present.

    Raises:
        ValueError: If any required variables are missing
    """
    required_vars = [
        "CH_HOST", "CH_USER", "CH_DATABASE",
        "DD_API_KEY", "DD_APP_KEY",
        "DEEPL_API_KEY",
        "REPO_AUTHOR_NAME", "REPO_AUTHOR_EMAIL"
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}. "
            f"Please copy env.sample to .env and fill in the values."
        )

