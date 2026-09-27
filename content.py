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

    # Practice (placeholder until milestone 2)
    "practice_title": "💳 Mahfadati Wallet",
    "no_session": "Commencez d'abord par la page d'accueil.",
    "go_home": "🏠 Retour à l'accueil",

    # Dashboard (placeholder until milestone 4)
    "dashboard_title": "📊 Tableau de bord",
}
