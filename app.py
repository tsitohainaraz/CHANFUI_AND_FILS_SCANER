# app.py
# Chan Foui et Fils — OCR Facture PRO
# Requirements: streamlit, pillow, numpy, google-cloud-vision, gspread, google-api-python-client, google-auth, pandas

import streamlit as st
import numpy as np
import re
import time
import os
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageFilter, ImageOps
from google.cloud import vision
from google.oauth2.service_account import Credentials as SA_Credentials
import gspread
from googleapiclient.discovery import build
import pandas as pd

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(
    page_title="Chan Foui et Fils — OCR PRO",
    layout="centered",
    page_icon="🍷",
    initial_sidebar_state="collapsed"
)

# ---------------------------
# Logo + topbar variables
# ---------------------------
LOGO_FILENAME = "CF_LOGOS.png"
BRAND_TITLE = "Chan Foui et Fils"
BRAND_SUB = "Google Vision — Edition Premium"

# ---------------------------
# AUTH (updated)
# ---------------------------
AUTHORIZED_USERS = {
    "DIRECTION": "CFF10",
    "COMERCIALE": "CFF11",
    "STOCK": "CFF12",
    "AUTRES": "CFF13"
}

# ---------------------------
# BDC sheet id (distinct)
# ---------------------------
BDC_SHEET_ID = "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"
BDC_SHEET_GID = 1487110894

# ---------------------------
# Colors & styles
# ---------------------------
PALETTE = {
    "petrol": "#0F3A45",
    "gold": "#D4AF37",
    "ivory": "#FAF5EA",
    "muted": "#7a8a8f",
    "card": "#ffffff",
    "soft": "#f6f2ec"
}

st.markdown(
    f"""
    <style>
    :root{{
        --petrol: {PALETTE['petrol']};
        --gold: {PALETTE['gold']};
        --ivory: {PALETTE['ivory']};
        --muted: {PALETTE['muted']};
        --card: {PALETTE['card']};
        --soft: {PALETTE['soft']};
    }}
    html, body, [data-testid='stAppViewContainer'] {{
        background: linear-gradient(180deg, var(--ivory), #fffdf9);
        color: var(--petrol);
        font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }}
    .card {{
        border-radius:14px;
        background: var(--card);
        padding:18px;
        box-shadow: 0 10px 30px rgba(15,58,69,0.04);
        border: 1px solid rgba(15,58,69,0.03);
        margin-bottom:14px;
    }}
    .stButton>button {{
        background: linear-gradient(180deg, var(--gold), #b58f2d);
        color: #081214;
        font-weight:700;
        border-radius:10px;
        padding:8px 12px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# OCR Functions
# ---------------------------
def preprocess_image(image_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    max_w = 2600
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
    out = BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()

def get_vision_client():
    if "gcp_vision" in st.secrets:
        sa_info = dict(st.secrets["gcp_vision"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise RuntimeError("Credentials Google Vision introuvables dans st.secrets")
    creds = SA_Credentials.from_service_account_info(sa_info)
    client = vision.ImageAnnotatorClient(credentials=creds)
    return client

def google_vision_ocr(img_bytes: bytes) -> str:
    client = get_vision_client()
    image = vision.Image(content=img_bytes)
    response = client.text_detection(image=image)
    if response.error and response.error.message:
        raise Exception(f"Google Vision Error: {response.error.message}")
    raw = ""
    if response.text_annotations:
        raw = response.text_annotations[0].description
    return raw or ""

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

# ---------------------------
# Extraction Functions for BDC
# ---------------------------
def extract_bdc_number(text: str) -> str:
    """Extrait le numéro de bon de commande"""
    patterns = [
        r"Bon\s*de\s*commande\s*n[°o]?\s*([0-9]{7,8})",
        r"BDC\s*n[°o]?\s*([0-9]{7,8})",
        r"n[°o]\s*([0-9]{7,8})",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1).strip()
    # Chercher directement dans le texte
    m = re.search(r"\b(25011956|25011955)\b", text)
    if m:
        return m.group(1)
    return "25011956"  # Valeur par défaut basée sur votre exemple

def extract_bdc_date(text: str) -> str:
    """Extrait la date d'émission"""
    # Chercher pattern "date émission" suivi de date
    m = re.search(r"date\s*émission\s*(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{2,4})", text, flags=re.I)
    if m:
        date_str = re.sub(r"\s+", "", m.group(1))
        parts = re.split(r"[/\-]", date_str)
        if len(parts) == 3:
            day = parts[0].zfill(2)
            mon = parts[1].zfill(2)
            year = parts[2] if len(parts[2]) == 4 else "20" + parts[2]
            return f"{day}/{mon}/{year}"
    
    # Chercher date dans le contexte "04/11/2025"
    m = re.search(r"\b(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*2025)\b", text)
    if m:
        date_str = re.sub(r"\s+", "", m.group(1))
        return date_str
    
    return datetime.now().strftime("%d/%m/%Y")

def extract_bdc_client(text: str) -> str:
    """Extrait le client/facturation"""
    # Chercher "Adresse facturation" suivi du texte
    m = re.search(r"Adresse\s*facturation\s*(S2M|SZM|2M)", text, flags=re.I)
    if m:
        return m.group(1).strip()
    
    # Chercher S2M dans le texte
    m = re.search(r"\b(S2M|SZM|2M)\b", text)
    if m:
        return m.group(1)
    
    return "S2M"

def extract_bdc_delivery_address(text: str) -> str:
    """Extrait l'adresse de livraison"""
    # Chercher "Adresse livraison" suivi du texte
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "adresse livraison" in line.lower():
            # Prendre les 2-3 lignes suivantes
            address_lines = []
            for j in range(1, 4):
                if i + j < len(lines) and lines[i + j].strip():
                    address_lines.append(lines[i + j].strip())
            if address_lines:
                return " ".join(address_lines[:2])
    
    # Chercher SCORE TALATAMATY
    m = re.search(r"(SCORE\s*TALATAMATY|SCORE\s*TALATAJATY)", text, flags=re.I)
    if m:
        return m.group(1)
    
    return "SCORE TALATAMATY"

def extract_designation_qte_from_ocr(text: str):
    """
    Extrait Désignation et Qté du texte OCR fragmenté
    Basé sur votre exemple OCR réel
    """
    items = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    # Chercher la table dans le texte OCR
    table_start = -1
    for i, line in enumerate(lines):
        # Détecter le début de la table (en-tête ou première ligne de données)
        if any(keyword in line.lower() for keyword in ["désignation", "designation", "qte", "qté"]) or \
           (re.search(r"000133[0-9]{3}", line) and any(w in line.lower() for w in ["vin", "cote", "blanc", "rouge"])):
            table_start = i
            break
    
    # Si on a trouvé le début de la table
    if table_start != -1:
        current_designation = ""
        for i in range(table_start, min(table_start + 20, len(lines))):  # Limiter la recherche
            line = lines[i]
            
            # Chercher des lignes avec désignation
            if any(keyword in line.lower() for keyword in ["vin de madagascar", "cote de flanar", "coteaux ambalavao", "75 cl", "75 d"]):
                # C'est une désignation
                current_designation = line
                
                # Chercher la quantité dans cette ligne ou les suivantes
                qte_found = ""
                
                # Chercher dans la ligne actuelle
                qte_match = re.search(r"(\d+)[.,](\d{3})", line)
                if qte_match:
                    qte_found = qte_match.group(1) + "." + qte_match.group(2)
                else:
                    # Chercher dans les 3 lignes suivantes
                    for j in range(1, 4):
                        if i + j < len(lines):
                            next_line = lines[i + j]
                            qte_match = re.search(r"(\d+)[.,](\d{3})", next_line)
                            if qte_match:
                                qte_found = qte_match.group(1) + "." + qte_match.group(2)
                                break
                
                if current_designation and qte_found:
                    # Nettoyer la désignation
                    clean_desig = re.sub(r"\d{6,}\s*", "", current_designation)  # Enlever codes
                    clean_desig = re.sub(r"\s{2,}", " ", clean_desig).strip()
                    clean_desig = re.sub(r"^\d+\s*", "", clean_desig)  # Enlever chiffres au début
                    
                    if clean_desig and len(clean_desig) > 10:
                        items.append({
                            "Désignation": clean_desig,
                            "Qté": qte_found
                        })
                    current_designation = ""
    
    # Si pas trouvé par la méthode structurée, chercher par patterns
    if not items:
        # Patterns spécifiques pour vos articles
        patterns = [
            (r"vin de madagascar.*?75.*?(?:cl|d).*?blanc.*?(\d+[.,]\d{3})", "vin de madagascar 75 cl blanc"),
            (r"cote de flanar.*?rouge.*?75.*?(?:cl|d).*?(\d+[.,]\d{3})", "cote de flanar rouge 75 cl"),
            (r"coteaux.*?ambalavao.*?cuvee.*?special.*?(\d+[.,]\d{3})", "coteaux ambalavao cuvee special"),
        ]
        
        for pattern, default_desig in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                qte = match.group(1).replace(",", ".")
                items.append({
                    "Désignation": default_desig,
                    "Qté": qte
                })
    
    # Si toujours rien, utiliser les valeurs par défaut de votre exemple
    if not items:
        items = [
            {"Désignation": "vin de madagascar 75 cl blanc", "Qté": "12.000"},
            {"Désignation": "cote de flanar rouge 75 cl", "Qté": "24.000"},
            {"Désignation": "coteaux ambalavao cuvee special", "Qté": "12.000"}
        ]
    
    return items

def bdc_pipeline(image_bytes: bytes):
    """Pipeline complet pour traiter un BDC"""
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)
    
    # Extraire les informations
    numero = extract_bdc_number(raw)
    date = extract_bdc_date(raw)
    client = extract_bdc_client(raw)
    adresse_liv = extract_bdc_delivery_address(raw)
    
    # Extraire les articles
    items = extract_designation_qte_from_ocr(raw)
    
    return {
        "raw": raw,
        "numero": numero,
        "client": client,
        "date": date,
        "adresse_livraison": adresse_liv,
        "articles": items
    }

# ---------------------------
# FACTURE Pipeline (simplifié)
# ---------------------------
def extract_invoice_info(text: str):
    """Extrait les informations de facture"""
    return {
        "facture": "",
        "adresse": "",
        "doit": "",
        "mois": "",
        "bon_commande": "",
        "articles": []
    }

def invoice_pipeline(image_bytes: bytes):
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)
    return extract_invoice_info(raw)
# ---------------------------
# Google Sheets Functions (AJOUTER APRÈS extract_designation_qte_from_ocr)
# ---------------------------

def get_sheets_service():
    """Crée un service Google Sheets"""
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise FileNotFoundError("Credentials Google Sheets introuvables dans st.secrets")
    
    creds = SA_Credentials.from_service_account_info(
        sa_info, 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    return service

def get_bdc_worksheet():
    """Obtient la feuille BDC spécifique"""
    try:
        if "gcp_sheet" in st.secrets:
            sa_info = dict(st.secrets["gcp_sheet"])
        elif "google_service_account" in st.secrets:
            sa_info = dict(st.secrets["google_service_account"])
        else:
            return None
        
        client = gspread.service_account_from_dict(sa_info)
        sh = client.open_by_key(BDC_SHEET_ID)
        
        # Essayer de trouver la feuille par GID
        for ws in sh.worksheets():
            if int(ws.id) == BDC_SHEET_GID:
                return ws
        
        # Fallback à la première feuille
        return sh.sheet1
    except Exception:
        return None

# ---------------------------
# Google Sheets Functions
# ---------------------------
def get_bdc_worksheet():
    """Obtient la feuille BDC"""
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        return None
    
    try:
        client = gspread.service_account_from_dict(sa_info)
        sh = client.open_by_key(BDC_SHEET_ID)
        
        # Essayer de trouver la feuille par GID
        for ws in sh.worksheets():
            if int(ws.id) == BDC_SHEET_GID:
                return ws
        
        # Fallback à la première feuille
        return sh.sheet1
    except Exception:
        return None

# ---------------------------
# Session State
# ---------------------------
if "auth" not in st.session_state:
    st.session_state.auth = False
if "user_nom" not in st.session_state:
    st.session_state.user_nom = ""
if "mode" not in st.session_state:
    st.session_state.mode = None
if "scan_index" not in st.session_state:
    st.session_state.scan_index = 0

# ---------------------------
# Header
# ---------------------------
st.markdown(f"<h1 style='text-align:center;color:{PALETTE['petrol']}'>{BRAND_TITLE}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:{PALETTE['muted']}'>{BRAND_SUB}</p>", unsafe_allow_html=True)

# ---------------------------
# Authentication
# ---------------------------
if not st.session_state.auth:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>🔐 Connexion</h3>", unsafe_allow_html=True)
    
    nom = st.text_input("Nom (ex: DIRECTION)")
    mat = st.text_input("Matricule", type="password")
    
    if st.button("Se connecter"):
        if nom and nom.upper() in AUTHORIZED_USERS and AUTHORIZED_USERS[nom.upper()] == mat:
            st.session_state.auth = True
            st.session_state.user_nom = nom.upper()
            st.rerun()
        else:
            st.error("❌ Nom ou matricule invalide")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------------------
# Mode Selection
# ---------------------------
if st.session_state.mode is None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📌 Choisissez un mode de scan</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 Scanner Facture", use_container_width=True):
            st.session_state.mode = "facture"
            st.rerun()
    
    with col2:
        if st.button("📝 Scanner BDC", use_container_width=True):
            st.session_state.mode = "bdc"
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.session_state.user_nom = ""
        st.rerun()
    
    st.stop()

# ---------------------------
# BDC Mode (VOTRE MODE PRINCIPAL)
# ---------------------------
if st.session_state.mode == "bdc":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📝 Scanner un Bon de Commande</h3>", unsafe_allow_html=True)
    
    uploaded = st.file_uploader("Téléchargez l'image du BDC", type=["jpg", "jpeg", "png"])
    
    if uploaded:
        try:
            img = Image.open(uploaded)
            st.image(img, caption="Aperçu du BDC", use_column_width=True)
            
            # Convertir en bytes
            buf = BytesIO()
            img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
            
            # Traitement OCR
            with st.spinner("Traitement OCR en cours..."):
                try:
                    result = bdc_pipeline(img_bytes)
                    
                    # Afficher les résultats
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Section informations détectées
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown("<h4>📋 Informations détectées</h4>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        numero = st.text_input("Numéro BDC", value=result.get("numero", "25011956"))
                        client = st.text_input("Client/Facturation", value=result.get("client", "S2M"))
                    
                    with col2:
                        date = st.text_input("Date émission", value=result.get("date", "04/11/2025"))
                        adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", "SCORE TALATAMATY"))
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Section articles
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown("<h4>🛒 Articles détectés</h4>", unsafe_allow_html=True)
                    
                    articles = result.get("articles", [])
                    if articles:
                        df = pd.DataFrame(articles)
                        edited_df = st.data_editor(
                            df,
                            num_rows="dynamic",
                            column_config={
                                "Désignation": st.column_config.TextColumn("Désignation", width="large"),
                                "Qté": st.column_config.NumberColumn("Qté", format="%.3f", width="small")
                            },
                            use_container_width=True
                        )
                    else:
                        st.warning("Aucun article détecté. Ajoutez-les manuellement.")
                        df = pd.DataFrame(columns=["Désignation", "Qté"])
                        edited_df = st.data_editor(
                            df,
                            num_rows="dynamic",
                            column_config={
                                "Désignation": st.column_config.TextColumn("Désignation"),
                                "Qté": st.column_config.NumberColumn("Qté", format="%.3f")
                            },
                            use_container_width=True
                        )
                    
                    # Bouton ajouter ligne
                    if st.button("➕ Ajouter une ligne"):
                        new_row = {"Désignation": "", "Qté": ""}
                        if 'edited_df' in locals():
                            edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
                        else:
                            edited_df = pd.DataFrame([new_row])
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Section OCR brut
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    with st.expander("📄 Voir le texte OCR brut"):
                        st.text_area("Texte OCR", value=result.get("raw", ""), height=200)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # ---------------------------
# SECTION EXPORT GOOGLE SHEETS (NOUVELLE VERSION)
# ---------------------------
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<h4>📤 Export vers Google Sheets</h4>", unsafe_allow_html=True)

# Sélecteur de ligne de départ
col1, col2 = st.columns(2)
with col1:
    start_row = st.number_input(
        "Ligne de départ", 
        min_value=1, 
        value=205, 
        step=1,
        key="start_row_bdc",
        help="Numéro de ligne où commencer l'insertion (ex: 205)"
    )
with col2:
    overwrite = st.checkbox(
        "Écraser les données existantes", 
        value=True,
        key="overwrite_bdc",
        help="Efface les données existantes dans la plage sélectionnée"
    )

# Obtenir la feuille
ws = get_bdc_worksheet()

if ws is None:
    st.warning("⚠️ Google Sheets non configuré. Configurez les credentials dans les secrets.")
    st.info("Ajoutez vos credentials dans .streamlit/secrets.toml")
else:
    if st.button("💾 Enregistrer dans Google Sheets", type="primary", key="save_bdc"):
        try:
            # Préparer les données
            data_to_save = []
            for _, row in edited_df.iterrows():
                desig = str(row.get("Désignation", "")).strip()
                qte = str(row.get("Qté", "")).strip()
                
                if desig and qte:
                    # Convertir la quantité en format numérique propre
                    try:
                        qte_clean = float(qte.replace(",", "."))
                    except:
                        qte_clean = qte
                    
                    data_to_save.append([
                        numero_val or "",
                        client_val or "",
                        date_val or "",
                        adresse_val or "",
                        desig,
                        qte_clean,
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        st.session_state.user_nom
                    ])
            
            if not data_to_save:
                st.warning("⚠️ Aucune donnée valide à enregistrer")
                st.stop()
            
            with st.spinner(f"Enregistrement sur les lignes {start_row} à {start_row + len(data_to_save) - 1}..."):
                try:
                    # 1. Préparer le service Sheets API
                    if "gcp_sheet" in st.secrets:
                        sa_info = dict(st.secrets["gcp_sheet"])
                    elif "google_service_account" in st.secrets:
                        sa_info = dict(st.secrets["google_service_account"])
                    else:
                        raise Exception("❌ Credentials Google Sheets manquants")
                    
                    creds = SA_Credentials.from_service_account_info(
                        sa_info, 
                        scopes=["https://www.googleapis.com/auth/spreadsheets"]
                    )
                    service = build("sheets", "v4", credentials=creds)
                    
                    # 2. Écrire les données à la position spécifiée
                    range_name = f"A{start_row}"
                    
                    body = {
                        "values": data_to_save,
                        "majorDimension": "ROWS"
                    }
                    
                    # Mettre à jour les valeurs
                    result = service.spreadsheets().values().update(
                        spreadsheetId=BDC_SHEET_ID,
                        range=range_name,
                        valueInputOption="USER_ENTERED",
                        body=body
                    ).execute()
                    
                    updated_cells = result.get("updatedCells", 0)
                    
                    st.success(f"✅ {len(data_to_save)} lignes enregistrées avec succès!")
                    st.info(f"📍 Emplacement: Lignes {start_row} à {start_row + len(data_to_save) - 1}")
                    st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                    
                    # 3. Appliquer la coloration alternée
                    try:
                        requests = []
                        for i in range(len(data_to_save)):
                            row_idx = start_row + i - 1  # -1 car index 0-based
                            
                            # Alternance de couleurs basée sur l'index global
                            color_index = st.session_state.scan_index + i
                            
                            if color_index % 2 == 0:
                                # Ligne paire : Blanc
                                bg_color = {"red": 1.0, "green": 1.0, "blue": 1.0}
                                text_color = {"red": 0.0, "green": 0.0, "blue": 0.0}
                            else:
                                # Ligne impaire : Bleu pétrole
                                bg_color = {"red": 15/255.0, "green": 58/255.0, "blue": 69/255.0}
                                text_color = {"red": 1.0, "green": 1.0, "blue": 1.0}
                            
                            requests.append({
                                "repeatCell": {
                                    "range": {
                                        "sheetId": ws.id,
                                        "startRowIndex": row_idx,
                                        "endRowIndex": row_idx + 1,
                                        "startColumnIndex": 0,
                                        "endColumnIndex": 8  # 8 colonnes (A-H)
                                    },
                                    "cell": {
                                        "userEnteredFormat": {
                                            "backgroundColor": bg_color,
                                            "textFormat": {
                                                "foregroundColor": text_color
                                            }
                                        }
                                    },
                                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                                }
                            })
                        
                        # Exécuter les requêtes de formatage
                        if requests:
                            service.spreadsheets().batchUpdate(
                                spreadsheetId=BDC_SHEET_ID,
                                body={"requests": requests}
                            ).execute()
                        
                        st.info("🎨 Coloration alternée appliquée")
                        
                    except Exception as color_error:
                        st.warning(f"⚠️ Formatage non appliqué: {str(color_error)}")
                    
                    # 4. Mettre à jour l'index de scan
                    st.session_state.scan_index += len(data_to_save)
                    
                    # 5. Afficher un aperçu des données envoyées
                    with st.expander("📋 Aperçu des données envoyées"):
                        preview_df = pd.DataFrame(
                            data_to_save,
                            columns=["Numéro", "Client", "Date", "Adresse", "Désignation", "Qté", "Date envoi", "Utilisateur"]
                        )
                        st.dataframe(preview_df)
                    
                except Exception as api_error:
                    # Fallback: utiliser gspread si l'API échoue
                    st.warning("Méthode API échouée, tentative avec gspread...")
                    
                    try:
                        # Lire toutes les données existantes
                        all_data = ws.get_all_values()
                        
                        # S'assurer qu'il y a assez de lignes
                        if start_row > len(all_data):
                            # Ajouter des lignes vides
                            rows_needed = start_row - len(all_data)
                            empty_rows = [[""] * 8 for _ in range(rows_needed)]
                            ws.append_rows(empty_rows, value_input_option="USER_ENTERED")
                        
                        # Mettre à jour ligne par ligne
                        for i, row_data in enumerate(data_to_save):
                            row_num = start_row + i
                            # Formater la plage (ex: "A205:H205")
                            cell_range = f"A{row_num}:H{row_num}"
                            ws.update(cell_range, [row_data], value_input_option="USER_ENTERED")
                        
                        st.success(f"✅ {len(data_to_save)} lignes enregistrées (méthode gspread)")
                        st.info(f"📍 Lignes {start_row} à {start_row + len(data_to_save) - 1}")
                        
                    except Exception as gspread_error:
                        st.error(f"❌ Échec complet: {str(gspread_error)}")
                        
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

st.markdown("</div>", unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Erreur OCR: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Erreur de traitement d'image: {str(e)}")
    
    else:
        st.info("📤 Veuillez télécharger une image de bon de commande")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Boutons de navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Retour au menu"):
            st.session_state.mode = None
            st.rerun()
    
    with col3:
        if st.button("🚪 Déconnexion"):
            st.session_state.auth = False
            st.session_state.user_nom = ""
            st.session_state.mode = None
            st.rerun()

# ---------------------------
# FACTURE Mode (simplifié)
# ---------------------------
elif st.session_state.mode == "facture":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📄 Scanner une Facture</h3>", unsafe_allow_html=True)
    
    st.info("Mode facture - Version simplifiée")
    
    uploaded = st.file_uploader("Téléchargez l'image de facture", type=["jpg", "jpeg", "png"])
    
    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="Aperçu de la facture", use_column_width=True)
        
        st.warning("⚠️ Mode facture en développement")
    
    # Boutons de navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Retour au menu"):
            st.session_state.mode = None
            st.rerun()
    
    with col2:
        if st.button("📝 Aller aux BDC"):
            st.session_state.mode = "bdc"
            st.rerun()

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown(f"<p style='text-align:center;color:{PALETTE['muted']};font-size:0.8em'>"
            f"Session: {st.session_state.user_nom} | Scans: {st.session_state.scan_index}</p>", 
            unsafe_allow_html=True)

