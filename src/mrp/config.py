from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_dsn: str = "sqlite:///./data/mrp.sqlite"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "mrp-renders"
    artifact_root: str = "./data/renders"
    parquet_root: str = "./data/parquet"
    use_s3: bool = False


settings = Settings()
