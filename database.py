import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Solution pour éviter les imports circulaires
DB_PATH = os.environ.get("DB_PATH", "/storage/emulated/0/telegram_bot/database")

class TeleSucheDB:
    """Implémentation robuste de la base de données JSON"""
    
    def __init__(self, path=None):
        self.path = self.resolve_path(path or DB_PATH)
        self.cache = {}
        logger.info(f"Base de données initialisée à: {self.path}")

    def resolve_path(self, path):
        """Résolution robuste du chemin de stockage"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

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
        for file in self.path.glob(f"{collection}_*.json"):
            try:
                key = file.stem.split('_', 1)[1]
                data = self.load(collection, key)
                if data:
                    results[key] = data
            except Exception as e:
                logger.error(f"Erreur traitement {file}: {e}")
        return results

class DatabaseManager:
    """Interface compatible avec l'ancien code"""

    def __init__(self):
        self.db = TeleSucheDB()

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.db.load('users', str(user_id))

    def save_user(self, user_data: Dict[str, Any]) -> None:
        user_id = str(user_data.get('id'))
        if user_id:
            self.db.save('users', user_id, user_data)
    
    def get_temp_data(self, user_id: int, key: str) -> Any:
        """Récupère une donnée temporaire"""
        user_data = self.get_user(user_id)
        if user_data and 'temp_data' in user_data:
            return user_data['temp_data'].get(key)
        return None

    def set_temp_data(self, user_id: int, key: str, value: Any) -> None:
        """Définit une donnée temporaire"""
        user_data = self.get_user(user_id) or {}
        if 'temp_data' not in user_data:
            user_data['temp_data'] = {}
        user_data['temp_data'][key] = value
        self.save_user(user_data)

    def clear_temp_data(self, user_id: int) -> None:
        """Efface toutes les données temporaires"""
        user_data = self.get_user(user_id) or {}
        if 'temp_data' in user_data:
            del user_data['temp_data']
            self.save_user(user_data)

    def get_user_state(self, user_id: int) -> Optional[str]:
        """Récupère l'état utilisateur"""
        user_data = self.get_user(user_id)
        return user_data.get('state') if user_data else None

    def set_user_state(self, user_id: int, state: str) -> None:
        """Définit l'état utilisateur"""
        user_data = self.get_user(user_id) or {}
        user_data['state'] = state
        self.save_user(user_data)

    def get_user_pin(self, user_id: int) -> Optional[str]:
        """Récupère le PIN utilisateur"""
        user_data = self.get_user(user_id)
        return user_data.get('pin') if user_data else None

    def set_user_pin(self, user_id: int, pin: str) -> None:
        """Définit le PIN utilisateur"""
        user_data = self.get_user(user_id) or {}
        user_data['pin'] = pin
        self.save_user(user_data)

# Initialisation différée pour éviter les erreurs au chargement
_disk_db_instance = None

def get_disk_db() -> TeleSucheDB:
    """Obtient l'instance de base de données sur disque"""
    global _disk_db_instance
    if _disk_db_instance is None:
        _disk_db_instance = TeleSucheDB()
    return _disk_db_instance