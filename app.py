import streamlit as st
import re
import pandas as pd
import numpy as np
from io import BytesIO
from PIL import Image, ImageFilter, ImageOps
from google.cloud import vision
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime
import os

# ============================================================
# CONFIGURATION STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Chan Foui & Fils — Scanner Multi-Documents",
    page_icon="🍷",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================
# THÈME CHAN FOUI & FILS
# ============================================================
LOGO_FILENAME = "CF_LOGOS.png"
BRAND_TITLE = "Chan Foui et Fils"
BRAND_SUB = "Google Vision AI — Scanner Multi-Documents"

# Palette de couleurs Chan Foui
PALETTE = {
    "petrol": "#0F3A45",
    "gold": "#D4AF37",
    "ivory": "#FAF5EA",
    "muted": "#7a8a8f",
    "card": "#ffffff",
    "soft": "#f6f2ec"
}

# CSS personnalisé
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
    .secondary-button {{
        background: linear-gradient(180deg, #f0f0f0, #d0d0d0) !important;
        color: #333 !important;
        font-weight:600 !important;
        border-radius:10px !important;
        padding:8px 12px !important;
        border: 1px solid #ccc !important;
    }}
    .logo-title-container {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        margin-bottom: 10px;
    }}
    .logo-img {{
        height: 80px;
        width: auto;
    }}
    .brand-title {{
        color: {PALETTE['petrol']};
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }}
    .brand-sub {{
        color: {PALETTE['muted']};
        text-align: center;
        font-size: 1.1rem;
        margin-top: 0;
    }}
    .doc-type-badge {{
        background: linear-gradient(135deg, var(--gold) 0%, #b58f2d 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 600;
        display: inline-block;
        margin: 10px 0;
    }}
    .upload-section {{
        border: 3px dashed var(--gold);
        border-radius: 15px;
        padding: 40px;
        text-align: center;
        background: rgba(212, 175, 55, 0.05);
        margin: 20px 0;
    }}
    .stat-box {{
        background: var(--petrol);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# AUTHENTIFICATION
# ============================================================
AUTHORIZED_USERS = {
    "LATITIA": "CFF1",
    "ELODIE": "CFF2",
    "PATHOU": "CFF3",
    "ADMIN": "CFF4"
}

# ============================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================
SHEET_IDS = {
    "FACTURE EN COMPTE": "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE",
    "BDC LEADERPRICE": "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE",
    "BDC SUPERMAKI": "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE",
    "BDC ULYS": "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"
}

SHEET_GIDS = {
    "FACTURE EN COMPTE": 72936741,
    "BDC LEADERPRICE": 1487110894,
    "BDC SUPERMAKI": 1487110894,
    "BDC ULYS": 1487110894
}

# ============================================================
# FONCTIONS COMMUNES
# ============================================================
def preprocess_image(image_bytes: bytes) -> bytes:
    """Prétraitement d'image standard"""
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
    """Création du client Google Vision"""
    if "gcp_vision" in st.secrets:
        sa_info = dict(st.secrets["gcp_vision"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise RuntimeError("Credentials Google Vision introuvables dans st.secrets")
    creds = Credentials.from_service_account_info(sa_info)
    client = vision.ImageAnnotatorClient(credentials=creds)
    return client

def google_vision_ocr(img_bytes: bytes) -> str:
    """OCR avec Google Vision AI"""
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
    """Nettoyage du texte OCR"""
    text = text.replace("\r", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

# ============================================================
# FONCTIONS D'EXTRACTION (BACKEND ORIGINAL)
# ============================================================

# ----- FACTURE EN COMPTE -----
def extract_facture(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    result = {
        "date": "",
        "facture_numero": "",
        "adresse_livraison": "",
        "doit": "",
        "mois": "",
        "bon_commande": "",
        "articles": []
    }
    
    # Date
    m = re.search(r"le\s+(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    if m:
        result["date"] = m.group(1)
    
    # Mois
    months = {
        "janvier": "Janvier", "février": "Février", "fevrier": "Février",
        "mars": "Mars", "avril": "Avril", "mai": "Mai",
        "juin": "Juin", "juillet": "Juillet", "août": "Août",
        "aout": "Août", "septembre": "Septembre", "octobre": "Octobre",
        "novembre": "Novembre", "décembre": "Décembre", "decembre": "Décembre"
    }
    for mname in months:
        if re.search(r"\b" + re.escape(mname) + r"\b", text, flags=re.I):
            result["mois"] = months[mname]
            break
    
    # Numéro de facture
    m = re.search(r"FACTURE EN COMPTE\s+N[°o]?\s*(\d+)", text, re.IGNORECASE)
    if m:
        result["facture_numero"] = m.group(1)
    
    # DOIT
    m = re.search(r"DOIT\s*:\s*(S2M|ULYS|DLP)", text, re.IGNORECASE)
    if m:
        result["doit"] = m.group(1)
    
    # Adresse
    m = re.search(r"Adresse de livraison\s*:\s*(.+)", text, re.IGNORECASE)
    if m:
        result["adresse_livraison"] = m.group(1).strip()
    
    # Bon de commande
    patterns = [
        r"Suivant votre bon de commande\s*[:\-]?\s*([0-9A-Za-z\-\/]+)",
        r"bon de commande\s*[:\-]?\s*(.+)"
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            result["bon_commande"] = m.group(1).strip().split()[0]
            break
    
    # Tableau des articles
    in_table = False
    designation_queue = []
    
    def clean_designation(s: str) -> str:
        return re.sub(r"\s{2,}", " ", s).strip()
    
    for line in lines:
        up = line.upper()
        
        if "DÉSIGNATION DES MARCHANDISES" in up:
            in_table = True
            continue
        
        if not in_table:
            continue
        
        if "ARRÊTÉE LA PRÉSENTE FACTURE" in up or "TOTAL HT" in up:
            break
        
        if (
            len(line) > 12
            and not any(x in up for x in ["NB", "BTLL", "PU", "MONTANT", "TOTAL"])
            and not re.fullmatch(r"\d+", line)
        ):
            designation_queue.append(clean_designation(line))
            continue
        
        qty_match = re.search(r"\b(6|12|24|48|60|72|120)\b", line)
        if qty_match and designation_queue:
            qty = int(qty_match.group(1))
            designation = designation_queue.pop(0)
            result["articles"].append({
                "article": designation,
                "bouteilles": qty
            })
    
    return result

# ----- BDC LEADERPRICE -----
def extract_leaderprice(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    result = {
        "client": "LEADER PRICE",
        "numero": "",
        "date": "",
        "adresse_livraison": "SCORE TALATAMATY",
        "articles": []
    }
    
    # Numéro BDC
    m = re.search(r"BCD\d+", text)
    if m:
        result["numero"] = m.group(0)
    
    # Date
    m = re.search(r"Date\s*(\d{2}/\d{2}/\d{2,4})", text)
    if m:
        date_str = re.sub(r"\s+", "", m.group(1))
        parts = re.split(r"[/\-]", date_str)
        if len(parts) == 3:
            day = parts[0].zfill(2)
            mon = parts[1].zfill(2)
            year = parts[2] if len(parts[2]) == 4 else "20" + parts[2]
            result["date"] = f"{day}/{mon}/{year}"
    
    # Tableau des articles
    in_table = False
    designation_queue = []
    
    def clean_designation(s: str) -> str:
        s = re.sub(r"\b\d{4}\b", "", s)
        s = re.sub(r"\s{2,}", " ", s)
        return s.strip()
    
    for line in lines:
        up = line.upper()
        
        if up == "RÉF" or "DÉSIGNATION" in up:
            in_table = True
            continue
        
        if not in_table:
            continue
        
        if "TOTAL HT" in up:
            break
        
        if (
            not re.search(r"\d+\.\d{3}", line)
            and len(line) >= 15
            and not any(x in up for x in [
                "PIÈCES", "C/12", "PX", "REM",
                "MONTANT", "QTÉ", "DATE", "TOTAL"
            ])
        ):
            designation_queue.append(clean_designation(line))
            continue
        
        qty_match = re.search(r"(\d{2,4})\.(\d{3})", line)
        if qty_match and designation_queue:
            qty = f"{qty_match.group(1)}.{qty_match.group(2)}"
            designation = designation_queue.pop(0)
            result["articles"].append({
                "Désignation": designation.title(),
                "Qté": qty
            })
    
    return result

# ----- BDC SUPERMAKI -----
def normalize_designation(designation: str) -> str:
    d = designation.upper()
    d = re.sub(r"\s+", " ", d)
    
    if "COTE DE FIANAR" in d:
        if "ROUGE" in d:
            return "Côte de Fianar Rouge 75 cl"
        if "BLANC" in d:
            return "Côte de Fianar Blanc 75 cl"
        if "ROSE" in d or "ROSÉ" in d:
            return "Côte de Fianar Rosé 75 cl"
        if "GRIS" in d:
            return "Côte de Fianar Gris 75 cl"
        return "Côte de Fianar Rouge 75 cl"
    
    if "CONS" in d and "CHAN" in d:
        return "CONS 2000 CHANFOUI"
    
    if "MAROPARASY" in d:
        return "Maroparasy Rouge 75 cl"
    
    return designation.title()

def extract_bdc_supermaki(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    result = {
        "client": "SUPERMAKI",
        "numero": "",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "adresse_livraison": "",
        "articles": []
    }
    
    # Numéro BDC
    m = re.search(r"Bon de commande n[°o]\s*(\d{8})", text)
    if m:
        result["numero"] = m.group(1)
    
    # Date
    m = re.search(r"Date\s+[ée]mission\s*(\d{2}/\d{2}/\d{4})", text)
    if m:
        result["date"] = m.group(1)
    
    # Adresse livraison
    for i, l in enumerate(lines):
        if "Adresse de livraison" in l and i + 1 < len(lines):
            result["adresse_livraison"] = lines[i + 1]
            break
    
    # Extraction par blocs
    i = 0
    while i < len(lines):
        if re.fullmatch(r"\d{6}", lines[i]):
            if i + 5 < len(lines):
                ean = lines[i + 1]
                designation = lines[i + 2]
                pcb = lines[i + 3]
                nb_colis = lines[i + 4]
                quantite = lines[i + 5]
                
                if (
                    re.fullmatch(r"\d{13}\.?", ean) and
                    any(k in designation.upper() for k in ["COTE", "CONS", "MAROPARASY"]) and
                    pcb.isdigit() and
                    nb_colis.isdigit() and
                    quantite.isdigit()
                ):
                    result["articles"].append({
                        "Désignation": normalize_designation(designation),
                        "Qté": quantite + ".000"
                    })
                    i += 6
                    continue
        i += 1
    
    return result

# ----- BDC ULYS -----
def extract_bdc_ulys(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    result = {
        "client": "ULYS",
        "numero": "",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "articles": []
    }
    
    # Numéro BDC
    m = re.search(r"N[°o]\s*(\d{8,})", text)
    if m:
        result["numero"] = m.group(1)
    
    # Date
    m = re.search(r"Date de la Commande\s*:?[\s\-]*(\d{2}/\d{2}/\d{4})", text)
    if m:
        result["date"] = m.group(1)
    
    # Extraction
    in_table = False
    current_designation = ""
    waiting_qty = False
    
    def is_valid_qty(s: str) -> bool:
        s = s.replace("D", "").replace("O", "0").replace("G", "0")
        return re.fullmatch(r"\d{1,3}", s) is not None
    
    def clean_designation(s: str) -> str:
        s = re.sub(r"\b\d{6,}\b", "", s)
        s = s.replace("PAQ", "").replace("/PC", "")
        s = re.sub(r"\s{2,}", " ", s)
        return s.strip()
    
    for line in lines:
        up = line.upper()
        
        if "DESCRIPTION DE L'ARTICLE" in up:
            in_table = True
            continue
        
        if not in_table:
            continue
        
        if "TOTAL DE LA COMMANDE" in up:
            break
        
        if re.match(r"\d{6}\s+(VINS|CONSIGNE|LIQUEUR)", up):
            continue
        
        if ("VIN " in up or "CONS." in up) and not re.match(r"\d{6,}", line):
            current_designation = clean_designation(line)
            waiting_qty = False
            continue
        
        if up in ["PAQ", "/PC"]:
            waiting_qty = True
            continue
        
        if current_designation and waiting_qty:
            clean = line.replace("D", "").replace("O", "0").replace("G", "0")
            if is_valid_qty(clean):
                result["articles"].append({
                    "Désignation": current_designation.title(),
                    "Qté": clean + ".000"
                })
                waiting_qty = False
                continue
    
    return result

# ============================================================
# GOOGLE SHEETS FUNCTIONS
# ============================================================
def get_worksheet(document_type: str):
    try:
        if "gcp_sheet" in st.secrets:
            sa_info = dict(st.secrets["gcp_sheet"])
        elif "google_service_account" in st.secrets:
            sa_info = dict(st.secrets["google_service_account"])
        else:
            return None
        
        client = gspread.service_account_from_dict(sa_info)
        sheet_id = SHEET_IDS.get(document_type)
        
        if not sheet_id:
            return None
        
        sh = client.open_by_key(sheet_id)
        
        # Chercher la feuille par ID
        target_gid = SHEET_GIDS.get(document_type)
        for ws in sh.worksheets():
            if int(ws.id) == target_gid:
                return ws
        
        return sh.sheet1
        
    except Exception as e:
        st.error(f"Erreur Google Sheets: {str(e)}")
        return None

def save_to_google_sheets(document_type: str, data: dict, user_nom: str):
    ws = get_worksheet(document_type)
    
    if not ws:
        return 0, 1  # Pas de feuille configurée
    
    try:
        # Récupérer toutes les données existantes
        all_values = ws.get_all_values()
        
        # Vérifier les doublons selon le type de document
        duplicate_count = 0
        
        if document_type == "FACTURE EN COMPTE":
            # Vérifier doublons pour facture
            for row in all_values:
                if len(row) >= 7:
                    existing_mois = row[0] if len(row) > 0 else ""
                    existing_bdc = row[3] if len(row) > 3 else ""
                    existing_article = row[5] if len(row) > 5 else ""
                    
                    if (existing_mois == data.get("mois", "") and 
                        existing_bdc == data.get("bon_commande", "") and
                        any(item.get("article") == existing_article for item in data.get("articles", []))):
                        duplicate_count += 1
        else:
            # Vérifier doublons pour BDC
            for row in all_values:
                if len(row) >= 6:
                    existing_bdc = row[2] if len(row) > 2 else ""
                    existing_client = row[1] if len(row) > 1 else ""
                    existing_article = row[4] if len(row) > 4 else ""
                    
                    for item in data.get("articles", []):
                        if (existing_bdc == data.get("numero", "") and 
                            existing_client == data.get("client", "") and
                            existing_article == item.get("Désignation", item.get("article", ""))):
                            duplicate_count += 1
        
        if duplicate_count > 0:
            return 0, duplicate_count
        
        # Préparer les données pour l'insertion
        rows_to_add = []
        
        if document_type == "FACTURE EN COMPTE":
            # Format pour facture: Mois | Doit | Date | Bon de commande | Adresse | Article | Bouteille | Editeur
            for item in data.get("articles", []):
                row = [
                    data.get("mois", ""),
                    data.get("doit", ""),
                    datetime.now().strftime("%d/%m/%Y"),
                    data.get("bon_commande", ""),
                    data.get("adresse_livraison", ""),
                    item.get("article", ""),
                    item.get("bouteilles", ""),
                    user_nom
                ]
                rows_to_add.append(row)
        
        else:  # BDC
            # Format pour BDC: Date émission | Client | Numéro BDC | Adresse | Article | Qte | Editeur
            for item in data.get("articles", []):
                row = [
                    data.get("date", datetime.now().strftime("%d/%m/%Y")),
                    data.get("client", ""),
                    data.get("numero", ""),
                    data.get("adresse_livraison", ""),
                    item.get("Désignation", item.get("article", "")),
                    item.get("Qté", item.get("bouteilles", "")),
                    user_nom
                ]
                rows_to_add.append(row)
        
        # Nettoyer les valeurs NaN
        def clean_value(v):
            if v is None:
                return ""
            if isinstance(v, float):
                if np.isnan(v) or np.isinf(v):
                    return ""
            return str(v)
        
        rows_to_add = [[clean_value(x) for x in row] for row in rows_to_add]
        
        # Ajouter les nouvelles lignes
        if rows_to_add:
            ws.append_rows(rows_to_add)
            return len(rows_to_add), 0
        
        return 0, 0
        
    except Exception as e:
        st.error(f"Erreur d'enregistrement: {str(e)}")
        return 0, 0

# ============================================================
# SESSION STATE
# ============================================================
if "auth" not in st.session_state:
    st.session_state.auth = False
if "user_nom" not in st.session_state:
    st.session_state.user_nom = ""
if "document_type" not in st.session_state:
    st.session_state.document_type = ""
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = None
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "invoice_scans" not in st.session_state:
    st.session_state.invoice_scans = 0
if "bdc_scans" not in st.session_state:
    st.session_state.bdc_scans = 0

# ============================================================
# HEADER AVEC LOGO ET TITRE
# ============================================================
col_logo, col_title = st.columns([1, 3])
with col_logo:
    if os.path.exists(LOGO_FILENAME):
        st.image(LOGO_FILENAME, width=100)
    else:
        st.markdown("🍷")

with col_title:
    st.markdown(f"<h1 class='brand-title'>{BRAND_TITLE}</h1>", unsafe_allow_html=True)

st.markdown(f"<p class='brand-sub'>{BRAND_SUB}</p>", unsafe_allow_html=True)

# ============================================================
# AUTHENTIFICATION
# ============================================================
if not st.session_state.auth:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>🔐 Connexion</h3>", unsafe_allow_html=True)
    
    nom = st.text_input("Nom (ex: admin)")
    mat = st.text_input("code", type="password")
    
    if st.button("Se connecter"):
        if nom and nom.upper() in AUTHORIZED_USERS and AUTHORIZED_USERS[nom.upper()] == mat:
            st.session_state.auth = True
            st.session_state.user_nom = nom.upper()
            st.rerun()
        else:
            st.error("❌ Nom ou matricule invalide")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ============================================================
# SÉLECTION DU TYPE DE DOCUMENT
# ============================================================
if st.session_state.document_type == "":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📌 Choisissez un type de document</h3>", unsafe_allow_html=True)
    
    # Affichage des options avec badges colorés
    options = {
        "FACTURE EN COMPTE": {"icon": "🧾", "color": PALETTE["gold"]},
        "BDC LEADERPRICE": {"icon": "🏪", "color": PALETTE["petrol"]},
        "BDC SUPERMAKI": {"icon": "🛒", "color": PALETTE["gold"]},
        "BDC ULYS": {"icon": "🏢", "color": PALETTE["petrol"]}
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"{options['FACTURE EN COMPTE']['icon']} Scanner Facture", use_container_width=True):
            st.session_state.document_type = "FACTURE EN COMPTE"
            st.rerun()
        
        if st.button(f"{options['BDC LEADERPRICE']['icon']} BDC Leader Price", use_container_width=True):
            st.session_state.document_type = "BDC LEADERPRICE"
            st.rerun()
    
    with col2:
        if st.button(f"{options['BDC SUPERMAKI']['icon']} BDC Supermaki", use_container_width=True):
            st.session_state.document_type = "BDC SUPERMAKI"
            st.rerun()
        
        if st.button(f"{options['BDC ULYS']['icon']} BDC Ulys", use_container_width=True):
            st.session_state.document_type = "BDC ULYS"
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🚪 Déconnexion"):
        st.session_state.auth = False
        st.session_state.user_nom = ""
        st.rerun()
    
    st.stop()

# ============================================================
# INTERFACE PRINCIPALE PAR TYPE DE DOCUMENT
# ============================================================
# Affichage du type de document sélectionné
doc_icons = {
    "FACTURE EN COMPTE": "🧾",
    "BDC LEADERPRICE": "🏪",
    "BDC SUPERMAKI": "🛒",
    "BDC ULYS": "🏢"
}

st.markdown(f"""
<div class='card'>
    <h3 style='text-align:center'>{doc_icons[st.session_state.document_type]} {st.session_state.document_type}</h3>
</div>
""", unsafe_allow_html=True)

# Zone de téléchargement
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align:center'>📤 Téléchargement du document</h4>", unsafe_allow_html=True)

uploaded = st.file_uploader(
    f"Importez l'image du document ({st.session_state.document_type})", 
    type=["jpg", "jpeg", "png"],
    key=f"{st.session_state.document_type}_uploader"
)

if uploaded and uploaded != st.session_state.uploaded_file:
    st.session_state.uploaded_file = uploaded
    st.session_state.show_results = False
    st.session_state.ocr_result = None

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# TRAITEMENT DU DOCUMENT
# ============================================================
if st.session_state.uploaded_file and not st.session_state.show_results:
    try:
        img = Image.open(st.session_state.uploaded_file)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>Aperçu du document</h4>", unsafe_allow_html=True)
        st.image(img, caption="Aperçu", use_column_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Convertir en bytes
        buf = BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()
        
        # Traitement OCR
        with st.spinner("Traitement OCR en cours..."):
            try:
                # Prétraitement
                cleaned = preprocess_image(img_bytes)
                raw = google_vision_ocr(cleaned)
                raw = clean_text(raw)
                
                # Extraction selon le type de document
                if st.session_state.document_type == "FACTURE EN COMPTE":
                    result = extract_facture(raw)
                elif st.session_state.document_type == "BDC LEADERPRICE":
                    result = extract_leaderprice(raw)
                elif st.session_state.document_type == "BDC SUPERMAKI":
                    result = extract_bdc_supermaki(raw)
                elif st.session_state.document_type == "BDC ULYS":
                    result = extract_bdc_ulys(raw)
                
                result["raw"] = raw
                st.session_state.ocr_result = result
                st.session_state.show_results = True
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Erreur OCR: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Erreur de traitement d'image: {str(e)}")

# ============================================================
# AFFICHAGE DES RÉSULTATS
# ============================================================
elif st.session_state.uploaded_file and st.session_state.show_results and st.session_state.ocr_result:
    result = st.session_state.ocr_result
    
    # Afficher les résultats
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Section informations détectées
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h4>📋 Informations détectées</h4>", unsafe_allow_html=True)
    
    if st.session_state.document_type == "FACTURE EN COMPTE":
        col1, col2 = st.columns(2)
        with col1:
            mois = st.text_input("Mois", value=result.get("mois", ""), key="facture_mois")
            doit = st.text_input("DOIT", value=result.get("doit", ""), key="facture_doit")
            bon_commande = st.text_input("Bon de commande", value=result.get("bon_commande", ""), key="facture_bdc")
        
        with col2:
            adresse = st.text_input("Adresse de livraison", value=result.get("adresse_livraison", ""), key="facture_adresse")
            facture = st.text_input("Numéro de facture", value=result.get("facture_numero", ""), key="facture_num")
    
    else:  # BDC
        col1, col2 = st.columns(2)
        with col1:
            date = st.text_input("Date émission", value=result.get("date", datetime.now().strftime("%d/%m/%Y")), key="bdc_date")
            client = st.text_input("Client", value=result.get("client", ""), key="bdc_client")
        
        with col2:
            numero = st.text_input("Numéro BDC", value=result.get("numero", ""), key="bdc_numero")
            
            if st.session_state.document_type == "BDC SUPERMAKI":
                adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", ""), key="bdc_adresse")
            else:
                adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", "SCORE TALATAMATY"), key="bdc_adresse")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Section articles
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h4>🛒 Articles détectés</h4>", unsafe_allow_html=True)
    
    if st.session_state.document_type == "FACTURE EN COMPTE":
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
                use_container_width=True,
                key="facture_articles"
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
                use_container_width=True,
                key="facture_articles_empty"
            )
    else:
        articles = result.get("articles", [])
        if articles:
            df = pd.DataFrame(articles)
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Désignation": st.column_config.TextColumn("Article (Désignation)", width="large"),
                    "Qté": st.column_config.TextColumn("Qté", width="small")
                },
                use_container_width=True,
                key="bdc_articles"
            )
        else:
            st.warning("Aucun article détecté. Ajoutez-les manuellement.")
            df = pd.DataFrame(columns=["Désignation", "Qté"])
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Désignation": st.column_config.TextColumn("Article (Désignation)"),
                    "Qté": st.column_config.TextColumn("Qté")
                },
                use_container_width=True,
                key="bdc_articles_empty"
            )
    
    # Bouton ajouter ligne
    col_add1, col_add2 = st.columns([3, 1])
    with col_add2:
        if st.button("➕ Ajouter une ligne"):
            if st.session_state.document_type == "FACTURE EN COMPTE":
                new_row = {"article": "", "bouteilles": 0}
            else:
                new_row = {"Désignation": "", "Qté": ""}
            
            if 'edited_df' in locals():
                edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                edited_df = pd.DataFrame([new_row])
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Section OCR brut
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    with st.expander("📄 Voir le texte OCR brut"):
        st.text_area("Texte OCR", value=result.get("raw", ""), height=200, key="ocr_raw")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Section export Google Sheets
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h4>📤 Export vers Google Sheets</h4>", unsafe_allow_html=True)
    
    if st.button("💾 Enregistrer dans Google Sheets", use_container_width=True, key="save_to_sheets"):
        try:
            # Vérifier que user_nom existe
            if not hasattr(st.session_state, 'user_nom') or not st.session_state.user_nom:
                st.error("❌ Erreur de session. Veuillez vous reconnecter.")
            else:
                # Préparer les données pour l'export
                export_data = {}
                
                if st.session_state.document_type == "FACTURE EN COMPTE":
                    export_data = {
                        "mois": mois,
                        "doit": doit,
                        "bon_commande": bon_commande,
                        "adresse_livraison": adresse,
                        "articles": edited_df.to_dict('records')
                    }
                else:
                    export_data = {
                        "client": client,
                        "numero": numero,
                        "date": date,
                        "adresse_livraison": adresse,
                        "articles": edited_df.to_dict('records')
                    }
                
                # Sauvegarder dans Google Sheets
                saved_count, duplicate_count = save_to_google_sheets(
                    st.session_state.document_type,
                    export_data,
                    st.session_state.user_nom
                )
                
                if saved_count > 0:
                    # Mettre à jour les statistiques
                    if st.session_state.document_type == "FACTURE EN COMPTE":
                        st.session_state.invoice_scans += 1
                    else:
                        st.session_state.bdc_scans += 1
                    
                    st.success(f"✅ {saved_count} ligne(s) enregistrée(s) avec succès!")
                    st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                    
                    # Bouton pour effacer et recommencer
                    if st.button("🗑️ Effacer et recommencer", use_container_width=True, type="secondary"):
                        st.session_state.uploaded_file = None
                        st.session_state.show_results = False
                        st.session_state.ocr_result = None
                        st.rerun()
                        
                elif duplicate_count > 0:
                    st.warning("⚠️ Ce document existe déjà dans la base de données.")
                else:
                    st.warning("⚠️ Aucune donnée valide à enregistrer")
                    
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
    
    # Bouton Effacer et recommencer
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Effacer et recommencer", use_container_width=True, type="secondary", key="clear_all"):
        st.session_state.uploaded_file = None
        st.session_state.show_results = False
        st.session_state.ocr_result = None
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# MENU DE NAVIGATION
# ============================================================
st.markdown("---")
col_nav1, col_nav2, col_nav3 = st.columns(3)

with col_nav1:
    if st.button("⬅️ Retour au choix", use_container_width=True):
        st.session_state.document_type = ""
        st.session_state.uploaded_file = None
        st.session_state.ocr_result = None
        st.session_state.show_results = False
        st.rerun()

with col_nav2:
    if st.button("📄 Nouveau scan", use_container_width=True):
        st.session_state.uploaded_file = None
        st.session_state.ocr_result = None
        st.session_state.show_results = False
        st.rerun()

with col_nav3:
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.auth = False
        st.session_state.user_nom = ""
        st.session_state.document_type = ""
        st.session_state.uploaded_file = None
        st.session_state.ocr_result = None
        st.session_state.show_results = False
        st.rerun()

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(f"<p style='text-align:center;color:{PALETTE['muted']};font-size:0.8em'>"
            f"Session: {st.session_state.user_nom} | Factures: {st.session_state.invoice_scans} | BDC: {st.session_state.bdc_scans}</p>", 
            unsafe_allow_html=True)
