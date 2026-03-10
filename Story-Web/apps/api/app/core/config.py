from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Story AI Platform API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Clerk
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""
    
    # Databases
    DATABASE_URL: str = ""
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI Endpoints
    OLLAMA_GEN_HOST: str = "http://222.253.80.30:11434"
    OLLAMA_MODEL_GEN: str = "gpt-oss:120b-cloud"
    OLLAMA_EMBED_HOST: str = "http://222.253.80.30:11434/api/embeddings"
    OLLAMA_MODEL_EMBED: str = "bge-m3:567m"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
