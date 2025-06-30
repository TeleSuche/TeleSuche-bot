from datetime import datetime
import logging
from datetime import datetime, timedelta
from enum import Enum
import random
import string
from typing import Dict, List, Optional, Any, Tuple

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

class DB:
    def __init__(self):
        # Stockage des données utilisateur
        self.users: Dict[int, Dict] = {}
        
        # Stockage des groupes
        self.groups: Dict[int, Dict] = {}
        
        # Fichiers indexés
        self.files: Dict[str, Dict] = {}
        
        # Données temporaires
        self.temp_data: Dict[int, Any] = {}
        
        # Historique des recherches
        self.search_history: Dict[int, List] = {}
        
        # Historique des téléchargements
        self.download_history: Dict[int, List] = {}
        
        # Références et parrainage
        self.referral_codes: Dict[str, int] = {}
        self.referrals: Dict[int, List[int]] = {}
        
        # Portefeuilles
        self.wallets: Dict[int, float] = {}
        self.transactions: Dict[int, List] = {}
        
        # Abonnements
        self.subscriptions: Dict[int, Dict] = {}
        
        # Paramètres de monétisation
        self.monetization_settings: Dict[int, Dict] = {}
        
        # États temporaires
        self.temp_states: Dict[int, Dict] = {}
        
        # Configuration PDG
        self.pdg_config: Dict = {}

    # Méthodes pour les utilisateurs
    def get_user_state(self, user_id: int) -> Optional[UserStates]:
        user = self.users.get(user_id)
        return UserStates(user['state']) if user and 'state' in user else None

    def set_user_state(self, user_id: int, state: UserStates):
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]['state'] = state.value

    def get_user_pin(self, user_id: int) -> Optional[str]:
        return self.users.get(user_id, {}).get('pin')

    def set_user_pin(self, user_id: int, pin: str):
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]['pin'] = pin

    def get_user_email(self, user_id: int) -> Optional[str]:
        return self.users.get(user_id, {}).get('email')

    def set_user_email(self, user_id: int, email: str):
        if user_id not in self.users:
            self.users[user_id] = {}
        self.users[user_id]['email'] = email

    def get_user_credits(self, user_id: int) -> int:
        return self.users.get(user_id, {}).get('credits', 0)

    def add_credits(self, user_id: int, amount: int):
        if user_id not in self.users:
            self.users[user_id] = {'credits': 0}
        self.users[user_id]['credits'] = self.users[user_id].get('credits', 0) + amount

    def deduct_credit(self, user_id: int):
        if user_id in self.users and self.users[user_id].get('credits', 0) > 0:
            self.users[user_id]['credits'] -= 1

    def has_credits(self, user_id: int) -> bool:
        return self.get_user_credits(user_id) > 0

    # Méthodes pour les groupes
    def is_search_group(self, group_id: int) -> bool:
        return self.groups.get(group_id, {}).get('is_search_group', False)

    def set_search_group(self, user_id: int, group_id: int):
        if group_id not in self.groups:
            self.groups[group_id] = {'admin_id': user_id}
        self.groups[group_id]['is_search_group'] = True

    def is_group_admin(self, user_id: int, group_id: int) -> bool:
        return self.groups.get(group_id, {}).get('admin_id') == user_id

    def get_group_admin(self, group_id: int) -> Optional[int]:
        return self.groups.get(group_id, {}).get('admin_id')

    # Méthodes pour l'indexation et la recherche de fichiers
    def index_file(self, file_data: Dict):
        file_id = file_data['file_id']
        self.files[file_id] = file_data

    def get_temp_file_data(self, message_id: int) -> Optional[Dict]:
        return self.temp_data.get(message_id)

    def set_temp_file_data(self, message_id: int, file_data: Dict):
        self.temp_data[message_id] = file_data

    def search_files(self, query: str) -> List[Dict]:
        results = []
        for file_id, file_data in self.files.items():
            if query.lower() in file_data.get('title', '').lower() or query.lower() in file_data.get('description', '').lower():
                results.append(file_data)
        return results

    def get_file_by_id(self, file_id: str) -> Optional[Dict]:
        return self.files.get(file_id)

    # Méthodes pour le parrainage
    def generate_referral_code(self, user_id: int, length=8) -> str:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        self.referral_codes[code] = user_id
        return code

    def get_user_by_ref_code(self, code: str) -> Optional[int]:
        return self.referral_codes.get(code)

    def add_referred_user(self, referrer_id: int, referred_id: int):
        if referrer_id not in self.referrals:
            self.referrals[referrer_id] = []
        self.referrals[referrer_id].append(referred_id)

    def get_referrer(self, user_id: int) -> Optional[int]:
        for referrer_id, referred_list in self.referrals.items():
            if user_id in referred_list:
                return referrer_id
        return None

    def get_referred_users_count(self, group_id: int) -> int:
        admin_id = self.get_group_admin(group_id)
        if admin_id not in self.referrals:
            return 0
        return len(self.referrals[admin_id])

    # Méthodes pour le wallet
    def get_wallet_balance(self, user_id: int) -> float:
        return self.wallets.get(user_id, 0.0)

    def add_wallet_balance(self, user_id: int, amount: float):
        self.wallets[user_id] = self.wallets.get(user_id, 0.0) + amount

    def add_wallet_transaction(self, user_id: int, amount: float, description: str):
        if user_id not in self.transactions:
            self.transactions[user_id] = []
        self.transactions[user_id].append({
            'date': datetime.now(),
            'description': description,
            'amount': amount
        })

    def get_recent_transactions(self, user_id: int, limit=5) -> List[Dict]:
        return self.transactions.get(user_id, [])[:limit]

    # Méthodes pour les abonnements
    def activate_subscription(self, user_id: int, plan: str, months: int):
        expiry_date = datetime.now() + timedelta(days=30 * months)
        self.subscriptions[user_id] = {
            'plan': plan,
            'expiry': expiry_date
        }

    def get_subscription(self, user_id: int) -> Optional[Dict]:
        return self.subscriptions.get(user_id)

    def is_subscription_active(self, user_id: int) -> bool:
        sub = self.get_subscription(user_id)
        if not sub:
            return False
        return sub['expiry'] > datetime.now()

    # Méthodes pour la monétisation
    def set_monetization_setting(self, group_id: int, key: str, value: Any):
        if group_id not in self.monetization_settings:
            self.monetization_settings[group_id] = {}
        self.monetization_settings[group_id][key] = value

    def get_monetization_setting(self, group_id: int, key: str, default=None) -> Any:
        return self.monetization_settings.get(group_id, {}).get(key, default)

    # Méthodes pour l'historique
    def save_search_history(self, user_id: int, chat_id: int, query: str, search_type: str):
        if user_id not in self.search_history:
            self.search_history[user_id] = []
        self.search_history[user_id].append({
            'date': datetime.now(),
            'query': query,
            'type': search_type,
            'chat_id': chat_id
        })

    def save_download_history(self, user_id: int, chat_id: int, file_title: str, file_id: str):
        if user_id not in self.download_history:
            self.download_history[user_id] = []
        self.download_history[user_id].append({
            'date': datetime.now(),
            'file_title': file_title,
            'file_id': file_id,
            'chat_id': chat_id
        })

    def get_user_history(self, user_id: int) -> List[Dict]:
        return self.search_history.get(user_id, []) + self.download_history.get(user_id, [])

    # États temporaires
    def set_temp_state(self, user_id: int, state: str, message_id: int = None):
        if user_id not in self.temp_states:
            self.temp_states[user_id] = {}
        self.temp_states[user_id]['state'] = state
        if message_id:
            self.temp_states[user_id]['message_id'] = message_id

    def get_temp_state(self, user_id: int) -> Optional[str]:
        return self.temp_states.get(user_id, {}).get('state')

    def get_temp_message_id(self, user_id: int) -> Optional[int]:
        return self.temp_states.get(user_id, {}).get('message_id')

    def set_temp_message_id(self, user_id: int, message_id: int):
        if user_id not in self.temp_states:
            self.temp_states[user_id] = {}
        self.temp_states[user_id]['message_id'] = message_id

    # Méthodes PDG
    def get_pdg_config(self) -> Dict:
        """Retourne la configuration du bot PDG"""
        return self.get("pdg_bot", {})
    
    def is_pdg_user(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur est le propriétaire du PDG"""
        pdg = self.get_pdg_config()
        return pdg and pdg.get("owner") == user_id
    
    def get_all_children_bots(self) -> List[Dict]:
        """Retourne tous les bots enfants (non-PDG)"""
        return [b for b in self.get("user_bots", []) 
                if b.get("bot_id") != self.get_pdg_config().get("bot_id")]
    
    def get_system_overview(self) -> Dict:
        """Retourne les statistiques système pour le dashboard PDG"""
        return {
            "bots_total": len(self.get_all_children_bots()),
            "bots_active": sum(1 for b in self.get_all_children_bots() if b.get("is_active", False)),
            "bots_inactive": 0,  # À implémenter
            "admins_total": len(self.users),
            "groups_total": len(self.groups),
            "subscriptions_total": len(self.subscriptions)
        }

# Instance globale de la base de données
db = DB()