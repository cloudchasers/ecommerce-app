import os
from dotenv import load_dotenv

def load_config():
    # Load base/local env first if it exists
    load_dotenv('.env.local')
    
    env = os.environ.get('APP_ENV', 'development').lower()
    
    if env == 'production':
        load_dotenv('.env.production', override=True)
        from .production import ProductionConfig as Config
    elif env == 'staging':
        load_dotenv('.env.staging', override=True)
        from .staging import StagingConfig as Config
    else:
        load_dotenv('.env.development', override=True)
        from .development import DevelopmentConfig as Config
        
    return Config
