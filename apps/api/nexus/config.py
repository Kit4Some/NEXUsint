"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Application ---
    app_name: str = "NEXUS OSINT Platform"
    debug: bool = False

    # --- Neo4j ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "nexus_secret_2025"

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "nexus"
    postgres_user: str = "nexus"
    postgres_password: str = "nexus_pg_secret"
    postgres_dsn: str = ""  # Override via POSTGRES_DSN env var; if empty, built from components

    def get_postgres_dsn(self) -> str:
        if self.postgres_dsn:
            return self.postgres_dsn
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Elasticsearch ---
    elasticsearch_url: str = "http://localhost:9200"

    # --- Kafka ---
    kafka_bootstrap_servers: str = "localhost:9092"

    # --- MinIO ---
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "nexus_minio"
    minio_secret_key: str = "nexus_minio_secret"

    # --- JWT ---
    jwt_secret: str = ""  # REQUIRED — set via JWT_SECRET env var
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # --- Security ---
    audit_log_enabled: bool = True
    password_min_length: int = 12

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # --- CYBINT API Keys ---
    shodan_api_key: str = ""
    virustotal_api_key: str = ""
    abuseipdb_api_key: str = ""
    alienvault_otx_api_key: str = ""
    securitytrails_api_key: str = ""

    # --- SOCMINT API Keys ---
    twitter_bearer_token: str = ""
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""

    # --- SIGINT API Keys ---
    opensky_username: str = ""
    opensky_password: str = ""
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    ais_api_key: str = ""

    # --- Live Feed ---
    live_feed_enabled: bool = False
    live_feed_fast_interval: int = 60
    live_feed_slow_interval: int = 300
    ais_api_url: str = "https://api.aisstream.io"

    # --- GEOINT ---
    copernicus_client_id: str = ""
    copernicus_client_secret: str = ""
    nominatim_user_agent: str = "NEXUS-OSINT/0.1"
    geoip_db_path: str = ""  # Path to MaxMind GeoLite2-City.mmdb

    # --- LLM ---
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]
