import logging
logger = logging.getLogger(__name__)
# security.py - Gestionnaire complet de sécurité

import logging
import hashlib
import secrets
import re
from typing import Optional, Dict, Any
from config import Config
import time

logger = logging.getLogger(__name__)

class SecurityManager:
    """Gestion centralisée de la sécurité avec protection contre les abus"""
    
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.login_attempts = {}
        self.locked_accounts = {}
        
    async def check_message(self, update, context) -> bool:
        """
        Vérifie la sécurité d'un message entrant
        Retourne False pour bloquer le message
        """
        try:
            user_id = update.effective_user.id
            message = update.effective_message
            
            # 1. Vérification des permissions de base
            if await self._basic_permission_check(update, context):
                return True
                
            # 2. Filtrage de contenu
            if self._contains_malicious_content(message.text or message.caption):
                logger.warning(f"Contenu malveillant détecté de {user_id}")
                return False
                
            # 3. Vérification du spam
            if self._is_spam(user_id):
                logger.warning(f"Compte spammé détecté: {user_id}")
                return False
                
            # 4. Vérification des comptes verrouillés
            if self.is_account_locked(user_id):
                logger.warning(f"Compte verrouillé tenté: {user_id}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Erreur de sécurité: {e}")
            return False

    async def _basic_permission_check(self, update, context) -> bool:
        """Vérifie les permissions basiques"""
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        
        # Messages privés toujours autorisés
        if chat_type == 'private':
            return True
            
        # Dans les groupes, seuls les admins peuvent envoyer des commandes
        if chat_type in ['group', 'supergroup']:
            if update.effective_message.text and update.effective_message.text.startswith('/'):
                member = await context.bot.get_chat_member(
                    update.effective_chat.id,
                    user_id
                )
                return member.status in ['administrator', 'creator']
            return True
            
        return False

    def _contains_malicious_content(self, text: Optional[str]) -> bool:
        """Détecte les contenus potentiellement malveillants"""
        if not text:
            return False
            
        # Liste de motifs suspects
        malicious_patterns = [
            r"(?i)http[s]?://[^\s]+",  # URLs
            r"@[^\s]+",                 # Mentions
            r"<script>",                # Balises script
            r"eval\(",                  # Fonctions eval
            r"php",                     # Langage serveur
            r"\b(?:viagra|cialis)\b",   # Spam classique
            r"\b(?:bitcoin|crypto)\b"   # Cryptomonnaies
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, text):
                return True
                
        return False

    def _is_spam(self, user_id: int) -> bool:
        """Détecte les comportements de spam"""
        now = time.time()
        
        # Initialiser le suivi
        if user_id not in self.login_attempts:
            self.login_attempts[user_id] = {'count': 0, 'timestamp': now}
            return False
            
        # Réinitialiser si plus de 5 minutes se sont écoulées
        if now - self.login_attempts[user_id]['timestamp'] > 300:
            self.login_attempts[user_id] = {'count': 0, 'timestamp': now}
            return False
            
        # Vérifier le nombre de tentatives
        self.login_attempts[user_id]['count'] += 1
        
        # Bloquer si plus de 10 tentatives en 5 minutes
        if self.login_attempts[user_id]['count'] > 10:
            self.lock_account(user_id)
            return True
            
        return False

    def lock_account(self, user_id: int, duration: int = 3600) -> None:
        """Verrouille un compte temporairement"""
        self.locked_accounts[user_id] = time.time() + duration
        logger.warning(f"Compte {user_id} verrouillé pour {duration}s")

    def unlock_account(self, user_id: int) -> None:
        """Déverrouille un compte"""
        if user_id in self.locked_accounts:
            del self.locked_accounts[user_id]

    def is_account_locked(self, user_id: int) -> bool:
        """Vérifie si un compte est verrouillé"""
        lock_time = self.locked_accounts.get(user_id, 0)
        if lock_time > time.time():
            return True
        elif lock_time != 0:
            del self.locked_accounts[user_id]
        return False

    def generate_token(self, length: int = 32) -> str:
        """Génère un token sécurisé pour les authentifications"""
        return secrets.token_urlsafe(length)

    def hash_password(self, password: str) -> str:
        """Hash un mot de passe avec sel (SHA-256)"""
        salt = secrets.token_hex(8)
        return f"{salt}${hashlib.sha256((salt + password).encode()).hexdigest()}"

    def verify_password(self, password: str, hashed: str) -> bool:
        """Vérifie un mot de passe contre son hash"""
        try:
            salt, stored_hash = hashed.split('$')
            computed_hash = hashlib.sha256((salt + password).encode()).hexdigest()
            return secrets.compare_digest(computed_hash, stored_hash)
        except:
            return False

    def check_admin(self, user_id: int) -> bool:
        """Vérifie si un utilisateur est administrateur"""
        return user_id in Config.ADMIN_IDS

    def sanitize_input(self, input_str: str) -> str:
        """Nettoie les entrées utilisateur pour prévenir les injections"""
        return re.sub(r"[;\\\"\']", "", input_str)[:255]

# Fonction utilitaire pour créer l'instance
def create_security_manager(db_manager=None):
    return SecurityManager(db_manager)