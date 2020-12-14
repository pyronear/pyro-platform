import os
from dotenv import load_dotenv

# If there is an .env, load it
load_dotenv()

DEBUG: bool = os.environ.get('DEBUG', '') != 'False'
API_URL: str = os.getenv('API_URL')
API_LOGIN: str = os.getenv('API_LOGIN')
API_PWD: str = os.getenv('API_PWD')
PYRORISK_FALLBACK: str = "https://github.com/pyronear/pyro-risks/releases/download/v0.1.0-data/pyrorisk_20200901.json"
