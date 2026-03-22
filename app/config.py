from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # Chroma 配置
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_persist_directory: str = "/chroma_data"
    
    # 千问 API 配置
    dashscope_api_key: Optional[str] = None
    qwen_embedding_model: str = "text-embedding-v2"
    
    # 向量库配置
    collection_name: str = "medical_books"
    
    # 文本处理配置
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
