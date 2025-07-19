# memory_full.py
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from .database import get_disk_db

logger = logging.getLogger(__name__)

class UserStates(Enum):
    INITIAL = 0
    ASKING_PIN = 1
    AUTHENTICATED = 2
    ASKING_EMAIL = 3
    WAITING_FOR_EMAIL_CODE = 4
    CREATING_PIN = 5
    IN_SETUP = 6
    AWAITING_SEARCH = 7
    RECOVERING_ACCOUNT = 8
    VERIFYING_RECOVERY = 9
    LOCKED_OUT = 10

class DB:
    def __init__(self):
        self.disk_db = get_disk_db()
        
        # Stockage en mémoire
        self.users: Dict[int, Dict] = {}
        self.groups: Dict[int, Dict] = {}
        self.files: Dict[str, Dict] = {}
        self.temp_data: Dict[int, Dict] = {}
        self.search_history: Dict[int, List] = {}
        self.download_history: Dict[int, List] = {}
        self.referral_codes: Dict[str, int] = {}
        self.referrals: Dict[int, List[int]] = {}
        self.wallets: Dict[int, float] = {}
        self.transactions: Dict[int, List] = {}
        self.subscriptions: Dict[int, Dict] = {}
        self.monetization_settings: Dict[int, Dict] = {}
        self.temp_states: Dict[int, Dict] = {}
        self.pdg_config: Dict = {}
        self.user_bots: Dict[int, List[Dict]] = {}
        self.user_plans: Dict[int, str] = {}
        self.pending_deletions: Dict[tuple, Dict] = {}

        self.load_pdg_config()

    def save_to_disk(self, collection, key, data):
        return self.disk_db.save(collection, key, data)

    def load_from_disk(self, collection, key):
        return self.disk_db.load(collection, key)
    
    def get_all_from_disk(self, collection):
        return self.disk_db.get_all(collection)

    def load_pdg_config(self):
        data = self.load_from_disk("config", "pdg_config")
        if isinstance(data, dict):
            self.pdg_config = data
        else:
            self.pdg_config = {}

    def save_pdg_config(self):
        self.save_to_disk("config", "pdg_config", self.pdg_config)

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        return default

    # Méthodes pour la gestion des bots utilisateur
    def save_user_bot(self, user_id: int, token: str, bot_username: str, bot_name: str, creation_time: str):
        if user_id not in self.user_bots:
            self.user_bots[user_id] = []
        
        for bot in self.user_bots[user_id]:
            if bot["bot_username"] == bot_username:
                bot["token"] = token
                bot["bot_name"] = bot_name
                bot["updated_at"] = datetime.now().isoformat()
                break
        else:
            self.user_bots[user_id].append({
                "token": token,
                "bot_username": bot_username,
                "bot_name": bot_name,
                "created_at": creation_time,
                "creation_time": creation_time
            })
        
        self.save_to_disk("user_bots", str(user_id), self.user_bots[user_id])

    def get_user_bots(self, user_id: int) -> List[Dict]:
        if user_id in self.user_bots:
            return self.user_bots[user_id]
        
        user_bots = self.load_from_disk("user_bots", str(user_id))
        if user_bots is None:
            return []
        
        self.user_bots[user_id] = user_bots
        return user_bots

    def delete_user_bot(self, user_id: int, bot_username: str):
        if user_id not in self.user_bots:
            return False
        
        new_list = [bot for bot in self.user_bots[user_id] if bot["bot_username"] != bot_username]
        if len(new_list) == len(self.user_bots[user_id]):
            return False
        
        self.user_bots[user_id] = new_list
        self.save_to_disk("user_bots", str(user_id), new_list)
        return True

    def mark_bot_for_deletion(self, user_id: int, bot_username: str):
        if user_id not in self.user_bots:
            return False
            
        for bot in self.user_bots[user_id]:
            if bot["bot_username"] == bot_username:
                bot["deletion_time"] = datetime.now().timestamp()
                bot["deletion_scheduled"] = True
                self.save_to_disk("user_bots", str(user_id), self.user_bots[user_id])
                return True
        return False

    def cancel_bot_deletion(self, user_id: int, bot_username: str):
        if user_id not in self.user_bots:
            return False
            
        for bot in self.user_bots[user_id]:
            if bot["bot_username"] == bot_username:
                if "deletion_scheduled" in bot:
                    del bot["deletion_scheduled"]
                if "deletion_time" in bot:
                    del bot["deletion_time"]
                self.save_to_disk("user_bots", str(user_id), self.user_bots[user_id])
                return True
        return False

    def set_user_plan(self, user_id: int, plan: str):
        self.user_plans[user_id] = plan
        self.save_to_disk("user_plans", str(user_id), plan)

    def get_user_plan(self, user_id: int) -> str:
        if user_id in self.user_plans:
            return self.user_plans[user_id]
        
        plan = self.load_from_disk("user_plans", str(user_id))
        if plan is None:
            return "sub_basic"
        
        self.user_plans[user_id] = plan
        return plan

    # Méthodes pour l'authentification et la gestion des utilisateurs
    def get_user_state(self, user_id: int) -> Optional[UserStates]:
        user = self.users.get(user_id)
        return UserStates(user["state"]) if user and "state" in user else None

    def set_user_state(self, user_id: int, state: UserStates):
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]["state"] = state.value
        self.save_to_disk("users", str(user_id), self.users[user_id])

    def is_new_user(self, user_id: int) -> bool:
        if user_id in self.users:
            return False
        user_data = self.load_from_disk("users", str(user_id))
        return user_data is None

    def get_user_language(self, user_id: int) -> str:
        # 1. Vérifier le cache mémoire
        if user_id in self.users and "language" in self.users[user_id]:
            return self.users[user_id]["language"]
        
        # 2. Charger depuis le disque si absent du cache
        user_data = self.load_from_disk("users", str(user_id))
        
        # 3. Mettre à jour le cache avec TOUTES les données
        if user_data:
            if user_id not in self.users:
                self.users[user_id] = {}
            self.users[user_id].update(user_data)  # Mise à jour complète
            return user_data.get("language", "fr")
        
        # 4. Retourner la valeur par défaut
        return "fr"

    def set_user_language(self, user_id: int, lang_code: str):
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]["language"] = lang_code
        self.save_to_disk("users", str(user_id), self.users[user_id])

    def save_terms_acceptance(self, user_id: int):
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]["terms_accepted"] = True
        self.users[user_id]["terms_accepted_at"] = datetime.now().isoformat()
        self.save_to_disk("users", str(user_id), self.users[user_id])

    def has_accepted_terms(self, user_id: int) -> bool:
        if user_id in self.users and self.users[user_id].get("terms_accepted"):
            return True
        user_data = self.load_from_disk("users", str(user_id))
        if user_data and user_data.get("terms_accepted"):
            self.users[user_id] = user_data
            return True
        return False

    def get_user_trial_end_date(self, user_id: int) -> Optional[datetime]:
        """Récupère la date de fin de la période d'essai de l'utilisateur."""
        user_data = self.users.get(user_id)
        if not user_data:
            user_data = self.load_from_disk("users", str(user_id))
            if not user_data:
                return None
            self.users[user_id] = user_data # Cache the loaded data

        trial_end_date_str = user_data.get("trial_end_date")
        if trial_end_date_str:
            try:
                return datetime.fromisoformat(trial_end_date_str)
            except ValueError:
                logger.error(f"Invalid trial_end_date format for user {user_id}: {trial_end_date_str}")
                return None
        return None

    # Méthodes spécifiques à l'authentification
    def get_user_pin(self, user_id: int) -> Optional[str]:
        user = self.users.get(user_id)
        return user.get("pin") if user else None

    def set_user_pin(self, user_id: int, pin_hash: str):
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]["pin"] = pin_hash
        self.save_to_disk("users", str(user_id), self.users[user_id])

    def increment_failed_attempts(self, user_id: int) -> int:
        if user_id not in self.users:
            self.users[user_id] = {"failed_attempts": 0}
        
        attempts = self.users[user_id].get("failed_attempts", 0) + 1
        self.users[user_id]["failed_attempts"] = attempts
        self.save_to_disk("users", str(user_id), self.users[user_id])
        return attempts

    def reset_failed_attempts(self, user_id: int):
        if user_id in self.users and "failed_attempts" in self.users[user_id]:
            self.users[user_id]["failed_attempts"] = 0
            self.save_to_disk("users", str(user_id), self.users[user_id])

    def set_temp_data(self, user_id: int, key: str, value: Any):
        if user_id not in self.temp_data:
            self.temp_data[user_id] = {}
        self.temp_data[user_id][key] = value

    def get_temp_data(self, user_id: int, key: str) -> Any:
        return self.temp_data.get(user_id, {}).get(key) if user_id in self.temp_data else None

    def clear_temp_data(self, user_id: int):
        if user_id in self.temp_data:
            del self.temp_data[user_id]

    def set_temp_message_id(self, user_id: int, message_id: int):
        self.set_temp_data(user_id, "message_id", message_id)

    def get_temp_message_id(self, user_id: int) -> Optional[int]:
        return self.get_temp_data(user_id, "message_id")

    # Méthodes de sauvegarde et de gestion globale
    def full_backup(self):
        for user_id, data in self.users.items():
            self.save_to_disk("users", str(user_id), data)
        
        for group_id, data in self.groups.items():
            self.save_to_disk("groups", str(group_id), data)
        
        self.save_to_disk("user_bots", "all", self.user_bots)
        self.save_to_disk("user_plans", "all", self.user_plans)

    def is_token_used(self, token: str, current_user_id: int) -> bool:
        """Vérifie si un token est déjà utilisé par un bot d'un utilisateur, y compris l'utilisateur actuel."""
        # Charger tous les bots de tous les utilisateurs
        all_user_bots_data = self.get_all_from_disk("user_bots")
        
        for user_id_str, bots_list in all_user_bots_data.items():
            user_id = int(user_id_str)
            for bot in bots_list:
                if bot.get("token") == token:
                    # Si le token est trouvé, vérifier si c'est le bot de l'utilisateur actuel
                    # Si c'est le bot de l'utilisateur actuel, ce n'est pas une 
                    # réutilisation mais une mise à jour.
                    # Si c'est un autre utilisateur, alors le token est déjà utilisé.
                    if user_id != current_user_id:
                        return True
        return False

# Initialisation de la base de données
db = DB()