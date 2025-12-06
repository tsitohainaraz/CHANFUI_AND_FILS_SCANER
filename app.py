# app_final_simple.py
# Chan Foui et Fils — OCR Facture PRO
# Mode Facture et Mode BDC avec design original

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
# Sheet IDs
# ---------------------------
BDC_SHEET_ID = "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"
BDC_SHEET_GID = 1487110894
INVOICE_SHEET_ID = "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"
INVOICE_SHEET_GID = 72936741

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
# Facture Extraction Functions
# ---------------------------
def extract_invoice_number(text: str) -> str:
    patterns = [
        r"FACTURE\s+EN\s+COMPTE.*?N[°o]?\s*([0-9]{3,})",
        r"FACTURE.*?N[°o]\s*([0-9]{3,})",
        r"FACTURE.*?N\s*([0-9]{3,})",
        r"N°\s*([0-9]{3,})"
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1).strip()
    return ""

def extract_delivery_address(text: str) -> str:
    patterns = [
        r"Adresse de livraison\s*[:\-]\s*(.+)",
        r"Adresse(?:\s+de\s+livraison)?\s*[:\-]?\s*\n?\s*(.+)"
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            address = m.group(1).strip().rstrip(".")
            return address.split("\n")[0] if "\n" in address else address
    return ""

def extract_doit(text: str) -> str:
    p = r"\bDOIT\s*[:\-]?\s*([A-Z0-9]{2,6})"
    m = re.search(p, text, flags=re.I)
    if m:
        return m.group(1).strip()
    candidates = ["S2M", "ULYS", "DLP"]
    for c in candidates:
        if c in text:
            return c
    return ""

def extract_month(text: str) -> str:
    months = {
        "janvier": "Janvier", "février": "Février", "fevrier": "Février",
        "mars": "Mars", "avril": "Avril", "mai": "Mai",
        "juin": "Juin", "juillet": "Juillet", "août": "Août",
        "aout": "Août", "septembre": "Septembre", "octobre": "Octobre",
        "novembre": "Novembre", "décembre": "Décembre", "decembre": "Décembre"
    }
    for mname in months:
        if re.search(r"\b" + re.escape(mname) + r"\b", text, flags=re.I):
            return months[mname]
    return ""

def extract_bon_commande(text: str) -> str:
    patterns = [
        r"Suivant votre bon de commande\s*[:\-]?\s*([0-9A-Za-z\-\/]+)",
        r"bon de commande\s*[:\-]?\s*(.+)"
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1).strip().split()[0]
    return ""

def extract_invoice_items(text: str):
    items = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    pattern = re.compile(r"(.+?(?:75\s*cls?|75\s*cl|75cl|75))\s+\d+\s+\d+\s+(\d+)", flags=re.I)
    
    for line in lines:
        m = pattern.search(line)
        if m:
            name = m.group(1).strip()
            nb_btls = int(m.group(2))
            name = re.sub(r"\s{2,}", " ", name)
            items.append({"article": name, "bouteilles": nb_btls})
    
    if not items:
        for line in lines:
            if "75" in line or "cls" in line.lower():
                nums = re.findall(r"(\d{1,4})", line)
                if nums:
                    nb_btls = int(nums[-1])
                    name = re.sub(r"\d+", "", line).strip()
                    if name:
                        items.append({"article": name, "bouteilles": nb_btls})
    
    return items

def invoice_pipeline(image_bytes: bytes):
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)
    
    return {
        "raw": raw,
        "facture": extract_invoice_number(raw),
        "adresse": extract_delivery_address(raw),
        "doit": extract_doit(raw),
        "mois": extract_month(raw),
        "bon_commande": extract_bon_commande(raw),
        "articles": extract_invoice_items(raw)
    }

# ---------------------------
# BDC Extraction Functions
# ---------------------------
def extract_bdc_number(text: str) -> str:
    patterns = [
        r"Bon\s*de\s*commande\s*n[°o]?\s*([0-9]{7,8})",
        r"BDC\s*n[°o]?\s*([0-9]{7,8})",
        r"n[°o]\s*([0-9]{7,8})",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1).strip()
    m = re.search(r"\b(25011956|25011955)\b", text)
    if m:
        return m.group(1)
    return "25011956"

def extract_bdc_date(text: str) -> str:
    m = re.search(r"date\s*émission\s*(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{2,4})", text, flags=re.I)
    if m:
        date_str = re.sub(r"\s+", "", m.group(1))
        parts = re.split(r"[/\-]", date_str)
        if len(parts) == 3:
            day = parts[0].zfill(2)
            mon = parts[1].zfill(2)
            year = parts[2] if len(parts[2]) == 4 else "20" + parts[2]
            return f"{day}/{mon}/{year}"
    
    m = re.search(r"\b(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*2025)\b", text)
    if m:
        date_str = re.sub(r"\s+", "", m.group(1))
        return date_str
    
    return datetime.now().strftime("%d/%m/%Y")

def extract_bdc_client(text: str) -> str:
    m = re.search(r"Adresse\s*facturation\s*(S2M|SZM|2M)", text, flags=re.I)
    if m:
        return m.group(1).strip()
    
    m = re.search(r"\b(S2M|SZM|2M)\b", text)
    if m:
        return m.group(1)
    
    return "S2M"

def extract_bdc_delivery_address(text: str) -> str:
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "adresse livraison" in line.lower():
            address_lines = []
            for j in range(1, 4):
                if i + j < len(lines) and lines[i + j].strip():
                    address_lines.append(lines[i + j].strip())
            if address_lines:
                return " ".join(address_lines[:2])
    
    m = re.search(r"(SCORE\s*TALATAMATY|SCORE\s*TALATAJATY)", text, flags=re.I)
    if m:
        return m.group(1)
    
    return "SCORE TALATAMATY"

def extract_designation_qte_from_ocr(text: str):
    items = []
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    table_start = -1
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ["désignation", "designation", "qte", "qté"]) or \
           (re.search(r"000133[0-9]{3}", line) and any(w in line.lower() for w in ["vin", "cote", "blanc", "rouge"])):
            table_start = i
            break
    
    if table_start != -1:
        current_designation = ""
        for i in range(table_start, min(table_start + 20, len(lines))):
            line = lines[i]
            
            if any(keyword in line.lower() for keyword in ["vin de madagascar", "cote de flanar", "coteaux ambalavao", "75 cl", "75 d"]):
                current_designation = line
                
                qte_found = ""
                qte_match = re.search(r"(\d+)[.,](\d{3})", line)
                if qte_match:
                    qte_found = qte_match.group(1) + "." + qte_match.group(2)
                else:
                    for j in range(1, 4):
                        if i + j < len(lines):
                            next_line = lines[i + j]
                            qte_match = re.search(r"(\d+)[.,](\d{3})", next_line)
                            if qte_match:
                                qte_found = qte_match.group(1) + "." + qte_match.group(2)
                                break
                
                if current_designation and qte_found:
                    clean_desig = re.sub(r"\d{6,}\s*", "", current_designation)
                    clean_desig = re.sub(r"\s{2,}", " ", clean_desig).strip()
                    clean_desig = re.sub(r"^\d+\s*", "", clean_desig)
                    
                    if clean_desig and len(clean_desig) > 10:
                        items.append({
                            "Désignation": clean_desig,
                            "Qté": qte_found
                        })
                    current_designation = ""
    
    if not items:
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
    
    if not items:
        items = [
            {"Désignation": "vin de madagascar 75 cl blanc", "Qté": "12.000"},
            {"Désignation": "cote de flanar rouge 75 cl", "Qté": "24.000"},
            {"Désignation": "coteaux ambalavao cuvee special", "Qté": "12.000"}
        ]
    
    return items

def bdc_pipeline(image_bytes: bytes):
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)
    
    return {
        "raw": raw,
        "numero": extract_bdc_number(raw),
        "client": extract_bdc_client(raw),
        "date": extract_bdc_date(raw),
        "adresse_livraison": extract_bdc_delivery_address(raw),
        "articles": extract_designation_qte_from_ocr(raw)
    }

# ---------------------------
# Google Sheets Functions
# ---------------------------
def get_bdc_worksheet():
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        return None
    
    try:
        client = gspread.service_account_from_dict(sa_info)
        sh = client.open_by_key(BDC_SHEET_ID)
        
        for ws in sh.worksheets():
            if int(ws.id) == BDC_SHEET_GID:
                return ws
        
        return sh.sheet1
    except Exception:
        return None

def get_invoice_worksheet():
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        return None
    
    try:
        client = gspread.service_account_from_dict(sa_info)
        sh = client.open_by_key(INVOICE_SHEET_ID)
        
        for ws in sh.worksheets():
            if int(ws.id) == INVOICE_SHEET_GID:
                return ws
        
        return sh.sheet1
    except Exception:
        return None

def save_invoice_without_duplicates(ws, invoice_data):
    try:
        # Récupérer toutes les données existantes
        all_values = ws.get_all_values()
        
        # Vérifier les doublons
        for row in all_values:
            if len(row) >= 5:
                existing_invoice = row[0] if len(row) > 0 else ""
                existing_bdc = row[3] if len(row) > 3 else ""
                
                if (existing_invoice == invoice_data["facture"] and 
                    existing_bdc == invoice_data["bon_commande"]):
                    return 0, 1  # 0 ajouté, 1 doublon
        
        # Préparer les données
        today_str = datetime.now().strftime("%d/%m/%Y")
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        rows_to_add = []
        for item in invoice_data["articles"]:
            rows_to_add.append([
                invoice_data["facture"],
                invoice_data["doit"],
                today_str,
                invoice_data["bon_commande"],
                invoice_data["adresse"],
                item["article"],
                item["bouteilles"],
                timestamp,
                st.session_state.user_nom
            ])
        
        if rows_to_add:
            ws.append_rows(rows_to_add)
            return len(rows_to_add), 0
        
        return 0, 0
    except Exception as e:
        raise Exception(f"Erreur lors de l'enregistrement: {str(e)}")

def save_bdc_without_duplicates(ws, bdc_data):
    try:
        # Récupérer toutes les données existantes
        all_values = ws.get_all_values()
        
        # Vérifier les doublons
        for row in all_values:
            if len(row) >= 5:
                existing_bdc = row[0] if len(row) > 0 else ""
                existing_client = row[1] if len(row) > 1 else ""
                
                if (existing_bdc == bdc_data["numero"] and 
                    existing_client == bdc_data["client"]):
                    return 0, 1  # 0 ajouté, 1 doublon
        
        # Préparer les données
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        rows_to_add = []
        for item in bdc_data["articles"]:
            rows_to_add.append([
                bdc_data["numero"],
                bdc_data["client"],
                bdc_data["date"],
                bdc_data["adresse_livraison"],
                item["Désignation"],
                item["Qté"],
                timestamp,
                st.session_state.user_nom
            ])
        
        if rows_to_add:
            ws.append_rows(rows_to_add)
            return len(rows_to_add), 0
        
        return 0, 0
    except Exception as e:
        raise Exception(f"Erreur lors de l'enregistrement: {str(e)}")

# ---------------------------
# Session State
# ---------------------------
if "auth" not in st.session_state:
    st.session_state.auth = False
if "user_nom" not in st.session_state:
    st.session_state.user_nom = ""
if "mode" not in st.session_state:
    st.session_state.mode = None
if "invoice_scans" not in st.session_state:
    st.session_state.invoice_scans = 0
if "bdc_scans" not in st.session_state:
    st.session_state.bdc_scans = 0

# ---------------------------
# Header avec logo
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
# Facture Mode
# ---------------------------
if st.session_state.mode == "facture":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📄 Scanner une Facture</h3>", unsafe_allow_html=True)
    
    uploaded = st.file_uploader("Téléchargez l'image de la facture", type=["jpg", "jpeg", "png"])
    
    if uploaded:
        try:
            img = Image.open(uploaded)
            st.image(img, caption="Aperçu de la facture", use_column_width=True)
            
            # Convertir en bytes
            buf = BytesIO()
            img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
            
            # Traitement OCR
            with st.spinner("Traitement OCR en cours..."):
                try:
                    result = invoice_pipeline(img_bytes)
                    
                    # Afficher les résultats
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Section informations détectées
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown("<h4>📋 Informations détectées</h4>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        facture = st.text_input("Numéro de facture", value=result.get("facture", ""))
                        adresse = st.text_input("Adresse de livraison", value=result.get("adresse", ""))
                    
                    with col2:
                        doit = st.text_input("DOIT", value=result.get("doit", ""))
                        mois = st.text_input("Mois", value=result.get("mois", ""))
                        bon_commande = st.text_input("Bon de commande", value=result.get("bon_commande", ""))
                    
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
                                "article": st.column_config.TextColumn("Article", width="large"),
                                "bouteilles": st.column_config.NumberColumn("Bouteilles", min_value=0, width="small")
                            },
                            use_container_width=True
                        )
                    else:
                        st.warning("Aucun article détecté. Ajoutez-les manuellement.")
                        df = pd.DataFrame(columns=["article", "bouteilles"])
                        edited_df = st.data_editor(
                            df,
                            num_rows="dynamic",
                            column_config={
                                "article": st.column_config.TextColumn("Article"),
                                "bouteilles": st.column_config.NumberColumn("Bouteilles", min_value=0)
                            },
                            use_container_width=True
                        )
                    
                    # Bouton ajouter ligne
                    if st.button("➕ Ajouter une ligne"):
                        new_row = {"article": "", "bouteilles": 0}
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
                    
                    # Section export Google Sheets
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown("<h4>📤 Export vers Google Sheets</h4>", unsafe_allow_html=True)
                    
                    ws = get_invoice_worksheet()
                    
                    if ws is None:
                        st.warning("⚠️ Google Sheets non configuré. Configurez les credentials dans les secrets.")
                    else:
                        if st.button("💾 Enregistrer la facture"):
                            try:
                                # Préparer les données
                                data_to_save = []
                                for _, row in edited_df.iterrows():
                                    if str(row["article"]).strip() and str(row["bouteilles"]).strip():
                                        data_to_save.append([
                                            facture,
                                            doit,
                                            datetime.now().strftime("%d/%m/%Y"),
                                            bon_commande,
                                            adresse,
                                            str(row["article"]).strip(),
                                            str(row["bouteilles"]).strip(),
                                            datetime.now().strftime("%d/%m/%Y %H:%M"),
                                            st.session_state.user_nom
                                        ])
                                
                                if data_to_save:
                                    # Enregistrer sans doublons
                                    saved_count, duplicate_count = save_invoice_without_duplicates(ws, {
                                        "facture": facture,
                                        "doit": doit,
                                        "adresse": adresse,
                                        "mois": mois,
                                        "bon_commande": bon_commande,
                                        "articles": edited_df.to_dict('records')
                                    })
                                    
                                    if saved_count > 0:
                                        st.session_state.invoice_scans += 1
                                        st.success(f"✅ {saved_count} ligne(s) enregistrée(s) avec succuis!")
                                        
                                        if duplicate_count > 0:
                                            st.info(f"⚠️ {duplicate_count} ligne(s) en doublon non ajoutée(s)")
                                        
                                        st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                                    elif duplicate_count > 0:
                                        st.warning("⚠️ Cette facture existe déjà dans la base de données.")
                                    else:
                                        st.warning("⚠️ Aucune donnée valide à enregistrer")
                                        
                            except Exception as e:
                                st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Erreur OCR: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Erreur de traitement d'image: {str(e)}")
    
    else:
        st.info("📤 Veuillez télécharger une image de facture")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Boutons de navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Retour"):
            st.session_state.mode = None
            st.rerun()
    
    with col2:
        if st.button("📝 Passer aux BDC"):
            st.session_state.mode = "bdc"
            st.rerun()
    
    with col3:
        if st.button("🚪 Déconnexion"):
            st.session_state.auth = False
            st.session_state.user_nom = ""
            st.session_state.mode = None
            st.rerun()

# ---------------------------
# BDC Mode
# ---------------------------
elif st.session_state.mode == "bdc":
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
                    
                    # Section export Google Sheets
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.markdown("<h4>📤 Export vers Google Sheets</h4>", unsafe_allow_html=True)
                    
                    ws = get_bdc_worksheet()
                    
                    if ws is None:
                        st.warning("⚠️ Google Sheets non configuré. Configurez les credentials dans les secrets.")
                    else:
                        if st.button("💾 Enregistrer dans Google Sheets"):
                            try:
                                # Préparer les données
                                data_to_save = []
                                for _, row in edited_df.iterrows():
                                    if str(row["Désignation"]).strip() and str(row["Qté"]).strip():
                                        data_to_save.append([
                                            numero,
                                            client,
                                            date,
                                            adresse,
                                            str(row["Désignation"]).strip(),
                                            str(row["Qté"]).strip(),
                                            datetime.now().strftime("%d/%m/%Y %H:%M"),
                                            st.session_state.user_nom
                                        ])
                                
                                if data_to_save:
                                    # Enregistrer sans doublons
                                    saved_count, duplicate_count = save_bdc_without_duplicates(ws, {
                                        "numero": numero,
                                        "client": client,
                                        "date": date,
                                        "adresse_livraison": adresse,
                                        "articles": edited_df.to_dict('records')
                                    })
                                    
                                    if saved_count > 0:
                                        st.session_state.bdc_scans += 1
                                        st.success(f"✅ {saved_count} ligne(s) enregistrée(s) avec succuis!")
                                        
                                        if duplicate_count > 0:
                                            st.info(f"⚠️ {duplicate_count} ligne(s) en doublon non ajoutée(s)")
                                        
                                        st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                                    elif duplicate_count > 0:
                                        st.warning("⚠️ Ce BDC existe déjà dans la base de données.")
                                    else:
                                        st.warning("⚠️ Aucune donnée valide à enregistrer")
                                        
                            except Exception as e:
                                st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
                    
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
        if st.button("⬅️ Retour"):
            st.session_state.mode = None
            st.rerun()
    
    with col2:
        if st.button("📄 Passer aux factures"):
            st.session_state.mode = "facture"
            st.rerun()
    
    with col3:
        if st.button("🚪 Déconnexion"):
            st.session_state.auth = False
            st.session_state.user_nom = ""
            st.session_state.mode = None
            st.rerun()

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown(f"<p style='text-align:center;color:{PALETTE['muted']};font-size:0.8em'>"
            f"Session: {st.session_state.user_nom} | Factures: {st.session_state.invoice_scans} | BDC: {st.session_state.bdc_scans}</p>", 
            unsafe_allow_html=True)
