# A mock database client initializing with the environment configuration
from src.config import load_config

config = load_config()

def get_db_url():
    return config.DATABASE_URL

def init_db():
    print(f"[DB] Initializing database connection at {get_db_url()} (Env: {config.__name__})")
    # Here we would initialize SQLAlchemy or PyMySQL
