import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve the project root (two levels up from src/config/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_config():
    # Load base/local env first if it exists
    load_dotenv(BASE_DIR / '.env.local')

    env = os.environ.get('APP_ENV', 'development').lower()

    if env == 'production':
        load_dotenv(BASE_DIR / '.env.production', override=True)
        from .production import ProductionConfig as Config
    elif env == 'staging':
        load_dotenv(BASE_DIR / '.env.staging', override=True)
        from .staging import StagingConfig as Config
    else:
        load_dotenv(BASE_DIR / '.env.development', override=True)
        from .development import DevelopmentConfig as Config

    return Config
