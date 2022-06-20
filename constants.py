from pathlib import Path

APP_NAME = 'mrsh'
LATEST_VERSION = '0.0.5'
USERCONTENT_PATH = Path('~').expanduser() / 'Documents' / 'Static' / 'usercontent'
PFP_PATH = USERCONTENT_PATH / 'profile_pictures'
PFP_URL = 'https://sovamor.co/usercontent/profile_pictures'
CHAT_IMAGE_PATH = USERCONTENT_PATH / 'chat_images'
CHAT_IMAGE_URL = 'https://sovamor.co/usercontent/chat_images'

API_URL = f'https://sovamor.co/{APP_NAME}/api'
