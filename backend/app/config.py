from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    chroma_db_path: str = "./data/chroma_db"
    chroma_collection_name: str = "meal_history"
    upload_dir: str = "./uploads"
    claude_model: str = "claude-sonnet-4-20250514"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
