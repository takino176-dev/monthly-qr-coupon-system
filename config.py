import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change_this_to_a_secure_random_key_in_production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///coupons')
    SQLALCHEMY_TRACK_MODIFICATIONS = False