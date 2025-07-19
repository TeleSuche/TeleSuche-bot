import logging
logger = logging.getLogger(__name__)
from telegram.ext import Application
from typing import List, Callable
from dataclasses import dataclass

@dataclass
class InterfaceModule:
    setup_fn: Callable
    dependencies: List[str] = None

class AdminMenu:
    """Gestion centralisée des interfaces administrateur avec injection de dépendances"""
    
    MODULES = {
        'subscriptions': InterfaceModule(
            setup_fn=lambda app: app.add_handler(CallbackQueryHandler(...)),
            dependencies=['auth']
        ),
        'commands': InterfaceModule(
            setup_fn=lambda app: app.add_handler(CommandHandler(...))
        ),
        'payment_links': InterfaceModule(
            setup_fn=lambda app: app.add_handler(MessageHandler(...)),
            dependencies=['payment']
        ),
        'admin_panel': InterfaceModule(
            setup_fn=lambda app: app.add_handler(CommandHandler(...)),
            dependencies=['auth', 'permissions']
        ),
        'credits': InterfaceModule(
            setup_fn=lambda app: app.add_handler(CallbackQueryHandler(...)),
            dependencies=['payment']
        )
    }

    @classmethod
    def register_all(cls, application: Application) -> None:
        """Enregistre tous les modules avec gestion des dépendances"""
        registered = set()
        
        def register_module(name: str):
            if name in registered:
                return
            
            module = cls.MODULES[name]
            
            # Enregistre les dépendances d'abord
            if module.dependencies:
                for dep in module.dependencies:
                    register_module(dep)
            
            # Enregistre le module
            module.setup_fn(application)
            registered.add(name)
            logger.info(f"Module admin '{name}' chargé")

        for module_name in cls.MODULES:
            register_module(module_name)

# Alternative simplifiée (version basique)
def setup_admin_interfaces(application: Application):
    """Configure toutes les interfaces admin (version simplifiée)"""
    from .subscriptions import setup_subscription_handlers
    from .commands_menu import setup_commands_handlers as setup_commands
    from .create_link import setup_payment_links
    from .admin_panel import setup_admin_handlers as setup_admin_panel
    from .add_credits import setup_credit_handlers as setup_credits

    setup_subscription_handlers(application)
    setup_commands(application)
    setup_payment_links(application)
    setup_admin_panel(application)
    setup_credits(application)