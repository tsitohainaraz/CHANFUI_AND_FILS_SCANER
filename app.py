# app.py (Version complète Noir & Or – CHAN FOU I & FILS)
# -----------------------------------------------------------------------------
# NOTE : Remplace les parties marquées par VOS VALEURS dans Streamlit Secrets.
# Assure-toi que ton fichier CF_LOGOS.png est dans le même dossier que app.py
# -----------------------------------------------------------------------------

import streamlit as st
import base64
from google.cloud import vision
import gspread
from google.oauth2 import service_account
from PIL import Image
import io

# ================================
# THEME NOIR & OR SUPER PREMIUM
# ================================
st.markdown("""
<style>
body, .main { background-color: #0A0A0A !important; color: #F8F5E6 !important; }
h1, h2, h3, h4, h5 { font-family: 'Georgia', serif !important; color: #E3C778 !important; letter-spacing: 1px !important; }
p, span, div { color: #F8F5E6 !important; }
.stButton button { background: linear-gradient(135deg, #CBA135 0%, #8F6B20 100%); color: black !important; padding: 0.75rem 1.4rem; border-radius: 10px; border: none; font-size: 17px; font-weight: bold; transition: 0.3s; box-shadow: 0px 0px 12px rgba(203,161,53,0.4); }
.stButton button:hover { background: linear-gradient(135deg, #E3C778 0%, #CBA135 100%); box-shadow: 0px 0px 18px rgba(227,199,120,0.6); }
.card { background-color: #111111; padding: 28px; border-radius: 14px; border-left: 4px solid #CBA135; box-shadow: 0px 0px 22px rgba(203,161,53,0.15); }
footer { text-align: center; color: #E3C778 !important; margin-top: 2rem; font-size: 14px; }
hr { border: 1px solid #CBA135; }
</style>
""", unsafe_allow_html=True)

# ================================
# LOGO & TITRE PREMIUM
# ================================
st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
st.image("CF_LOGOS.png", width=160)
st.markdown("""
<h1 style='text-align:center; font-family:Georgia;'>Maison CHAN FOU I & FILS</h1>
<p style='text-align:center; font-style:italic; color:#E3C778;'>Excellence • Tradition • Vins d’Exception</p>
""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ================================
# CHARGEMENT DES SECRETS
# ================================
try:
    vision_credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_vision"])
    sheet_credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_sheet"])
except Exception:
    st.error("❌ Erreur : Impossible de charger les credentials GCP. Vérifie st.secrets !")
    st.stop()

# ================================
# INITIALISATION GOOGLE SHEETS
# ================================
try:
    gc = gspread.authorize(sheet_credentials)
    sh = gc.open_by_key(st.secrets["sheet_id"])
    worksheet = sh.sheet1
except Exception:
    st.error("❌ Impossible de se connecter à Google Sheets. Vérifie sheet_id et gcp_sheet.")
    st.stop()

# ================================
# OCR GOOGLE VISION
# ================================
def extract_text_from_image(image_bytes):
    try:
        client = vision.ImageAnnotatorClient(credentials=vision_credentials)
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        if response.error.message:
            raise Exception(response.error.message)
        return response.text_annotations[0].description if response.text_annotations else ""
    except Exception as e:
        st.error(f"Erreur OCR : {e}")
        return ""

# ================================
# INTERFACE PRINCIPALE
# ================================
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.subheader("📤 Importer une facture pour OCR")
uploaded_file = st.file_uploader("Choisir une image", type=["jpg", "jpeg", "png"])
st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Image importée", use_column_width=True)
    img_bytes = uploaded_file.read()

    if st.button("✨ Lancer l'analyse OCR (Google Vision)"):
        with st.spinner("Analyse en cours..."):
            extracted_text = extract_text_from_image(img_bytes)

        st.markdown("---")
        st.subheader("📑 Résultat OCR :")
        st.text_area("Texte extrait", extracted_text, height=200)

        if extracted_text:
            if st.button("📥 Enregistrer dans Google Sheets"):
                try:
                    worksheet.append_row([extracted_text])
                    st.success("✔ Données enregistrées avec succès dans Google Sheets !")
                except Exception as e:
                    st.error(f"Erreur lors de l'enregistrement : {e}")

# ================================
# FOOTER
# ================================
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>© 2025 — Maison CHAN FOU I & FILS, Vins d’Exception</p>", unsafe_allow_html=True)

```python
import streamlit as st
from PIL import Image
import base64
import io

# ===================== CONFIG APP =====================
st.set_page_config(page_title="CF & FILS — Premium Wine", page_icon="🍷", layout="wide")

# ===================== STYLES =====================
st.markdown(
    """
    <style>
        body {
            background-color: #0D0D0D;
        }
        .main {
            background-color: #0D0D0D !important;
        }
        .title {
            color: #D4AF37;
            font-size: 3rem;
            font-weight: 700;
            text-align: center;
            margin-top: -30px;
        }
        .subtitle {
            color: white;
            font-size: 1.2rem;
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-box {
            border: 2px dashed #D4AF37;
            padding: 30px;
            border-radius: 15px;
            background-color: rgba(212, 175, 55, 0.05);
        }
        .result-box {
            background-color: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ===================== HEADER WITH LOGO =====================
col1, col2, col3 = st.columns([1,2,1])
with col2:
    try:
        logo = Image.open("CF_LOGOS.png")
        st.image(logo, use_column_width=True)
    except:
        st.error("⚠️ Logo introuvable. Assurez-vous que 'CF_LOGOS.png' est dans le même dossier.")

st.markdown("<div class='title'>CF & FILS — PREMIUM WINE</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Application interne — Gestion, Analyse & OCR de documents</div>", unsafe_allow_html=True)

# ===================== SIDEBAR =====================
st.sidebar.markdown("## 🍇 Menu")
menu = st.sidebar.radio(
    "Navigation",
    ["Accueil", "OCR Document", "Catalogue Vin", "À propos"]
)

# ===================== PAGE — ACCUEIL =====================
if menu == "Accueil":
    st.markdown("### 🏆 Bienvenue dans l’application CF & FILS")
    st.markdown(
        "Découvrez une expérience premium pour gérer vos documents, vos fiches de vin et vos analyses internes."
    )

# ===================== PAGE — OCR =====================
elif menu == "OCR Document":
    st.markdown("## 📄 OCR — Extraction de texte depuis une image")

    uploaded = st.file_uploader("Importer une image", type=["png", "jpg", "jpeg"], label_visibility="visible")

    if uploaded:
        st.markdown("### 📌 Aperçu de l’image")
        st.image(uploaded, width=400)

        img_bytes = uploaded.read()

        # Appel OCR fictif — remplacer par votre API
        st.markdown("### 🧠 Résultat OCR")
        st.markdown(
            f"<div class='result-box'>Texte détecté :<br><br><code>{"Démo : remplacer par votre OCR"}</code></div>",
            unsafe_allow_html=True
        )

# ===================== PAGE — CATALOGUE =====================
elif menu == "Catalogue Vin":
    st.markdown("## 🍷 Catalogue Premium")
    st.write("Cette section pourra afficher vos produits, vos stocks et vos fiches techniques.")

# ===================== PAGE — ABOUT =====================
elif menu == "À propos":
    st.markdown("## 🏛️ À propos de CF & FILS")
    st.write("Entreprise spécialisée dans les vins premium et services associés.")
```
