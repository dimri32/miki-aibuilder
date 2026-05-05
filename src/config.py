# python imports
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # <realtime_streaming> directory
TENANT_DIR = BASE_DIR / "tenants"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        protected_namespaces=("settings_",),  # merged here
        env_file=BASE_DIR / ".env",
        env_file_encoding='utf-8',
        extra="ignore",
    )

    # Add your environment variables here
    log_level: str = "INFO"
    
    model_version: str = "v2"

    HF_TOKEN: str = ""
    MODEL_ID: str = ""

    EMBEEDING_HF_TOKEN: str = ""
    EMBEDDING_MODEL_ID: str = ""

    OPENAI_API_KEY: str = ""

    ASTRAV_DB_API_ENDPOINT: str = ""
    ASTRAV_DB_APPLICATION_TOKEN: str = ""
    ASTRAV_VECTOR_COLLECTION: str = "document_collection"
    keyspace: str = "ironclad" 
    DIM: int = 512

    MIXBREAD_EMBED_MODEL: str = "tei-embeddings"
    MIXBREAD_EMBED_DIM: int = 1024
    PREWARM_EMBEDDER: str = 'true'

    MIKI_API_URL: str = ""
    MIKI_API_USERNAME: str = ""
    MIKI_API_PASSWORD: str = ""

confy = Settings()