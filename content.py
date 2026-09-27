"""All user-facing texts, keyed by language, plus the shared CSS.

To add a language later: copy TEXTS["fr"], translate it, and change LANG.
Every fixed line Salma says lives here (they are pre-generated to audio).
"""
import streamlit as st

LANG = "fr"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap');
html, body, p, li, label, input, textarea, button, h1, h2, h3, h4,
[data-testid="stMarkdownContainer"] { font-family: 'Atkinson Hyperlegible', sans-serif !important; }
html, body, p, li, label, input, .stMarkdown { font-size: 22px !important; }
h1 { font-size: 32px !important; }
h2 { font-size: 30px !important; }
h3 { font-size: 28px !important; }
.stApp { background: #ffffff; color: #111111; }
.block-container { max-width: 560px; padding: 1rem 1rem 4rem 1rem; }
.stElementContainer:has(.stButton), .stElementContainer:has(.stFormSubmitButton), .stButton, .stFormSubmitButton,
.stButton button, .stFormSubmitButton button { width: 100% !important; }
.st-key-btn_hangup, .st-key-btn_hangup .stButton, .st-key-btn_hangup button { width: auto !important; }
.stButton button, .stFormSubmitButton button {
    min-height: 72px; font-size: 24px !important; font-weight: 700;
    border-radius: 14px; border: 2px solid #0b3d91;
}
.stButton button p, .stFormSubmitButton button p { font-size: 24px !important; }
.st-key-btn_hangup button { background: #c62828 !important; color: #fff !important;
    border-color: #c62828 !important; min-height: 52px; }
.st-key-btn_hangup button p { font-size: 20px !important; }
.reassure { background: #e8f5e9; border-left: 6px solid #2e7d32; color: #1b3d1f;
    padding: 8px 14px; border-radius: 8px; margin: 4px 0 12px 0; font-weight: 700; }
.card { border: 2px solid #0b3d91; border-radius: 14px; padding: 16px 20px; margin: 8px 0 16px 0; }
.balance { font-size: 40px; font-weight: 800; color: #0b3d91; }
.bill { background: #fffde7; border: 2px dashed #555; border-radius: 8px; padding: 16px 20px; margin-bottom: 12px; }
.bill .top { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.bill .ref { font-size: 26px; font-weight: 800; padding: 2px 6px; border-radius: 6px; }
.sms { background: #eeeeee; border-radius: 18px; padding: 14px 18px; margin: 8px 0 16px 0; }
.lesson { background: #f3f6fc; border-radius: 14px; padding: 16px 20px; margin: 8px 0 16px 0; }
.big-value { font-size: 30px; font-weight: 800; color: #2e7d32; }
/* Salma's call panel */
.callpanel { display: flex; gap: 14px; align-items: flex-start; background: #0b1f44; color: #fff;
    border-radius: 16px; padding: 14px; margin: 4px 0 12px 0; }
.avatar { flex: 0 0 64px; height: 64px; border-radius: 50%; background: #ffd9b3;
    display: flex; align-items: center; justify-content: center; font-size: 38px; }
.avatar.speaking { animation-name: pulse; animation-duration: 1.2s; animation-timing-function: ease-in-out; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255,214,0,.8); }
                   70% { box-shadow: 0 0 0 16px rgba(255,214,0,0); }
                   100% { box-shadow: 0 0 0 0 rgba(255,214,0,0); } }
.subs { flex: 1; font-size: 20px; line-height: 1.35; }
.subs p { margin: 0 0 6px 0; font-size: 19px !important; color: #fff; }
.subs .you { color: #b3d4ff; }
.thinking { color: #ffd600; font-weight: 700; }
/* Salma pointing at an element (see highlight_css) */
@keyframes point { 0%,100% { outline-color: #ffd600; } 50% { outline-color: #ff9800; } }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def highlight_css(element_id):
    """Thick yellow outline around one element, like a finger on a shared screen.
    Works for our HTML cards (id=...) and Streamlit widgets (key=... gives class st-key-...)."""
    if not element_id:
        return
    st.markdown(
        f"<style>#{element_id}, .st-key-{element_id} {{ outline: 7px solid #ffd600; outline-offset: 5px;"
        f" border-radius: 12px; animation: point 1.2s ease-in-out infinite; }}</style>",
        unsafe_allow_html=True,
    )


def reassure(text):
    st.markdown(f'<div class="reassure">{text}</div>', unsafe_allow_html=True)


WALLET = {
    "balance": 500.00,
    "biller": "Régie Ville",
    "bill_type": "Électricité",
    "bill_date": "12/09/2026",
    "reference": "EL-4471-2093",
    "amount": 187.50,
    "otp": "4821",
}

TEXTS = {
    "fr": {
        "language_name": "français",
        "ui": {
            "reassure": "🛡️ Entraînement · argent fictif",
            # Consent (app.py)
            "consent_title": "👋 Bienvenue",
            "consent_body": (
                "Ici, vous allez **apprendre** à payer une facture avec votre téléphone, "
                "avec l'aide de **Salma**, au téléphone.\n\n"
                "- 🎭 C'est **anonyme** : pas de nom, pas de numéro de téléphone.\n"
                "- 💵 L'argent est **faux**. Rien n'est payé pour de vrai.\n"
                "- 📝 Nous gardons seulement vos **clics** et le **texte** de vos questions. "
                "Votre voix n'est jamais enregistrée."
            ),
            "consent_yes": "✅ J'accepte, on commence",
            "consent_no": "❌ Non merci",
            "consent_declined": "D'accord. Vous pouvez revenir quand vous voulez. 🙂",
            "profile_title": "🙂 Quelques questions (facultatif)",
            "age_label": "Votre âge",
            "age_options": ["Moins de 30 ans", "30 – 49 ans", "50 – 64 ans", "65 ans et plus"],
            "edu_label": "Votre niveau d'école",
            "edu_options": ["Pas d'école", "Primaire", "Collège / Lycée", "Université"],
            "profile_save": "💾 Continuer",
            "profile_skip": "⏭️ Passer",
            "go_home": "🏠 Retour à l'accueil",
            "no_session": "Commencez d'abord par la page d'accueil.",
            # Call
            "app_title": "💳 Mahfadati Wallet",
            "call_title": "📞 Salma vous attend",
            "call_intro": "Salma va vous guider, comme au téléphone. Montez le son 🔊.",
            "call_button": "📞 Appeler Salma",
            "call_preparing": "Préparation de l'appel…",
            "call_header": "📞 En appel avec Salma",
            "hangup": "📴 Raccrocher",
            "call_ended": "📴 Appel terminé",
            "call_again": "📞 Rappeler Salma",
            "thinking": "Salma réfléchit…",
            "you": "Vous",
            "salma": "Salma",
            "mic_label": "🎤 Appuyez pour parler à Salma",
            "text_label": "… ou écrivez votre question",
            "send": "📨 Envoyer",
            "mic_unavailable": "Le micro n'est pas disponible. Écrivez votre question ci-dessous.",
            "not_understood": "Je n'ai pas bien entendu. Pouvez-vous répéter ?",
            "lost": "🆘 Je suis perdu(e)",
            "help": "❓ Aide",
            "back": "⬅️ Retour",
            # Learn
            "next": "➡️ Suivant",
            "start_practice": "▶️ Commencer l'entraînement",
            # Wallet screens
            "balance_label": "Votre solde",
            "pay_bill": "🧾 Payer une facture",
            "biller_title": "🏢 Choisissez la facture",
            "biller_electricity": "⚡ Électricité — Régie Ville",
            "biller_water": "💧 Eau — Régie Ville",
            "water_info": "Pour cet entraînement, la facture est une facture d'**électricité** ⚡.",
            "reference_title": "🔢 Numéro de référence",
            "reference_label": "Tapez la référence de la facture",
            "bill_header": "🧾 RÉGIE VILLE — Facture d'électricité",
            "bill_date_label": "Date",
            "bill_ref_label": "Référence",
            "bill_amount_label": "Montant à payer",
            "continue": "➡️ Continuer",
            "confirm_title": "👀 Vérifiez avant de payer",
            "confirm_biller": "Facture",
            "confirm_button": "✅ Confirmer",
            "otp_title": "🔑 Code de confirmation",
            "sms_from": "📩 SMS — Mahfadati",
            "sms_text": "Votre code est 4821. Ne le partagez jamais.",
            "otp_label_A": "Saisissez le code OTP",
            "otp_label_B": "Tapez le code reçu par SMS. Il confirme que c'est bien vous. Il n'envoie pas d'argent.",
            "validate": "✅ Valider",
            "receipt_title": "🎉 Paiement réussi !",
            "new_balance": "Nouveau solde",
            "error_reference": "😊 Ce n'est pas le bon numéro. Pas de souci, réessayez.",
            "error_otp": "😊 Ce n'est pas le bon code. Pas de souci, réessayez.",
            # Journey
            "try_alone": "💪 Essayer seul(e)",
            "alone_badge": "💪 Vous êtes seul(e) · Salma reste en ligne",
            "repeat_yes": "🔁 Refaire avec Salma",
            "repeat_no": "💪 Je continue seul(e)",
            "done_title": "🏆 Vous l'avez fait !",
            "done_time": "Temps pour payer seul(e)",
            "done_value": "⏱️ 2 minutes depuis la maison, au lieu d'un trajet et d'une file d'attente.",
            "restart": "🔁 Recommencer",
            "variant_label": "Variante B (texte OTP amélioré)",
            "sidebar_admin": "🛠️ Testeur / admin",
            # Dashboard
            "dashboard_title": "📊 Tableau de bord",
        },
        # Learn: short spoken lessons (title, text shown and spoken).
        "lessons": [
            {
                "title": "📱 Un paiement numérique, c'est quoi ?",
                "say": (
                    "Un paiement numérique, c'est payer une facture depuis votre téléphone. "
                    "Pas besoin d'aller au guichet, pas besoin de faire la queue."
                ),
            },
            {
                "title": "🔑 Le code reçu par SMS",
                "say": (
                    "Avant de payer, vous recevez un code par SMS. C'est comme une clé envoyée "
                    "seulement à vous. Il prouve que c'est bien vous. Ne le donnez jamais à personne, "
                    "même au téléphone."
                ),
            },
            {
                "title": "🛡️ Ici, rien n'est réel",
                "say": (
                    "Maintenant, on va s'entraîner ensemble avec de l'argent fictif. "
                    "Vous ne pouvez rien casser. Je reste avec vous à chaque étape. C'est clair pour vous ?"
                ),
            },
        ],
        # Fixed lines, pre-generated to audio.
        "lines": {
            "greeting": (
                "Bonjour, je suis Salma. Je suis là pour vous aider, on a tout notre temps. "
                "D'abord, trois petites explications."
            ),
            "alone_intro": "Maintenant, essayez seul. Je reste en ligne si vous avez besoin de moi.",
            "repeat_offer": (
                "Ce n'est pas grave du tout. Voulez-vous refaire un tour avec moi ? "
                "Ou vous pouvez continuer seul."
            ),
            "done": (
                "Félicitations ! Vous avez payé seul, depuis chez vous. "
                "Deux minutes au lieu d'un trajet et d'une file d'attente."
            ),
            "resume": "Je suis de retour. On reprend là où on s'était arrêtés.",
        },
        # Short fillers played while the AI thinks, so there is never silence.
        "fillers": ["Hmm, un instant…", "Je regarde votre écran…"],
        # One spoken instruction per screen in coached mode, with where she points.
        "steps": {
            "home": {"say": "Vous voyez votre solde, cinq cents dirhams. Appuyez sur le bouton « Payer une facture ».",
                     "highlight": "btn_pay"},
            "biller": {"say": "Très bien, c'est exactement ça. Maintenant, choisissez « Électricité ».",
                       "highlight": "btn_elec"},
            "reference": {"say": "Parfait. Regardez la facture en papier. Le numéro de référence est en haut, "
                                 "à côté de la date. Recopiez-le dans la case.",
                          "highlight": "bill_ref"},
            "confirm": {"say": "Très bien. Vérifiez le nom, la référence et le montant. "
                               "Si tout est juste, appuyez sur « Confirmer ».",
                        "highlight": "summary"},
            "otp": {"say": "Vous avez reçu un SMS avec un code. C'est votre clé. Tapez ce code dans la case.",
                    "highlight": "sms"},
            # End of the coached round: hand over to the alone run.
            "receipt": {"say": "Bravo, vous avez payé votre facture ! Maintenant, essayez seul. "
                               "Appuyez sur « Essayer seul » quand vous êtes prêt.",
                        "highlight": "btn_alone"},
        },
        # First reaction to a mistake (fixed). A second mistake on the same step goes to the AI.
        "mistakes": {
            "reference": {"say": "Ce n'est pas grave. Regardez la case jaune en haut de la facture, "
                                 "à côté de la date. Recopiez les lettres et les chiffres.",
                          "highlight": "bill_ref"},
            "otp": {"say": "Pas de souci. Le code est dans le SMS gris, ce sont quatre chiffres. "
                           "Tapez-les dans la case.",
                    "highlight": "sms"},
        },
        # What Salma "sees" on each screen (screen share), the element ids she can point at,
        # and the validated facts she may use. The LLM must not go beyond these.
        "screens": {
            "lesson": {
                "visible": "Une carte de leçon avec un titre et un court texte, et un bouton Suivant.",
                "ids": ["lesson_card", "btn_next"],
                "facts": (
                    "Un paiement numérique permet de payer une facture depuis son téléphone, sans guichet. "
                    "Le code SMS est une clé à usage unique envoyée seulement à la personne; il prouve que "
                    "c'est bien elle; il ne faut jamais le donner à personne, même au téléphone. "
                    "L'entraînement utilise de l'argent fictif."
                ),
            },
            "home": {
                "visible": "L'accueil du portefeuille Mahfadati: le solde 500,00 MAD (balance) et un grand "
                           "bouton « Payer une facture » juste en dessous (btn_pay).",
                "ids": ["balance", "btn_pay", "btn_lost"],
                "facts": "Pour payer une facture, on appuie sur « Payer une facture ». Le solde est fictif.",
            },
            "biller": {
                "visible": "Deux boutons: « Électricité — Régie Ville » (btn_elec) et « Eau — Régie Ville » "
                           "(btn_water).",
                "ids": ["btn_elec", "btn_water", "btn_lost"],
                "facts": "La facture de l'entraînement est une facture d'électricité de Régie Ville.",
            },
            "reference": {
                "visible": f"Une facture papier jaune (bill_card). En haut: RÉGIE VILLE, facture d'électricité, "
                           f"date {WALLET['bill_date']}. À côté de la date, la référence {WALLET['reference']} "
                           f"(bill_ref). Plus bas, le montant 187,50 MAD. Sous la facture, une case "
                           f"« Tapez la référence de la facture » (input_ref) et un bouton Continuer.",
                "ids": ["bill_card", "bill_ref", "input_ref", "btn_lost"],
                "facts": (
                    f"La référence identifie la facture. Elle s'écrit {WALLET['reference']}: deux lettres EL, "
                    "puis des chiffres séparés par des tirets. Majuscules, minuscules et espaces n'ont pas d'importance."
                ),
            },
            "confirm": {
                "visible": "Un résumé (summary): Régie Ville — Électricité, référence EL-4471-2093, montant "
                           "187,50 MAD. Un bouton « Confirmer » (btn_confirm).",
                "ids": ["summary", "btn_confirm", "btn_lost"],
                "facts": "Rien n'est payé avant d'avoir tapé le code SMS. On vérifie le nom, la référence et le montant.",
            },
            "otp": {
                "visible": "Une bulle de SMS grise (sms): « Votre code est 4821. Ne le partagez jamais. » "
                           "En dessous, une case pour taper le code (input_otp) et un bouton Valider.",
                "ids": ["sms", "input_otp", "btn_lost"],
                "facts": (
                    "Le code SMS est une clé à usage unique envoyée seulement à la personne. Il confirme que "
                    "c'est bien elle. Il n'envoie pas d'argent. Il ne faut jamais le donner à personne, même "
                    "à quelqu'un qui dit appeler de la banque. Dans l'entraînement, le code est dans la bulle SMS."
                ),
            },
            "receipt": {
                "visible": "Un reçu (receipt): paiement réussi, Régie Ville, référence, montant, nouveau solde 312,50 MAD.",
                "ids": ["receipt", "btn_alone"],
                "facts": "Le paiement est terminé. Le reçu prouve le paiement.",
            },
            "done": {
                "visible": "L'écran de félicitations avec le temps pris pour payer seul.",
                "ids": [],
                "facts": "Payer depuis chez soi prend environ 2 minutes au lieu d'un trajet et d'une file d'attente.",
            },
        },
        # Last fallback when no AI provider answers: a safe, validated answer per screen.
        "cache": {
            "lesson": {"say": "Le code SMS, c'est une clé envoyée seulement à vous. Ne le donnez à personne. "
                              "Appuyez sur « Suivant » pour continuer.", "highlight": "btn_next"},
            "home": {"say": "Appuyez sur le bouton « Payer une facture », juste sous votre solde.",
                     "highlight": "btn_pay"},
            "biller": {"say": "Votre facture est une facture d'électricité. Appuyez sur « Électricité ».",
                       "highlight": "btn_elec"},
            "reference": {"say": "La référence est en haut de la facture, à côté de la date. "
                                 "Recopiez-la dans la case.", "highlight": "bill_ref"},
            "confirm": {"say": "Si le nom, la référence et le montant sont justes, appuyez sur « Confirmer ». "
                               "Rien n'est payé avant le code.", "highlight": "btn_confirm"},
            "otp": {"say": "Le code est dans le SMS gris. C'est une clé pour vous seul. "
                           "Tapez les quatre chiffres dans la case.", "highlight": "sms"},
            "receipt": {"say": "C'est terminé, votre facture est payée.", "highlight": "receipt"},
            "done": {"say": "Bravo, vous avez réussi !", "highlight": None},
        },
    },
}

T = TEXTS[LANG]
UI = T["ui"]
