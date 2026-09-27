"""All user-facing texts and the shared CSS.

# TO REVIEW BY TEAM: French and Darija texts below need a check by a Darija speaker.
"""
import streamlit as st

CSS = """
<style>
html, body, [class*="css"], .stMarkdown, p, li, label { font-size: 22px !important; }
h1 { font-size: 34px !important; }
h2 { font-size: 30px !important; }
h3 { font-size: 28px !important; }
.stApp { background: #ffffff; color: #111111; }
.stButton > button, .stFormSubmitButton > button {
    width: 100%;
    min-height: 72px;
    font-size: 24px !important;
    font-weight: 700;
    border-radius: 14px;
    border: 2px solid #0b3d91;
}
.stButton > button p, .stFormSubmitButton > button p { font-size: 24px !important; }
.stButton > button[kind="primary"] { background: #0b3d91; color: #ffffff; }
.darija { font-style: italic; color: #333333; margin-top: -8px; }
.card {
    border: 2px solid #0b3d91; border-radius: 14px; padding: 16px 20px; margin: 8px 0 16px 0;
}
.balance { font-size: 40px; font-weight: 800; color: #0b3d91; }
.bill { background: #fffde7; border: 2px dashed #555555; border-radius: 8px; padding: 16px 20px; }
.bill .ref { font-size: 28px; font-weight: 800; background: #ffeb3b; padding: 2px 6px; }
.sms { background: #eeeeee; border-radius: 18px; padding: 14px 18px; margin: 8px 0 16px 0; }
.coach { background: #e3f2fd; border-left: 6px solid #0b3d91; padding: 12px 16px; border-radius: 8px; }
.reassure {
    background: #e8f5e9; border-left: 6px solid #2e7d32;
    padding: 12px 16px; border-radius: 8px; margin: 8px 0 16px 0;
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def darija(text):
    """Show a Darija line under a French instruction."""
    st.markdown(f'<p class="darija">🗣️ {text}</p>', unsafe_allow_html=True)


def reassure(text):
    st.markdown(f'<div class="reassure">{text}</div>', unsafe_allow_html=True)


# TO REVIEW BY TEAM
TEXT = {
    "reassure": "🛡️ C'est un entraînement. Pas de vrai argent.",
    "reassure_darija": "Hada ghir tamrin, makaynch flous b s-sa7.",

    # Consent
    "consent_title": "👋 Bienvenue",
    "consent_body": (
        "Ici, vous allez **apprendre** à payer une facture avec votre téléphone.\n\n"
        "- 🎭 C'est **anonyme** : pas de nom, pas de numéro de téléphone.\n"
        "- 💵 L'argent est **faux**. Rien n'est payé pour de vrai.\n"
        "- 📝 Nous gardons seulement vos **clics** et vos **questions écrites**, "
        "pour améliorer l'application."
    ),
    "consent_darija": "Kolchi anonyme, l-flous machi s7a7. Kan7afdo ghir l-clicks w l-as2ila dyalek.",
    "consent_yes": "✅ J'accepte, on commence",
    "consent_no": "❌ Non merci",
    "consent_declined": "D'accord. Vous pouvez revenir quand vous voulez. 🙂",

    # Optional profile
    "profile_title": "🙂 Quelques questions (facultatif)",
    "profile_darija": "Ila bghiti, jaweb. Ila ma bghitich, dghat 3la 'Passer'.",
    "age_label": "Votre âge",
    "age_options": ["Moins de 30 ans", "30 – 49 ans", "50 – 64 ans", "65 ans et plus"],
    "edu_label": "Votre niveau d'école",
    "edu_options": ["Pas d'école", "Primaire", "Collège / Lycée", "Université"],
    "profile_save": "💾 Continuer",
    "profile_skip": "⏭️ Passer",

    # Lesson
    "lesson_title": "📚 Payer avec son téléphone",
    "lesson_body": (
        "### 📱 Un paiement numérique, c'est quoi ?\n"
        "C'est payer une facture **depuis votre téléphone**, sans aller au guichet "
        "et sans faire la queue.\n\n"
        "### 🔑 Le code reçu par SMS\n"
        "Avant de payer, vous recevez un **code par SMS**. "
        "C'est comme **une clé envoyée seulement à vous**. "
        "Il prouve que c'est bien vous.\n\n"
        "**⚠️ Ne donnez jamais ce code à personne**, même au téléphone."
    ),
    "lesson_darija": (
        "L-code li kayjik f SMS b7al chi sarout, ghir nta li 3ndek. "
        "Ma t3tih l 7ta wa7ed."
    ),
    "lesson_start": "▶️ Commencer l'entraînement",

    # Practice
    "practice_title": "💳 Mahfadati Wallet",
    "no_session": "Commencez d'abord par la page d'accueil.",
    "go_home": "🏠 Retour à l'accueil",

    # Dashboard (placeholder until milestone 4)
    "dashboard_title": "📊 Tableau de bord",
}


# ---------------- Practice wallet ----------------
# TO REVIEW BY TEAM
WALLET = {
    "balance": 500.00,
    "biller": "Régie Ville",
    "bill_type": "Électricité",
    "reference": "EL-4471-2093",
    "amount": 187.50,
    "otp": "4821",
}

# TO REVIEW BY TEAM
PRACTICE = {
    "back": "⬅️ Retour",
    "lost": "🆘 Je suis perdu",
    "help": "❓ Aide",
    "mode_title": "🤝 Comment voulez-vous pratiquer ?",
    "mode_darija": "Bghiti m3a l-coach wla bo7dek?",
    "mode_coached": "👩‍🏫 Avec le coach",
    "mode_alone": "💪 Tout seul",
    "balance_label": "Votre solde",
    "pay_bill": "🧾 Payer une facture",
    "biller_title": "🏢 Choisissez la facture",
    "biller_electricity": "⚡ Électricité — Régie Ville",
    "biller_water": "💧 Eau — Régie Ville",
    "water_info": "Pour cet entraînement, la facture est une facture d'**électricité** ⚡.",
    "reference_title": "🔢 Numéro de référence",
    "reference_label": "Tapez la référence de la facture",
    "bill_header": "🧾 RÉGIE VILLE — Facture d'électricité",
    "bill_ref_label": "Référence",
    "bill_amount_label": "Montant à payer",
    "next": "➡️ Continuer",
    "confirm_title": "👀 Vérifiez avant de payer",
    "confirm_biller": "Facture",
    "confirm_button": "✅ Confirmer",
    "otp_title": "🔑 Code de confirmation",
    "sms_from": "📩 SMS — Mahfadati",
    "sms_text": "Votre code est 4821. Ne le partagez jamais.",
    "otp_label_A": "Saisissez le code OTP",
    "otp_label_B": "Ce code confirme que c'est bien vous. Il n'envoie pas d'argent.",
    "validate": "✅ Valider",
    "receipt_title": "🎉 Paiement réussi !",
    "receipt_value": "⏱️ 2 minutes depuis la maison, au lieu d'un trajet et d'une file d'attente.",
    "receipt_value_darija": "Joj d9aye9 men dar, bla ma tmchi w bla ma tsenna f s-sf.",
    "new_balance": "Nouveau solde",
    "restart": "🔁 Recommencer",
    "variant_label": "Variante B (texte OTP amélioré)",
    "sidebar_admin": "🛠️ Testeur / admin",
}

# Instruction per screen: French + Darija. Shown by the coach in "coached" mode.
# TO REVIEW BY TEAM
STEPS = {
    "home": ("Appuyez sur « Payer une facture ».", "Brek 3la « Payer une facture »."),
    "biller": ("Choisissez « Électricité ».", "Khtar « Électricité »."),
    "reference": (
        "Regardez la facture en papier. Recopiez le numéro de référence.",
        "Chouf l-facture. Kteb r-référence li mktouba fiha.",
    ),
    "confirm": (
        "Vérifiez le nom, la référence et le montant. Puis appuyez sur « Confirmer ».",
        "Chouf smiya, r-référence w l-montant. 3ad brek 3la « Confirmer ».",
    ),
    "otp": (
        "Vous avez reçu un SMS avec un code. Tapez ce code ici.",
        "Dkhel l'code li jak f SMS.",
    ),
    "receipt": ("C'est fini ! Vous avez payé votre facture.", "Safi, khlssti l-facture dyalek!"),
}

# Help / cached coach answer per screen (also the last fallback of the coach in milestone 3).
# TO REVIEW BY TEAM
HELP = {
    "home": "Le bouton « Payer une facture » est en bas du solde. / L-bouton ta7t s-solde.",
    "biller": (
        "Votre facture est une facture d'électricité. Appuyez sur « Électricité ». / "
        "L-facture dyalek dyal d-do, brek 3la « Électricité »."
    ),
    "reference": (
        "La référence est sur la facture, en jaune : EL-4471-2093. / "
        "R-référence mktouba f l-facture, b l-asfar: EL-4471-2093."
    ),
    "confirm": (
        "Si tout est correct, appuyez sur « Confirmer ». Rien n'est payé avant le code. / "
        "Ila kolchi mzyan, brek 3la « Confirmer ». Walou ma kaytkhlless 9bel l'code."
    ),
    "otp": (
        "Le code est dans le SMS gris : 4 chiffres. C'est une clé pour vous seul. "
        "Ne le donnez à personne. / L'code f SMS, 4 d l-ar9am. Ma t3tih l 7ta wa7ed."
    ),
    "receipt": "Bravo, c'est terminé ! / Bravo, safi!",
}

# Friendly error messages. TO REVIEW BY TEAM
ERRORS = {
    "reference": (
        "😊 Ce n'est pas le bon numéro. Pas de souci, réessayez.",
        "Machi hada r-ra9m. Ma kayn mouchkil, 3awed.",
    ),
    "otp": (
        "😊 Ce n'est pas le bon code. Pas de souci, réessayez.",
        "Machi hada l'code. Ma kayn mouchkil, 3awed.",
    ),
}
