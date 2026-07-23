import os

class StagingConfig:
    DEBUG = False
    TESTING = True
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    BANK_PUBLIC_BASE = os.environ.get('BANK_PUBLIC_BASE', 'http://bank.staging.domain.com')
    MERCHANT_ACCOUNT = os.environ.get('MERCHANT_ACCOUNT', 'cloudchasers')
    ENABLE_BETA_FEATURES = True
