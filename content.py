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
/* Salma is heard, not seen: audio players stay invisible (they still play) */
[data-testid="stAudio"] { position: absolute !important; width: 1px; height: 1px; overflow: hidden; opacity: 0; }
/* The fictional payment app */
.st-key-app { border: 2px solid #d8dee9; border-radius: 26px; padding: 14px 16px 20px 16px;
    box-shadow: 0 6px 24px rgba(11,31,68,.10); background: #ffffff; }
.apphead { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;
    margin-bottom: 6px; }
.apphead .brand { font-size: 24px; font-weight: 800; color: #0b3d91; }
.apphead .badge { font-size: 15px; font-weight: 700; color: #1b3d1f; background: #e8f5e9;
    border-radius: 999px; padding: 2px 10px; }
.concept { background: #f3f6fc; border-radius: 16px; padding: 16px 18px; margin: 8px 0 14px 0; }
.st-key-btn_back button, .st-key-btn_lost button { min-height: 52px; }
.st-key-btn_back button p, .st-key-btn_lost button p { font-size: 19px !important; }
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
            "app_title": "💳 Mahfadati",
            # Before the call
            "call_title": "Payer une facture avec votre téléphone",
            "call_intro": "Salma vous guide pas à pas, comme au téléphone. Montez le son 🔊",
            "call_button": "📞 Appeler Salma",
            "chat_placeholder": "✍️ Écrire à Salma…",
            # Call bar
            "call_header": "En appel avec Salma",
            "hangup": "📴 Raccrocher",
            "listening": "🎙️ Salma vous écoute…",
            "speaking": "🔊 Salma parle…",
            "thinking": "⏳ Salma réfléchit…",
            "paused": "🎙️ Micro en pause",
            "nomic": "✍️ Écrivez à Salma en bas (touchez ici pour réessayer le micro)",
            "call_ended": "📴 Appel terminé",
            "call_again": "📞 Rappeler Salma",
            # Consent (inside the call)
            "consent_title": "👋 Avant de commencer",
            "consent_body": (
                "- 🎭 C'est **anonyme** : aucun numéro de téléphone.\n"
                "- 💵 L'argent est **fictif** : rien n'est payé pour de vrai.\n"
                "- 📝 On garde seulement vos **clics** et vos **questions**. Votre voix n'est jamais enregistrée."
            ),
            "consent_yes": "✅ J'accepte",
            "consent_no": "❌ Non merci",
            "declined": "D'accord. Vous pouvez rappeler Salma quand vous voulez. 🙂",
            # Profile (inside the call, optional)
            "profile_title": "🙂 Pour mieux vous aider",
            "profile_hint": "Tout est facultatif.",
            "name_label": "Votre prénom (Salma l'utilise pendant l'appel, il n'est jamais enregistré)",
            "age_label": "Votre âge",
            "age_options": ["Moins de 30 ans", "30 – 49 ans", "50 – 64 ans", "65 ans et plus"],
            "edu_label": "Votre niveau d'école",
            "edu_options": ["Pas d'école", "Primaire", "Collège / Lycée", "Université"],
            "job_label": "Votre activité",
            "job_options": ["Retraité(e)", "Au foyer", "Commerçant(e)", "Salarié(e)", "Autre"],
            "profile_save": "➡️ Continuer",
            "profile_skip": "⏭️ Passer",
            # Concepts
            "understood": "👍 J'ai compris, on essaie",
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
            "otp_label": "Tapez le code reçu par SMS. Il confirme que c'est bien vous. Il n'envoie pas d'argent.",
            "validate": "✅ Valider",
            "receipt_title": "🎉 Paiement réussi !",
            "new_balance": "Nouveau solde",
            "error_reference": "Ce n'est pas le bon numéro. Réessayez.",
            "error_otp": "Ce n'est pas le bon code. Réessayez.",
            "lost": "🆘 Je suis perdu(e)",
            "back": "⬅️ Retour",
            # Journey
            "try_alone": "💪 Essayer seul(e)",
            "alone_badge": "💪 Essai seul · Salma reste en ligne",
            "repeat_yes": "🔁 Refaire avec Salma",
            "repeat_no": "💪 Je continue seul(e)",
            "done_title": "🏆 Vous l'avez fait !",
            "done_time": "Temps pour payer seul(e)",
            "done_value": "⏱️ 2 minutes depuis la maison, au lieu d'un trajet et d'une file d'attente.",
            "restart": "🔁 Recommencer",
            "not_understood": "Je n'ai pas bien entendu. Pouvez-vous répéter ?",
            # Dashboard
            "dashboard_title": "📊 Tableau de bord",
        },
        # Fixed lines, pre-generated to audio.
        "lines": {
            "greeting": (
                "Bonjour, je suis Salma. Je vais vous aider à payer une facture avec votre téléphone, avec de "
                "l'argent fictif. C'est anonyme et votre voix n'est pas enregistrée. Vous êtes d'accord ? "
                "Dites oui, ou appuyez sur « J'accepte »."
            ),
            "profile_intro": (
                "Merci ! Pour mieux vous aider, quelques petites questions. C'est facultatif, "
                "vous pouvez aussi appuyer sur « Passer »."
            ),
            "declined": "D'accord, pas de problème. Au revoir, et à bientôt !",
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
        # Assisted mode: a concept is explained just before the screen where it is used.
        "concepts": {
            "payment": {
                "before": "home",
                "title": "📱 Payer depuis son téléphone",
                "text": "Au lieu d'aller au guichet, vous payez votre facture ici, en quelques touches. "
                        "L'argent part de votre portefeuille Mahfadati.",
                "say": "D'abord, une idée simple. Payer depuis son téléphone, c'est comme payer au guichet, "
                       "mais sans se déplacer et sans faire la queue. On essaie ?",
            },
            "reference": {
                "before": "reference",
                "title": "🔢 La référence de la facture",
                "text": "C'est le numéro de VOTRE facture. Il est écrit sur le papier, en haut, à côté de la date. "
                        "On le recopie pour payer la bonne facture.",
                "say": "Maintenant, la référence. C'est le numéro de votre facture, comme un nom pour elle. "
                       "Il est écrit en haut du papier, à côté de la date. On essaie ?",
            },
            "check": {
                "before": "confirm",
                "title": "👀 Vérifier avant de payer",
                "text": "On regarde toujours le nom, la référence et le montant. "
                        "Rien n'est payé tant que vous n'avez pas tapé le code SMS.",
                "say": "Avant de payer, on vérifie toujours trois choses : le nom, la référence et le montant. "
                       "Et rien n'est payé avant le code. On essaie ?",
            },
            "otp": {
                "before": "otp",
                "title": "🔑 Le code reçu par SMS",
                "text": "C'est une clé envoyée seulement à vous, pour prouver que c'est bien vous. "
                        "Il n'envoie pas d'argent. Ne le donnez jamais à personne, même au téléphone.",
                "say": "Dernière idée, la plus importante. Le code reçu par SMS, c'est une clé envoyée seulement "
                       "à vous. Il prouve que c'est bien vous. Ne le donnez jamais à personne. On essaie ?",
            },
        },
        # One spoken instruction per wallet screen in assisted mode, with where she points.
        "steps": {
            "home": {"say": "Voici votre portefeuille. Votre solde est de cinq cents dirhams. "
                            "Appuyez sur « Payer une facture ».", "highlight": "btn_pay"},
            "biller": {"say": "Très bien, c'est exactement ça. Maintenant, choisissez « Électricité ».",
                       "highlight": "btn_elec"},
            "reference": {"say": "À vous : regardez la facture, et recopiez la référence dans la case.",
                          "highlight": "bill_ref"},
            "confirm": {"say": "Vérifiez le nom, la référence et le montant. "
                               "Si tout est juste, appuyez sur « Confirmer ».", "highlight": "summary"},
            "otp": {"say": "Vous avez reçu le SMS. Tapez le code dans la case.", "highlight": "sms"},
            # End of the assisted round: hand over to the alone run.
            "receipt": {"say": "Bravo, vous avez payé votre facture ! Maintenant, essayez seul. "
                               "Appuyez sur « Essayer seul » quand vous êtes prêt.", "highlight": "btn_alone"},
        },
        # First reaction to a mistake (fixed). A second mistake on the same step goes to the AI.
        "mistakes": {
            "reference": {"say": "Ce n'est pas grave. Regardez la case jaune en haut de la facture, "
                                 "à côté de la date. Recopiez les lettres et les chiffres.", "highlight": "bill_ref"},
            "otp": {"say": "Pas de souci. Le code est dans le SMS gris, ce sont quatre chiffres. "
                           "Tapez-les dans la case.", "highlight": "sms"},
        },
        # What Salma "sees" on each screen (screen share), the element ids she can point at,
        # and the validated facts she may use. The LLM must not go beyond these.
        "screens": {
            "consent": {
                "visible": "Un écran d'accord : c'est anonyme, l'argent est fictif, on garde les clics et les "
                           "questions, pas la voix. Boutons « J'accepte » (btn_accept) et « Non merci » (btn_decline).",
                "ids": ["btn_accept", "btn_decline"],
                "facts": "L'entraînement est anonyme, avec de l'argent fictif. La voix n'est jamais enregistrée. "
                         "On garde seulement les clics et le texte des questions. On peut refuser.",
            },
            "profile": {
                "visible": "Des questions facultatives : prénom (input_name), âge, niveau d'école, activité. "
                           "Boutons « Continuer » (btn_profile) et « Passer » (btn_skip).",
                "ids": ["input_name", "btn_profile", "btn_skip"],
                "facts": "Toutes les questions sont facultatives. Le prénom n'est jamais enregistré.",
            },
            "concept": {
                "visible": "Une carte d'explication (concept_card) et un bouton « J'ai compris, on essaie » "
                           "(btn_understood).",
                "ids": ["concept_card", "btn_understood"],
                "facts": (
                    "Payer depuis son téléphone évite le guichet et la queue. La référence est le numéro de la "
                    "facture, en haut du papier à côté de la date. Avant de payer on vérifie nom, référence et "
                    "montant ; rien n'est payé avant le code SMS. Le code SMS est une clé envoyée seulement à la "
                    "personne, il prouve que c'est bien elle, il n'envoie pas d'argent, il ne faut jamais le donner."
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
                "visible": "Un reçu (receipt): paiement réussi, Régie Ville, référence, montant, nouveau solde "
                           "312,50 MAD, et un bouton « Essayer seul » (btn_alone).",
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
            "consent": {"say": "C'est un entraînement anonyme avec de l'argent fictif. Si vous êtes d'accord, "
                               "dites oui ou appuyez sur « J'accepte ».", "highlight": "btn_accept"},
            "profile": {"say": "Ces questions sont facultatives. Vous pouvez appuyer sur « Passer ».",
                        "highlight": "btn_skip"},
            "concept": {"say": "Prenez votre temps. Quand c'est clair, dites « on essaie » ou appuyez sur le bouton.",
                        "highlight": "btn_understood"},
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
