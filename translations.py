import logging
import json
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TranslationManager:
    """
    Gestionnaire avancé de traductions avec support multilingue via fichiers JSON.
    """

    def __init__(self, locale_dir: str = "i18n"):
        self.locale_dir = Path(locale_dir)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = "fr"
        self.load_all_translations()

    def load_all_translations(self):
        """Charge toutes les traductions depuis les fichiers JSON."""
        if not self.locale_dir.exists():
            logger.warning(f"Dossier de langues inexistant : {self.locale_dir}")
            return

        for file in self.locale_dir.glob("*.json"):
            lang = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.translations[lang] = json.load(f)
                    logger.info(f"✔️ Langue chargée : {lang} ({file.name})")
            except Exception as e:
                logger.error(f"❌ Erreur lors du chargement de {file.name} : {e}")

    def get(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        """
        Récupère une traduction selon la langue.
        Si non trouvée, retourne la valeur de la langue par défaut ou la clé brute.

        Args:
            key: Clé de traduction
            lang: Code langue (ex: 'en', 'fr')
            kwargs: Paramètres de formatage optionnels

        Returns:
            Traduction formatée
        """
        lang = lang or self.default_language

        # Essayons la langue demandée
        translation = self.translations.get(lang, {}).get(key)

        # Sinon fallback vers la langue par défaut
        if translation is None:
            translation = self.translations.get(self.default_language, {}).get(key, key)

        try:
            return translation.format(**kwargs) if kwargs else translation
        except Exception as e:
            logger.error(f"Erreur de formatage pour '{key}' ({lang}) : {e}")
            return translation

    def get_available_languages(self) -> list:
        """Retourne la liste des langues disponibles (codes)."""
        return list(self.translations.keys())


# Instanciation globale
translator = TranslationManager()

# Fonctions d'interface
def t(key: str, lang: str = None, **kwargs) -> str:
    """Alias court pour `translator.get()`"""
    return translator.get(key, lang, **kwargs)

def get_text(key: str, lang: str = None, **kwargs) -> str:
    """Alias complet pour compatibilité"""
    return translator.get(key, lang, **kwargs)