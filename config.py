"""Configuration centrale de l'application"""
import os
from pathlib import Path
import httpx  # Ajout de l'import manquant

class Config:
    """Configuration de base"""
    # Chemins
    PROJECT_ROOT = Path(__file__).parent.parent.resolve()
    DB_PATH = str(PROJECT_ROOT / "data/teleSuche_data")
    I18N_DIR = str(PROJECT_ROOT / "i18n")
    LOG_DIR = str(PROJECT_ROOT / "logs")
    
    # Tokens
    MAIN_BOT_TOKEN = "7794487631:AAG8Du5ajsGf0FTcJUUrkYEr86pwMO1f9eg"
    PDG_BOT_TOKEN = "7728919174:AAFsGWdqSdzdYErou1FO4Om3vbNs2QCPyX8"
    
    # Identifiants
    ADMIN_IDS = [1263139963]
    PDG_BOT_ID = 7728919174
    PDG_USER_ID = [1001157044]
    
    # Paramètres de validation
    TOKEN_VALIDATION_TIMEOUT = 60  # Secondes
    VALIDATE_TOKENS = True
    MAX_TOKEN_RETRIES = 3
    
    # Debug
    DEBUG_MODE = True
    LOG_LEVEL = "DEBUG"

    @property
    def http_timeout(self):
        return httpx.Timeout(self.TOKEN_VALIDATION_TIMEOUT)

class ProductionConfig(Config):
    """Configuration de production"""
    DEBUG_MODE = False
    LOG_LEVEL = "INFO"

config = ProductionConfig() if os.getenv('ENV') == 'PRODUCTION' else Config()