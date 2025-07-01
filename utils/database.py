import logging
logger = logging.getLogger(__name__)
# database.py - Gestionnaire de base de données JSON corrigé

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from config import Config
import logging

logger = logging.getLogger(__name__)

class TeleSucheDB:
    """Implémentation robuste de la base de données JSON"""
    def __init__(self, path=None):
        # Chemin par défaut dans le stockage interne de Termux
        default_path = "/data/data/com.termux/files/home/teleSuche_data"
        self.path = self.resolve_path(path or default_path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        logger.info(f"Base de données initialisée à: {self.path}")
    
    def resolve_path(self, path):
        """Résolution robuste du chemin de stockage"""
        try:
            path = Path(path)
            # Vérification des permissions sur le répertoire parent
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            
            # Test d'écriture simplifié
            test_file = path / ".permission_test"
            try:
                test_file.touch()
                test_file.unlink()
                return path
            except (PermissionError, OSError):
                # Basculer vers un chemin garanti accessible
                fallback = Path.home() / "teleSuche_data"
                fallback.mkdir(parents=True, exist_ok=True)
                logger.warning(f"Utilisation du chemin alternatif: {fallback}")
                return fallback
        except Exception as e:
            logger.error(f"Erreur de résolution du chemin: {e}")
            # Dernier recours: répertoire courant
            fallback = Path.cwd() / "teleSuche_data"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
    
    def _get_file_path(self, collection, key):
        """Génère un chemin de fichier sécurisé"""
        safe_key = "".join(c for c in str(key) if c.isalnum() or c in ('_', '-'))
        return self.path / f"{collection}_{safe_key}.json"
    
    def save(self, collection, key, data):
        """Sauvegarde des données avec gestion d'erreur améliorée"""
        file_path = self._get_file_path(collection, key)
        try:
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, default=str)
            temp_path.replace(file_path)  # Remplacement atomique
            self.cache[(collection, key)] = data
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde {file_path}: {e}")
            return False
    
    def load(self, collection, key):
        """Chargement avec cache"""
        cache_key = (collection, key)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        file_path = self._get_file_path(collection, key)
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.cache[cache_key] = data
                return data
        except Exception as e:
            logger.error(f"Erreur chargement {file_path}: {e}")
            return None
    
    def delete(self, collection, key):
        """Suppression sécurisée"""
        file_path = self._get_file_path(collection, key)
        try:
            if file_path.exists():
                file_path.unlink()
            self.cache.pop((collection, key), None)
            return True
        except Exception as e:
            logger.error(f"Erreur suppression {file_path}: {e}")
            return False
    
    def get_all(self, collection):
        """Récupération de tous les éléments d'une collection"""
        results = {}
        try:
            for file in self.path.glob(f"{collection}_*.json"):
                try:
                    key = file.stem.split('_', 1)[1]
                    data = self.load(collection, key)
                    if data:
                        results[key] = data
                except Exception as e:
                    logger.error(f"Erreur traitement {file}: {e}")
        except Exception as e:
            logger.error(f"Erreur glob {collection}: {e}")
        return results

class DatabaseManager:
    """Interface compatible avec le reste de l'application"""
    
    def __init__(self):
        # Utilisation du chemin configuré ou d'un chemin par défaut garanti accessible
        self.db = TeleSucheDB(getattr(Config, 'DB_PATH', None))
    
    # Méthodes requises
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.db.load('users', str(user_id))
    
    def save_user(self, user_data: Dict[str, Any]) -> None:
        user_id = str(user_data.get('id', user_data.get('_id')))
        if user_id:
            self.db.save('users', user_id, user_data)
    
    def get_user_bots(self, user_id: int) -> List[Dict[str, Any]]:
        all_bots = self.db.get_all('bots')
        return [b for b in all_bots.values() if str(b.get('owner_id')) == str(user_id)]
    
    def get_bot_stats(self, bot_id: str) -> Dict[str, Any]:
        return self.db.load('stats', bot_id) or {}
    
    # Méthodes supplémentaires
    def get_user_history(self, user_id: int) -> List[Dict[str, Any]]:
        return self.db.load('history', str(user_id)) or []
    
    def get_user_credits(self, user_id: int) -> int:
        user = self.get_user(user_id)
        return user.get('credits', 0) if user else 0
    
    def set_user_pin(self, user_id: int, pin: str) -> None:
        user = self.get_user(user_id) or {'id': str(user_id)}
        user['pin'] = pin
        self.save_user(user)
    
    def get_user_pin(self, user_id: int) -> Optional[str]:
        user = self.get_user(user_id)
        return user.get('pin') if user else None
    
    def set_user_state(self, user_id: int, state: str) -> None:
        user = self.get_user(user_id) or {'id': str(user_id)}
        user['state'] = state
        self.save_user(user)
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        user = self.get_user(user_id)
        return user.get('state') if user else None

# Initialisation différée pour éviter les erreurs au chargement
_db_instance = None

def get_db() -> DatabaseManager:
    """Obtient l'instance de base de données (initialisation différée)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance

# Alias pour compatibilité
db = get_db()
DatabaseManager = DatabaseManager