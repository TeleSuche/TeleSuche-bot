import logging
logger = logging.getLogger(__name__)
"""
Gestionnaire des fonctions de recherche et d'indexation
"""
import os
import hashlib
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class SearchHandler:
    """Gestionnaire des fonctions de recherche"""
    
    def __init__(self, db, translations):
        self.db = db
        self.translations = translations
        self.logger = logging.getLogger(__name__)
        self.supported_formats = ['.pdf', '.docx', '.txt', '.md', '.doc']
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /search - Recherche dans les documents indexés"""
        if not context.args:
            await update.message.reply_text(
                "🔍 **Recherche de documents**\n\n"
                "Usage: `/search <terme de recherche>`\n\n"
                "Exemples:\n"
                "• `/search contrat` - Cherche le mot 'contrat'\n"
                "• `/search \"phrase exacte\"` - Recherche de phrase\n"
                "• `/search tag:important` - Recherche par tag\n\n"
                "📊 Statistiques:\n"
                f"• Documents indexés: {self.db.get_indexed_documents_count()}\n"
                f"• Recherches ce mois: {self.db.get_monthly_search_count()}",
                parse_mode='Markdown'
            )
            return
        
        query = " ".join(context.args)
        user_id = update.effective_user.id
        
        # Vérifier les limites pour les utilisateurs non-premium
        if not self.db.is_premium_user(user_id):
            daily_searches = self.db.get_daily_search_count(user_id)
            if daily_searches >= 10:
                await update.message.reply_text(
                    "🔒 **Limite de recherche atteinte**\n\n"
                    "Utilisateurs gratuits: 10 recherches/jour\n"
                    "Vous avez utilisé toutes vos recherches aujourd'hui.\n\n"
                    "💡 Passez Premium pour des recherches illimitées!"
                )
                return
        
        # Effectuer la recherche
        results = await self.perform_search(query, user_id)
        
        if not results:
            await update.message.reply_text(
                f"🔍 **Aucun résultat trouvé**\n\n"
                f"Requête: `{query}`\n\n"
                "💡 Conseils:\n"
                "• Vérifiez l'orthographe\n"
                "• Essayez des termes plus généraux\n"
                "• Utilisez des synonymes\n"
                "• Indexez plus de documents avec /index",
                parse_mode='Markdown'
            )
            return
        
        # Afficher les résultats
        await self.display_search_results(update, query, results)
        
        # Enregistrer la recherche
        self.db.log_search(user_id, query, len(results))
    
    async def index_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /index - Gestion de l'indexation"""
        user_id = update.effective_user.id
        
        text = """📚 **Indexation de Documents**

🔍 **Formats supportés:**
• PDF (.pdf)
• Word (.docx, .doc)
• Texte (.txt, .md)

📊 **Vos statistiques:**
• Documents indexés: {indexed_count}
• Taille totale: {total_size} MB
• Dernière indexation: {last_indexed}

💡 **Comment indexer:**
1. Envoyez un document dans ce chat
2. Le bot l'analysera automatiquement
3. Le contenu sera indexable via /search""".format(
            indexed_count=self.db.get_user_indexed_count(user_id),
            total_size=round(self.db.get_user_storage_size(user_id) / (1024*1024), 2),
            last_indexed=self.db.get_last_indexed_date(user_id) or "Jamais"
        )
        
        keyboard = [
            [InlineKeyboardButton("📂 Mes documents", callback_data="search_my_docs")],
            [InlineKeyboardButton("🗑️ Supprimer documents", callback_data="search_delete_docs")],
            [InlineKeyboardButton("📊 Statistiques détaillées", callback_data="search_stats")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite les documents envoyés pour indexation"""
        document = update.message.document
        user_id = update.effective_user.id
        
        # Vérifications de base
        if not document:
            return
        
        if document.file_size > self.max_file_size:
            await update.message.reply_text(
                f"❌ **Fichier trop volumineux**\n\n"
                f"Taille: {round(document.file_size / (1024*1024), 2)} MB\n"
                f"Limite: {self.max_file_size // (1024*1024)} MB\n\n"
                f"💡 Compressez le fichier ou passez Premium pour une limite plus élevée."
            )
            return
        
        # Vérifier le format
        file_extension = os.path.splitext(document.file_name or "")[1].lower()
        if file_extension not in self.supported_formats:
            await update.message.reply_text(
                f"❌ **Format non supporté**\n\n"
                f"Fichier: {document.file_name}\n"
                f"Format: {file_extension}\n\n"
                f"📄 Formats supportés: {', '.join(self.supported_formats)}"
            )
            return
        
        # Vérifier les limites de stockage
        if not self.db.is_premium_user(user_id):
            user_storage = self.db.get_user_storage_size(user_id)
            storage_limit = 100 * 1024 * 1024  # 100MB pour utilisateurs gratuits
            
            if user_storage + document.file_size > storage_limit:
                await update.message.reply_text(
                    f"💾 **Limite de stockage atteinte**\n\n"
                    f"Utilisé: {round(user_storage / (1024*1024), 2)} MB\n"
                    f"Nouveau fichier: {round(document.file_size / (1024*1024), 2)} MB\n"
                    f"Limite gratuite: {storage_limit // (1024*1024)} MB\n\n"
                    f"🗑️ Supprimez des documents ou passez Premium!"
                )
                return
        
        # Télécharger et indexer le document
        try:
            processing_msg = await update.message.reply_text(
                "🔄 **Traitement en cours...**\n\n"
                f"📄 Fichier: {document.file_name}\n"
                f"📊 Taille: {round(document.file_size / 1024, 2)} KB\n\n"
                "⏳ Téléchargement et analyse..."
            )
            
            # Télécharger le fichier
            file = await context.bot.get_file(document.file_id)
            file_path = f"uploads/{user_id}_{document.file_id}_{document.file_name}"
            
            # Créer le dossier uploads s'il n'existe pas
            os.makedirs("uploads", exist_ok=True)
            
            await file.download_to_drive(file_path)
            
            # Extraire le texte selon le format
            extracted_text = await self.extract_text_from_file(file_path, file_extension)
            
            if not extracted_text:
                await processing_msg.edit_text(
                    "❌ **Erreur d'extraction**\n\n"
                    "Impossible d'extraire le texte de ce document.\n"
                    "Le fichier pourrait être corrompu ou protégé."
                )
                return
            
            # Indexer le document
            doc_id = await self.index_document(
                user_id=user_id,
                file_name=document.file_name,
                file_size=document.file_size,
                file_path=file_path,
                content=extracted_text,
                file_type=file_extension
            )
            
            # Analyser le contenu
            word_count = len(extracted_text.split())
            keywords = self.extract_keywords(extracted_text)
            
            await processing_msg.edit_text(
                f"✅ **Document indexé avec succès!**\n\n"
                f"📄 Nom: {document.file_name}\n"
                f"🔤 Mots extraits: {word_count:,}\n"
                f"🏷️ Mots-clés: {', '.join(keywords[:5])}\n"
                f"🆔 ID: `{doc_id}`\n\n"
                f"🔍 Utilisez `/search` pour rechercher dans ce document!",
                parse_mode='Markdown'
            )
            
            # Nettoyer le fichier temporaire
            try:
                os.remove(file_path)
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'indexation: {e}")
            await update.message.reply_text(
                "❌ **Erreur lors du traitement**\n\n"
                "Une erreur s'est produite lors de l'indexation.\n"
                "Veuillez réessayer ou contacter le support."
            )
    
    async def extract_text_from_file(self, file_path, file_extension):
        """Extrait le texte d'un fichier selon son format"""
        try:
            if file_extension in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif file_extension == '.pdf':
                # Simulation d'extraction PDF (nécessiterait PyPDF2 ou pdfplumber)
                return f"Contenu simulé du PDF: {os.path.basename(file_path)}\n" + \
                       "Ceci est un contenu d'exemple pour la démonstration.\n" + \
                       "Dans un environnement réel, le contenu serait extrait du PDF."
            
            elif file_extension in ['.docx', '.doc']:
                # Simulation d'extraction Word (nécessiterait python-docx)
                return f"Contenu simulé du document Word: {os.path.basename(file_path)}\n" + \
                       "Texte d'exemple extrait du document Word.\n" + \
                       "En production, le vrai contenu serait analysé."
            
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Erreur extraction texte: {e}")
            return None
    
    async def index_document(self, user_id, file_name, file_size, file_path, content, file_type):
        """Indexe un document dans la base de données"""
        # Générer un hash unique pour le document
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Vérifier si le document existe déjà
        existing_doc = self.db.get_document_by_hash(user_id, content_hash)
        if existing_doc:
            return existing_doc['id']
        
        # Créer l'entrée dans la base de données
        doc_data = {
            'user_id': user_id,
            'file_name': file_name,
            'file_size': file_size,
            'file_type': file_type,
            'content': content,
            'content_hash': content_hash,
            'keywords': ','.join(self.extract_keywords(content)),
            'indexed_at': datetime.now(),
            'word_count': len(content.split())
        }
        
        return self.db.create_indexed_document(doc_data)
    
    def extract_keywords(self, text):
        """Extrait les mots-clés d'un texte"""
        # Liste de mots vides en français et anglais
        stop_words = {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais',
            'donc', 'car', 'que', 'qui', 'quoi', 'dont', 'où', 'ce', 'cette',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been'
        }
        
        # Nettoyer et diviser le texte
        words = text.lower().split()
        cleaned_words = []
        
        for word in words:
            # Enlever la ponctuation
            word = ''.join(char for char in word if char.isalnum())
            
            # Filtrer les mots courts et les mots vides
            if len(word) > 3 and word not in stop_words:
                cleaned_words.append(word)
        
        # Compter les occurrences
        word_count = {}
        for word in cleaned_words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # Retourner les mots les plus fréquents
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:20]]
    
    async def perform_search(self, query, user_id):
        """Effectue une recherche dans les documents indexés"""
        # Analyser la requête
        search_terms = self.parse_search_query(query)
        
        # Rechercher dans la base de données
        results = self.db.search_documents(user_id, search_terms)
        
        # Trier les résultats par pertinence
        scored_results = []
        for result in results:
            score = self.calculate_relevance_score(result, search_terms)
            scored_results.append((score, result))
        
        # Trier par score décroissant
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return [result for score, result in scored_results[:20]]  # Top 20 résultats
    
    def parse_search_query(self, query):
        """Analyse une requête de recherche"""
        terms = {
            'words': [],
            'phrases': [],
            'tags': [],
            'exclude': []
        }
        
        # Recherche de phrases entre guillemets
        import re
        phrases = re.findall(r'"([^"]*)"', query)
        terms['phrases'] = phrases
        
        # Enlever les phrases de la requête
        query_without_phrases = re.sub(r'"[^"]*"', '', query)
        
        # Recherche de tags
        tags = re.findall(r'tag:(\w+)', query_without_phrases)
        terms['tags'] = tags
        
        # Enlever les tags de la requête
        query_without_tags = re.sub(r'tag:\w+', '', query_without_phrases)
        
        # Recherche de mots à exclure
        exclude_words = re.findall(r'-(\w+)', query_without_tags)
        terms['exclude'] = exclude_words
        
        # Enlever les mots exclus
        query_clean = re.sub(r'-\w+', '', query_without_tags)
        
        # Mots restants
        words = [word.strip() for word in query_clean.split() if word.strip()]
        terms['words'] = words
        
        return terms
    
    def calculate_relevance_score(self, document, search_terms):
        """Calcule un score de pertinence pour un document"""
        score = 0
        content = document.get('content', '').lower()
        title = document.get('file_name', '').lower()
        keywords = document.get('keywords', '').lower()
        
        # Score pour les mots dans le titre (poids plus élevé)
        for word in search_terms['words']:
            if word.lower() in title:
                score += 10
            if word.lower() in content:
                score += content.count(word.lower())
            if word.lower() in keywords:
                score += 5
        
        # Score pour les phrases exactes
        for phrase in search_terms['phrases']:
            if phrase.lower() in content:
                score += 20
            if phrase.lower() in title:
                score += 30
        
        # Score pour les tags
        for tag in search_terms['tags']:
            if tag.lower() in keywords:
                score += 15
        
        # Pénalité pour les mots exclus
        for exclude_word in search_terms['exclude']:
            if exclude_word.lower() in content:
                score -= 10
        
        return max(0, score)
    
    async def display_search_results(self, update, query, results):
        """Affiche les résultats de recherche"""
        text = f"🔍 **Résultats de recherche**\n\n"
        text += f"Requête: `{query}`\n"
        text += f"Résultats: {len(results)} document(s)\n\n"
        
        for i, result in enumerate(results[:10], 1):
            # Créer un extrait du contenu
            content = result.get('content', '')
            extract = self.create_excerpt(content, query)
            
            text += f"**{i}. {result['file_name']}**\n"
            text += f"   📄 Type: {result['file_type']}\n"
            text += f"   📅 Indexé: {result['indexed_at']}\n"
            text += f"   📝 Extrait: _{extract}_\n\n"
        
        if len(results) > 10:
            text += f"... et {len(results) - 10} autres résultats\n\n"
        
        text += "💡 Utilisez `/search \"phrase exacte\"` pour une recherche plus précise"
        
        keyboard = [
            [InlineKeyboardButton("📊 Filtrer résultats", callback_data=f"search_filter_{query}")],
            [InlineKeyboardButton("💾 Exporter résultats", callback_data=f"search_export_{query}")],
            [InlineKeyboardButton("🔍 Nouvelle recherche", callback_data="search_new")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Découper le message si trop long
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for i, part in enumerate(parts):
                if i == len(parts) - 1:  # Dernier message avec les boutons
                    await update.message.reply_text(part, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def create_excerpt(self, content, query, max_length=100):
        """Crée un extrait de texte autour des termes de recherche"""
        if not content:
            return "Aucun contenu disponible"
        
        # Trouver la première occurrence d'un terme de la requête
        query_words = query.lower().split()
        content_lower = content.lower()
        
        best_position = 0
        for word in query_words:
            pos = content_lower.find(word)
            if pos != -1:
                best_position = pos
                break
        
        # Extraire autour de cette position
        start = max(0, best_position - max_length // 2)
        end = min(len(content), start + max_length)
        excerpt = content[start:end]
        
        # Ajouter "..." si tronqué
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt = excerpt + "..."
        
        return excerpt.strip()
    
    async def handle_callback(self, update, context):
        """Gestionnaire des callbacks de recherche"""
        query = update.callback_query
        data = query.data
        
        await query.answer()
        
        if data == "search_my_docs":
            await self.show_user_documents(query)
        elif data == "search_delete_docs":
            await self.show_delete_options(query)
        elif data == "search_stats":
            await self.show_search_statistics(query)
        elif data.startswith("search_filter_"):
            query_text = data.replace("search_filter_", "")
            await self.show_filter_options(query, query_text)
        elif data.startswith("search_export_"):
            query_text = data.replace("search_export_", "")
            await self.export_search_results(query, query_text)
        elif data == "search_new":
            await self.prompt_new_search(query)
    
    async def show_user_documents(self, query):
        """Affiche les documents de l'utilisateur"""
        user_id = query.from_user.id
        documents = self.db.get_user_documents(user_id, limit=20)
        
        if not documents:
            text = "📂 **Vos Documents**\n\nAucun document indexé."
        else:
            text = f"📂 **Vos Documents** ({len(documents)})\n\n"
            
            for i, doc in enumerate(documents[:15], 1):
                size_mb = round(doc['file_size'] / (1024*1024), 2)
                text += f"**{i}. {doc['file_name']}**\n"
                text += f"   📊 {size_mb} MB | {doc['word_count']} mots\n"
                text += f"   📅 {doc['indexed_at']}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Supprimer documents", callback_data="search_delete_docs")],
            [InlineKeyboardButton("🔙 Retour", callback_data="search_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_search_statistics(self, query):
        """Affiche les statistiques de recherche"""
        user_id = query.from_user.id
        stats = self.db.get_user_search_stats(user_id)
        
        text = f"""📊 **Statistiques de Recherche**

📈 **Utilisation:**
• Recherches totales: {stats['total_searches']}
• Recherches ce mois: {stats['monthly_searches']}
• Moyenne/jour: {stats['daily_average']}

📚 **Documents:**
• Total indexés: {stats['total_documents']}
• Taille totale: {round(stats['total_size'] / (1024*1024), 2)} MB
• Mots indexés: {stats['total_words']:,}

🔍 **Recherches populaires:**
{self.format_popular_searches(stats['popular_searches'])}

⭐ **Efficacité:**
• Taux de succès: {stats['success_rate']}%
• Temps moyen: {stats['avg_response_time']}ms"""
        
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="search_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def format_popular_searches(self, searches):
        """Formate les recherches populaires"""
        if not searches:
            return "Aucune recherche récente"
        
        result = ""
        for i, search in enumerate(searches[:5], 1):
            result += f"{i}. `{search['query']}` ({search['count']} fois)\n"
        
        return result
