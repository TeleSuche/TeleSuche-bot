import logging
logger = logging.getLogger(__name__)
"""
Gestionnaire de la boutique et des achats
"""
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class ShopHandler:
    """Gestionnaire de la boutique"""
    
    def __init__(self, db, translations):
        self.db = db
        self.translations = translations
        self.logger = logging.getLogger(__name__)
        
        # Import du gestionnaire de paiements
        try:
            from utils.payments import PaymentManager, PaymentMethod
            self.payment_manager = PaymentManager(self.db, self.load_payment_config())
            self.PaymentMethod = PaymentMethod
        except ImportError:
            self.logger.warning("PaymentManager non disponible")
            self.payment_manager = None
            self.PaymentMethod = None
    
    @staticmethod
    def load_payment_config():
        """Charge la configuration des paiements"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('payments', {
                'simulation_mode': True,
                'stripe_enabled': False,
                'crypto_enabled': False,
                'telegram_payments_enabled': True
            })
        except:
            return {'simulation_mode': True}
    
    async def shop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /shop - Affiche la boutique"""
        user_id = update.effective_user.id
        
        # Récupérer les crédits de l'utilisateur
        user_credits = self.db.get_user_credits(user_id)
        
        # Charger les produits depuis la configuration
        products = self.load_products()
        
        text = f"""🏪 **Boutique TeleSuche**

💰 Vos crédits: **{user_credits}** crédits

🛍️ **Produits disponibles:**

"""
        
        keyboard = []
        for product in products:
            text += f"• **{product['name']}** - {product['price']} crédits\n"
            text += f"  _{product['description']}_\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"💳 Acheter {product['name']}", 
                    callback_data=f"shop_buy_{product['id']}"
                )
            ])
        
        # Ajouter les options de recharge
        keyboard.extend([
            [InlineKeyboardButton("💎 Acheter des crédits", callback_data="shop_buy_credits")],
            [InlineKeyboardButton("📊 Historique achats", callback_data="shop_history")],
            [InlineKeyboardButton("🎁 Codes promo", callback_data="shop_promo")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /buy - Acheter un produit spécifique"""
        if not context.args:
            await update.message.reply_text("❌ Usage: /buy <id_produit>")
            return
        
        product_id = context.args[0]
        user_id = update.effective_user.id
        
        # Vérifier si le produit existe
        product = self.get_product_by_id(product_id)
        if not product:
            await update.message.reply_text("❌ Produit non trouvé.")
            return
        
        # Vérifier les crédits
        user_credits = self.db.get_user_credits(user_id)
        if user_credits < product['price']:
            needed = product['price'] - user_credits
            await update.message.reply_text(
                f"❌ Crédits insuffisants!\n"
                f"Prix: {product['price']} crédits\n"
                f"Vos crédits: {user_credits}\n"
                f"Il vous manque: {needed} crédits\n\n"
                f"💎 Utilisez /shop pour acheter des crédits."
            )
            return
        
        # Confirmer l'achat
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmer", callback_data=f"shop_confirm_{product_id}"),
                InlineKeyboardButton("❌ Annuler", callback_data="shop_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🛒 **Confirmation d'achat**\n\n"
            f"Produit: {product['name']}\n"
            f"Prix: {product['price']} crédits\n"
            f"Vos crédits: {user_credits}\n"
            f"Après achat: {user_credits - product['price']} crédits\n\n"
            f"Confirmer l'achat?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def credits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /credits - Affiche les crédits de l'utilisateur"""
        user_id = update.effective_user.id
        credits = self.db.get_user_credits(user_id)
        
        # Historique des transactions récentes
        transactions = self.db.get_user_transactions(user_id, limit=5)
        
        text = f"""💰 **Vos Crédits**

💎 Solde actuel: **{credits}** crédits

📈 **Transactions récentes:**
"""
        
        if transactions:
            for transaction in transactions:
                emoji = "+" if transaction['type'] == 'credit' else "-"
                text += f"{emoji}{transaction['amount']} - {transaction['description']} ({transaction['date']})\n"
        else:
            text += "Aucune transaction récente."
        
        keyboard = [
            [InlineKeyboardButton("💳 Acheter des crédits", callback_data="shop_buy_credits")],
            [InlineKeyboardButton("🏪 Boutique", callback_data="shop_main")],
            [InlineKeyboardButton("📊 Historique complet", callback_data="shop_full_history")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des callbacks de la boutique"""
        query = update.callback_query
        data = query.data
        user_id = query.from_user.id
        
        await query.answer()
        
        if data.startswith("shop_buy_"):
            product_id = data.split("_")[2]
            if product_id == "credits":
                await self.show_credit_packages(query)
            else:
                await self.process_purchase(query, product_id)
        
        elif data.startswith("shop_confirm_"):
            product_id = data.split("_")[2]
            await self.confirm_purchase(query, product_id)
        
        elif data == "shop_cancel":
            await query.edit_message_text("❌ Achat annulé.")
        
        elif data == "shop_history":
            await self.show_purchase_history(query)
        
        elif data == "shop_promo":
            await self.show_promo_codes(query)
        
        elif data == "shop_main":
            await self.show_main_shop(query)
        
        elif data.startswith("credits_"):
            package = data.split("_")[1]
            await self.buy_credit_package(query, package)
        
        elif data.startswith("payment_"):
            method = data.split("_")[1]
            amount = float(data.split("_")[2])
            await self.process_payment(query, method, amount)
    
    @staticmethod
    async def show_credit_packages(query):
        """Affiche les packages de crédits"""
        text = """💎 **Packages de Crédits**

Sélectionnez un package:"""
        
        packages = [
            {'id': 'small', 'credits': 100, 'price': 1.99, 'bonus': 0},
            {'id': 'medium', 'credits': 500, 'price': 8.99, 'bonus': 50},
            {'id': 'large', 'credits': 1000, 'price': 15.99, 'bonus': 150},
            {'id': 'mega', 'credits': 2500, 'price': 34.99, 'bonus': 500}
        ]
        
        keyboard = []
        for package in packages:
            total_credits = package['credits'] + package['bonus']
            bonus_text = f" (+{package['bonus']} bonus)" if package['bonus'] > 0 else ""
            
            text += f"\n💰 **{total_credits} crédits** - {package['price']}€{bonus_text}"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"💳 {total_credits} crédits - {package['price']}€",
                    callback_data=f"credits_{package['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="shop_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def buy_credit_package(query, package_id):
        """Achète un package de crédits"""
        packages = {
            'small': {'credits': 100, 'price': 1.99, 'bonus': 0},
            'medium': {'credits': 500, 'price': 8.99, 'bonus': 50},
            'large': {'credits': 1000, 'price': 15.99, 'bonus': 150},
            'mega': {'credits': 2500, 'price': 34.99, 'bonus': 500}
        }
        
        package = packages.get(package_id)
        if not package:
            await query.edit_message_text("❌ Package non trouvé.")
            return
        
        total_credits = package['credits'] + package['bonus']
        
        text = f"""💳 **Achat de Crédits**

Package sélectionné: {total_credits} crédits
Prix: {package['price']}€

Choisissez votre méthode de paiement:"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Carte bancaire (Stripe)", callback_data=f"payment_stripe_{package['price']}")],
            [InlineKeyboardButton("₿ Cryptomonnaies", callback_data=f"payment_crypto_{package['price']}")],
            [InlineKeyboardButton("📱 Telegram Payments", callback_data=f"payment_telegram_{package['price']}")],
            [InlineKeyboardButton("💎 Mes crédits", callback_data=f"payment_credits_{package['price']}")],
            [InlineKeyboardButton("🔙 Retour", callback_data="shop_buy_credits")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def process_payment(self, query, method, amount):
        """Traite le paiement via le PaymentManager"""
        user_id = query.from_user.id
        
        if not self.payment_manager:
            await self.simulate_old_payment(query, method, amount)
            return
        
        try:
            # Déterminer la méthode de paiement
            if method == "stripe":
                payment_method = self.PaymentMethod.STRIPE
            elif method == "crypto":
                payment_method = self.PaymentMethod.CRYPTO
            elif method == "telegram":
                payment_method = self.PaymentMethod.TELEGRAM
            elif method == "credits":
                payment_method = self.PaymentMethod.CREDITS
            else:
                await query.edit_message_text("❌ Méthode de paiement non supportée.")
                return
            
            # Créer l'intention de paiement
            payment_intent = await self.payment_manager.create_payment_intent(
                user_id=user_id,
                amount=amount,
                currency="EUR",
                method=payment_method,
                description=f"Achat de crédits - {amount}€",
                metadata={'package_type': 'credits', 'source': 'shop'}
            )
            
            if payment_intent.get('error'):
                await query.edit_message_text(f"❌ Erreur: {payment_intent['error']}")
                return
            
            # Afficher les instructions selon la méthode
            if payment_method == self.PaymentMethod.STRIPE:
                await self.show_stripe_instructions(query, payment_intent)
            elif payment_method == self.PaymentMethod.CRYPTO:
                await self.show_crypto_instructions(query, payment_intent)
            elif payment_method == self.PaymentMethod.TELEGRAM:
                await self.show_telegram_instructions(query, payment_intent)
            elif payment_method == self.PaymentMethod.CREDITS:
                await self.show_credits_result(query, payment_intent)
            
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement du paiement: {e}")
            await query.edit_message_text("❌ Erreur lors du traitement du paiement.")
    
    @staticmethod
    async def show_stripe_instructions(query, payment_intent):
        """Affiche les instructions pour Stripe"""
        text = f"""💳 **Paiement Stripe (Simulation)**

Montant: {payment_intent['amount']}€
ID Paiement: `{payment_intent['payment_id'][:8]}...`

🔄 **Instructions de paiement:**
"""
        
        if payment_intent.get('simulation'):
            text += """
Dans un environnement réel:
1. Redirection vers Stripe Checkout
2. Saisie sécurisée des informations de carte
3. Validation 3D Secure si nécessaire
4. Confirmation automatique

✅ **Paiement simulé confirmé!**
Vos crédits ont été ajoutés automatiquement."""
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmer paiement (simulation)", callback_data=f"confirm_payment_{payment_intent['payment_id']}")],
            [InlineKeyboardButton("🔙 Retour", callback_data="shop_buy_credits")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def show_crypto_instructions(query, payment_intent):
        """Affiche les instructions pour crypto"""
        crypto_info = payment_intent
        
        text = f"""₿ **Paiement Cryptomonnaies (Simulation)**

Montant: {crypto_info['amount']}€

**Adresses de paiement:**
• Bitcoin: `{crypto_info.get('addresses', {}).get('BTC', 'Génération en cours...')}`
• Ethereum: `{crypto_info.get('addresses', {}).get('ETH', 'Génération en cours...')}`
• USDT: `{crypto_info.get('addresses', {}).get('USDT', 'Génération en cours...')}`

**Montants:**
• BTC: {crypto_info.get('amount_crypto', {}).get('BTC', '0.00000000')}
• ETH: {crypto_info.get('amount_crypto', {}).get('ETH', '0.000000')}
• USDT: {crypto_info.get('amount_crypto', {}).get('USDT', '0.00')}

⏰ **Expire dans:** 2 heures

📱 **Instructions:**
1. Ouvrez votre wallet crypto
2. Scannez le QR code ou copiez l'adresse
3. Envoyez le montant exact
4. Confirmation automatique après 1-3 blocs"""
        
        if crypto_info.get('simulation'):
            text += "\n\n✅ **Mode simulation:** Paiement confirmé automatiquement!"
        
        keyboard = [
            [InlineKeyboardButton("✅ Simuler paiement", callback_data=f"confirm_payment_{crypto_info['payment_id']}")],
            [InlineKeyboardButton("📋 Copier adresse BTC", callback_data="copy_btc_address")],
            [InlineKeyboardButton("🔙 Retour", callback_data="shop_buy_credits")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def show_telegram_instructions(query, payment_intent):
        """Affiche les instructions pour Telegram Payments"""
        text = f"""📱 **Telegram Payments (Simulation)**

Montant: {payment_intent['amount']}€
ID Paiement: `{payment_intent['payment_id'][:8]}...`

🔄 **Traitement via Telegram Payments...**

Dans un environnement réel:
• Interface de paiement native Telegram
• Support des principales cartes bancaires
• Traitement sécurisé par Telegram
• Confirmation instantanée

✅ **Paiement simulé validé!**
Vos crédits ont été ajoutés à votre compte."""
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirmer (simulation)", callback_data=f"confirm_payment_{payment_intent['payment_id']}")],
            [InlineKeyboardButton("🔙 Retour", callback_data="shop_buy_credits")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def show_credits_result(query, payment_intent):
        """Affiche le résultat du paiement par crédits"""
        if payment_intent['status'] == 'completed':
            text = f"""✅ **Paiement par crédits réussi!**

Transaction: `{payment_intent['payment_id'][:8]}...`
Crédits utilisés: {payment_intent['credits_used']}
Crédits restants: {payment_intent['remaining_credits']}

🎉 Votre achat a été traité avec succès!"""
        else:
            text = f"""❌ **Paiement échoué**

Raison: {payment_intent.get('error', 'Erreur inconnue')}

💡 Vérifiez votre solde ou utilisez une autre méthode de paiement."""
        
        keyboard = [[InlineKeyboardButton("🔙 Retour à la boutique", callback_data="shop_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def simulate_old_payment(self, query, method, amount):
        """Simulation de paiement (fallback si PaymentManager indisponible)"""
        text = f"""💳 **Paiement {method.title()} (Simulation)**

Montant: {amount}€

🔄 Traitement du paiement en cours...

✅ **Paiement simulé avec succès!**
Vos crédits ont été ajoutés à votre compte."""
        
        # Ajouter les crédits (simulation)
        credits_to_add = int(amount * 100)  # 1€ = 100 crédits
        self.db.add_user_credits(query.from_user.id, credits_to_add, f"Achat par {method} (simulation)")
        
        keyboard = [[InlineKeyboardButton("🏪 Retour à la boutique", callback_data="shop_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def confirm_purchase(self, query, product_id):
        """Confirme l'achat d'un produit"""
        user_id = query.from_user.id
        product = self.get_product_by_id(product_id)
        
        if not product:
            await query.edit_message_text("❌ Produit non trouvé.")
            return
        
        # Vérifier les crédits
        user_credits = self.db.get_user_credits(user_id)
        if user_credits < product['price']:
            await query.edit_message_text("❌ Crédits insuffisants!")
            return
        
        # Effectuer l'achat
        success = self.db.purchase_product(user_id, product_id, product['price'])
        
        if success:
            # Appliquer les effets du produit
            if product['type'] == 'subscription':
                self.db.activate_premium(user_id, duration_days=30)
            elif product['type'] == 'credits':
                bonus_credits = int(product['name'].split()[0])  # Extraire le nombre
                self.db.add_user_credits(user_id, bonus_credits, f"Achat {product['name']}")
            
            await query.edit_message_text(
                f"✅ **Achat réussi!**\n\n"
                f"Produit: {product['name']}\n"
                f"Prix: {product['price']} crédits\n\n"
                f"Merci pour votre achat! 🎉",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Erreur lors de l'achat. Veuillez réessayer.")
    
    async def show_purchase_history(self, query):
        """Affiche l'historique des achats"""
        user_id = query.from_user.id
        purchases = self.db.get_user_purchases(user_id, limit=10)
        
        if not purchases:
            text = "📊 **Historique des achats**\n\nAucun achat effectué."
        else:
            text = "📊 **Historique des achats**\n\n"
            for purchase in purchases:
                text += f"• {purchase['product_name']} - {purchase['price']} crédits\n"
                text += f"  _{purchase['purchased_at']}_\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="shop_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def show_promo_codes(query):
        """Affiche la section codes promo"""
        text = """🎁 **Codes Promo**

Entrez un code promo pour recevoir des bonus!

Codes valides (exemples de simulation):
• `WELCOME50` - 50 crédits bonus
• `PREMIUM20` - 20% de réduction premium
• `REFER100` - 100 crédits de parrainage

💡 Astuce: Parrainez des amis pour obtenir des codes exclusifs!

📝 Pour utiliser un code promo, tapez: `/promo <code>`"""
        
        keyboard = [
            [InlineKeyboardButton("✏️ Utiliser un code", callback_data="shop_enter_promo")],
            [InlineKeyboardButton("🤝 Programme parrainage", callback_data="main_referral")],
            [InlineKeyboardButton("🔙 Retour", callback_data="shop_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    def load_products():
        """Charge les produits depuis la configuration"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('shop', {}).get('products', [])
        except:
            return []
    
    def get_product_by_id(self, product_id):
        """Récupère un produit par son ID"""
        products = self.load_products()
        for product in products:
            if product['id'] == product_id:
                return product
        return None
    
    async def show_main_shop(self, query):
        """Affiche la boutique principale"""
        # Recréer l'affichage de la boutique
        user_id = query.from_user.id
        user_credits = self.db.get_user_credits(user_id)
        products = self.load_products()
        
        text = f"""🏪 **Boutique TeleSuche**

💰 Vos crédits: **{user_credits}** crédits

🛍️ **Produits disponibles:**

"""
        
        keyboard = []
        for product in products:
            text += f"• **{product['name']}** - {product['price']} crédits\n"
            text += f"  _{product['description']}_\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"💳 Acheter {product['name']}", 
                    callback_data=f"shop_buy_{product['id']}"
                )
            ])
        
        keyboard.extend([
            [InlineKeyboardButton("💎 Acheter des crédits", callback_data="shop_buy_credits")],
            [InlineKeyboardButton("📊 Historique achats", callback_data="shop_history")],
            [InlineKeyboardButton("🎁 Codes promo", callback_data="shop_promo")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def process_purchase(self, query, product_id):
        """Traite l'achat d'un produit spécifique"""
        product = self.get_product_by_id(product_id)
        if not product:
            await query.edit_message_text("❌ Produit non trouvé.")
            return
        
        user_id = query.from_user.id
        user_credits = self.db.get_user_credits(user_id)
        
        if user_credits < product['price']:
            needed = product['price'] - user_credits
            await query.edit_message_text(
                f"❌ **Crédits insuffisants!**\n\n"
                f"Produit: {product['name']}\n"
                f"Prix: {product['price']} crédits\n"
                f"Vos crédits: {user_credits}\n"
                f"Il vous manque: {needed} crédits\n\n"
                f"💎 Achetez des crédits d'abord!",
                parse_mode='Markdown'
            )
            return
        
        # Confirmer l'achat
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirmer", callback_data=f"shop_confirm_{product_id}"),
                InlineKeyboardButton("❌ Annuler", callback_data="shop_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🛒 **Confirmation d'achat**\n\n"
            f"Produit: {product['name']}\n"
            f"Description: {product['description']}\n"
            f"Prix: {product['price']} crédits\n\n"
            f"Vos crédits: {user_credits}\n"
            f"Après achat: {user_credits - product['price']} crédits\n\n"
            f"Confirmer l'achat?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
