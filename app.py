import streamlit as st
from google.oauth2 import service_account
from google.cloud import vision
from googleapiclient.discovery import build
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
import io
import base64

# ----------------------------
# CONFIGURATION DE LA PAGE
# ----------------------------
st.set_page_config(
    page_title="CHANFUI & FILS SCANNER",
    layout="centered"
)

# ----------------------------
# AFFICHER LE LOGO
# ----------------------------
st.image("CF_LOGOS.png", width=180)


# ----------------------------
#  LOGIN SIMPLE
# ----------------------------
USERS = {
    "CFCOMERCIALE": "B5531",
    "ADMIN": "0000"
}

def login_block():
    st.subheader("🔐 Connexion")

    username = st.text_input("Identifiant")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Connexion"):
        if username in USERS and USERS[username] == password:
            st.session_state["LOGGED"] = True
            st.experimental_rerun()
        else:
            st.error("❌ Identifiants incorrects")

if "LOGGED" not in st.session_state:
    login_block()
    st.stop()


# ----------------------------
# CHARGER LES CREDENTIALS GOOGLE
# ----------------------------
try:
    vision_credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_vision"]
    )

    sheet_credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_sheet"]
    )
except Exception as e:
    st.error("❌ Erreur : Les credentials Google ne sont pas trouvés dans st.secrets.")
    st.stop()

# ----------------------------
# FONCTION OCR GOOGLE VISION
# ----------------------------
def extract_text_from_image(uploaded_bytes):

    client = vision.ImageAnnotatorClient(credentials=vision_credentials)
    image = vision.Image(content=uploaded_bytes)

    response = client.text_detection(image=image)
    texts = response.text_annotations

    if not texts:
        return ""

    return texts[0].description


# ----------------------------
# FONCTION INSERTION GOOGLE SHEET
# ----------------------------
def insert_to_sheet(extracted_text):

    gc = gspread.authorize(sheet_credentials)
    sh = gc.open_by_key(st.secrets["sheet_id"])
    worksheet = sh.sheet1

    worksheet.append_row([extracted_text])


# ----------------------------
#    UI PRINCIPALE
# ----------------------------
st.title("📄 CHANFUI & FILS — OCR Scanner")
st.write("Scanne automatiquement vos factures et enregistre dans Google Sheet.")

uploaded_file = st.file_uploader("📤 Importer une image", type=["jpg", "jpeg", "png"])

if uploaded_file:

    # afficher image
    img = Image.open(uploaded_file)
    st.image(img, caption="Image importée", width=400)

    bytes_data = uploaded_file.read()

    if st.button("🧠 Lancer OCR"):
        with st.spinner("Analyse en cours…"):
            text = extract_text_from_image(bytes_data)

        st.subheader("📌 Texte extrait :")
        st.text(text)

        if st.button("📥 Enregistrer dans Google Sheet"):
            insert_to_sheet(text)
            st.success("✔ Texte enregistré avec succès dans Google Sheet ! 🎉")
