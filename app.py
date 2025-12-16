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
    page_title="Chan Foui & Fils — Scanner Pro",
    page_icon="🍷",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================
# THÈME CHAN FOUI & FILS
# ============================================================
LOGO_FILENAME = "CF_LOGOS.png"
BRAND_TITLE = "Chan Foui et Fils"
BRAND_SUB = "Google Vision AI — Édition Pro"

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
st.markdown(f"""
<style>
    :root {{
        --petrol: {PALETTE['petrol']};
        --gold: {PALETTE['gold']};
        --ivory: {PALETTE['ivory']};
        --muted: {PALETTE['muted']};
        --card: {PALETTE['card']};
        --soft: {PALETTE['soft']};
    }}
    
    .main {{
        background: linear-gradient(180deg, var(--ivory), #fffdf9);
    }}
    
    .stApp {{
        background: var(--ivory);
        color: var(--petrol);
        font-family: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }}
    
    /* Header avec logo */
    .logo-title-container {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        margin-bottom: 10px;
        padding: 1rem;
    }}
    
    .logo-img {{
        height: 80px;
        width: auto;
    }}
    
    .brand-title {{
        color: var(--petrol);
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
    }}
    
    .brand-sub {{
        color: var(--muted);
        text-align: center;
        font-size: 1.1rem;
        margin-top: 0;
        margin-bottom: 2rem;
    }}
    
    /* Cartes */
    .card {{
        border-radius: 14px;
        background: var(--card);
        padding: 1.5rem;
        box-shadow: 0 10px 30px rgba(15, 58, 69, 0.04);
        border: 1px solid rgba(15, 58, 69, 0.03);
        margin-bottom: 1rem;
    }}
    
    /* Boutons */
    .stButton > button {{
        background: linear-gradient(180deg, var(--gold), #b58f2d);
        color: #081214;
        font-weight: 700;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        border: none;
        transition: all 0.3s ease;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(212, 175, 55, 0.3);
    }}
    
    .secondary-button {{
        background: linear-gradient(180deg, #f0f0f0, #d0d0d0) !important;
        color: #333 !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        border: 1px solid #ccc !important;
    }}
    
    /* Sélecteur de document */
    .doc-selector {{
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        justify-content: center;
        margin: 2rem 0;
    }}
    
    .doc-option {{
        flex: 1;
        min-width: 150px;
        text-align: center;
        background: white;
        padding: 1rem;
        border-radius: 12px;
        border: 2px solid transparent;
        transition: all 0.3s ease;
        cursor: pointer;
    }}
    
    .doc-option.selected {{
        border-color: var(--gold);
        background: rgba(212, 175, 55, 0.1);
    }}
    
    .doc-option:hover {{
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }}
    
    /* Zone de téléchargement */
    .upload-box {{
        border: 3px dashed var(--gold);
        border-radius: 20px;
        padding: 3rem;
        text-align: center;
        background: rgba(212, 175, 55, 0.05);
        margin: 2rem 0;
        transition: all 0.3s ease;
    }}
    
    .upload-box:hover {{
        background: rgba(212, 175, 55, 0.1);
        border-color: var(--petrol);
    }}
    
    /* Responsive */
    @media (max-width: 768px) {{
        .brand-title {{
            font-size: 1.8rem;
        }}
        
        .doc-option {{
            min-width: 100%;
        }}
        
        .upload-box {{
            padding: 1.5rem;
        }}
        
        .card {{
            padding: 1rem;
        }}
        
        .logo-title-container {{
            flex-direction: column;
            text-align: center;
            gap: 10px;
        }}
        
        .logo-img {{
            height: 60px;
        }}
    }}
    
    /* Statistiques */
    .stats-card {{
        background: linear-gradient(135deg, var(--petrol) 0%, #0c2d35 100%);
        color: white;
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
    }}
    
    .stats-number {{
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0.5rem 0;
    }}
</style>
""", unsafe_allow_html=True)

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
def preprocess_image(b: bytes, radius=1.2, percent=180) -> bytes:
    img = Image.open(BytesIO(b)).convert("RGB")
    
    # Redimensionnement si trop grand
    max_w = 2600
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def vision_ocr(b: bytes, creds: dict) -> str:
    client = vision.ImageAnnotatorClient(
        credentials=Credentials.from_service_account_info(creds)
    )
    image = vision.Image(content=b)
    res = client.document_text_detection(image=image)
    return res.full_text_annotation.text or ""

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
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

# ============================================================
# HEADER AVEC LOGO
# ============================================================
st.markdown('<div class="logo-title-container">', unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 3])
with col_logo:
    if os.path.exists(LOGO_FILENAME):
        st.image(LOGO_FILENAME, width=100)
    else:
        st.markdown("🍷")

with col_title:
    st.markdown(f'<h1 class="brand-title">{BRAND_TITLE}</h1>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown(f'<p class="brand-sub">{BRAND_SUB}</p>', unsafe_allow_html=True)

# ============================================================
# AUTHENTIFICATION
# ============================================================
if not st.session_state.auth:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; color: var(--petrol);">🔐 Connexion</h3>', unsafe_allow_html=True)
    
    nom = st.text_input("Nom utilisateur (ex: ADMIN)")
    matricule = st.text_input("Code d'accès", type="password")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Se connecter", use_container_width=True):
            if nom and nom.upper() in AUTHORIZED_USERS and AUTHORIZED_USERS[nom.upper()] == matricule:
                st.session_state.auth = True
                st.session_state.user_nom = nom.upper()
                st.rerun()
            else:
                st.error("❌ Nom ou code d'accès invalide")
    
    with col_btn2:
        if st.button("Annuler", use_container_width=True):
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ============================================================
# SÉLECTION DU TYPE DE DOCUMENT
# ============================================================
if not st.session_state.document_type:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; color: var(--petrol);">📋 Sélectionnez le type de document</h3>', unsafe_allow_html=True)
    
    doc_types = ["FACTURE EN COMPTE", "BDC LEADERPRICE", "BDC SUPERMAKI", "BDC ULYS"]
    icons = {"FACTURE EN COMPTE": "🧾", "BDC LEADERPRICE": "🏪", "BDC SUPERMAKI": "🛒", "BDC ULYS": "🏢"}
    
    cols = st.columns(len(doc_types))
    for idx, doc_type in enumerate(doc_types):
        with cols[idx]:
            if st.button(f"{icons[doc_type]}\n\n{doc_type}", use_container_width=True):
                st.session_state.document_type = doc_type
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bouton déconnexion
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.auth = False
        st.session_state.user_nom = ""
        st.session_state.document_type = ""
        st.rerun()
    
    st.stop()

# ============================================================
# INTERFACE PRINCIPALE
# ============================================================
st.markdown(f'<h3 style="text-align: center; color: var(--petrol);">📄 {st.session_state.document_type}</h3>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align: center; color: var(--muted);">Connecté en tant que : {st.session_state.user_nom}</p>', unsafe_allow_html=True)

# Zone de téléchargement
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="upload-box">', unsafe_allow_html=True)

uploaded = st.file_uploader(
    f"**Glissez-déposez votre document {st.session_state.document_type} ici**",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
    help="Formats supportés : JPG, JPEG, PNG"
)

if uploaded:
    st.success("✅ Document importé avec succès !")
    
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# TRAITEMENT DU DOCUMENT
# ============================================================
if uploaded and uploaded != st.session_state.uploaded_file:
    st.session_state.uploaded_file = uploaded
    st.session_state.ocr_result = None
    st.session_state.show_results = False

if st.session_state.uploaded_file and not st.session_state.show_results:
    # Aperçu de l'image
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: var(--petrol);">👁️ Aperçu du document</h4>', unsafe_allow_html=True)
    
    image = Image.open(st.session_state.uploaded_file)
    st.image(image, use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bouton d'analyse
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("🚀 Lancer l'analyse", use_container_width=True):
            with st.spinner("Analyse en cours avec Google Vision AI..."):
                try:
                    # Conversion de l'image
                    buf = BytesIO()
                    image.save(buf, format="JPEG")
                    image_bytes = buf.getvalue()
                    
                    # Prétraitement spécifique
                    if st.session_state.document_type == "FACTURE EN COMPTE":
                        img_processed = preprocess_image(image_bytes, radius=1.1, percent=160)
                    elif st.session_state.document_type == "BDC LEADERPRICE":
                        img_processed = preprocess_image(image_bytes, radius=1.2, percent=170)
                    else:
                        img_processed = preprocess_image(image_bytes, radius=1.2, percent=180)
                    
                    # OCR
                    if "gcp_vision" not in st.secrets:
                        st.error("❌ Credentials Google Vision manquants")
                        st.stop()
                    
                    creds = dict(st.secrets["gcp_vision"])
                    raw_text = vision_ocr(img_processed, creds)
                    raw_text = clean_text(raw_text)
                    
                    # Extraction selon le type de document
                    if st.session_state.document_type == "FACTURE EN COMPTE":
                        result = extract_facture(raw_text)
                    elif st.session_state.document_type == "BDC LEADERPRICE":
                        result = extract_leaderprice(raw_text)
                    elif st.session_state.document_type == "BDC SUPERMAKI":
                        result = extract_bdc_supermaki(raw_text)
                    elif st.session_state.document_type == "BDC ULYS":
                        result = extract_bdc_ulys(raw_text)
                    
                    result["raw_text"] = raw_text
                    st.session_state.ocr_result = result
                    st.session_state.show_results = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
    
    with col_btn2:
        if st.button("🔄 Changer de document", use_container_width=True):
            st.session_state.uploaded_file = None
            st.rerun()

# ============================================================
# AFFICHAGE DES RÉSULTATS
# ============================================================
if st.session_state.show_results and st.session_state.ocr_result:
    result = st.session_state.ocr_result
    
    # Informations extraites
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: var(--petrol);">📋 Informations extraites</h4>', unsafe_allow_html=True)
    
    if st.session_state.document_type == "FACTURE EN COMPTE":
        col1, col2 = st.columns(2)
        with col1:
            mois = st.text_input("Mois", value=result.get("mois", ""))
            doit = st.text_input("DOIT", value=result.get("doit", ""))
            bon_commande = st.text_input("Bon de commande", value=result.get("bon_commande", ""))
        
        with col2:
            adresse = st.text_input("Adresse de livraison", value=result.get("adresse_livraison", ""))
            facture = st.text_input("Numéro de facture", value=result.get("facture_numero", ""))
    
    else:  # BDC
        col1, col2, col3 = st.columns(3)
        with col1:
            client = st.text_input("Client", value=result.get("client", ""))
        with col2:
            numero = st.text_input("Numéro BDC", value=result.get("numero", ""))
        with col3:
            date = st.text_input("Date", value=result.get("date", datetime.now().strftime("%d/%m/%Y")))
        
        if st.session_state.document_type == "BDC SUPERMAKI":
            adresse_livraison = st.text_input("Adresse de livraison", value=result.get("adresse_livraison", ""))
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Articles
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: var(--petrol);">🛒 Articles détectés</h4>', unsafe_allow_html=True)
    
    if st.session_state.document_type == "FACTURE EN COMPTE":
        articles = result.get("articles", [])
        if articles:
            df = pd.DataFrame(articles)
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "article": st.column_config.TextColumn("Article", width="large"),
                    "bouteilles": st.column_config.NumberColumn("Bouteilles", min_value=0)
                },
                use_container_width=True
            )
        else:
            st.warning("Aucun article détecté")
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
    else:
        articles = result.get("articles", [])
        if articles:
            df = pd.DataFrame(articles)
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Désignation": st.column_config.TextColumn("Article", width="large"),
                    "Qté": st.column_config.TextColumn("Quantité")
                },
                use_container_width=True
            )
        else:
            st.warning("Aucun article détecté")
            df = pd.DataFrame(columns=["Désignation", "Qté"])
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Désignation": st.column_config.TextColumn("Article"),
                    "Qté": st.column_config.TextColumn("Quantité")
                },
                use_container_width=True
            )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # OCR brut
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.expander("🔍 Voir le texte OCR brut"):
        st.text_area("Texte OCR", value=result.get("raw_text", ""), height=200)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Export vers Google Sheets
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: var(--petrol);">📤 Export vers Google Sheets</h4>', unsafe_allow_html=True)
    
    if st.button("💾 Enregistrer dans Google Sheets", use_container_width=True):
        try:
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
                    "adresse_livraison": adresse_livraison if st.session_state.document_type == "BDC SUPERMAKI" else "",
                    "articles": edited_df.to_dict('records')
                }
            
            # Sauvegarder dans Google Sheets
            saved_count, duplicate_count = save_to_google_sheets(
                st.session_state.document_type,
                export_data,
                st.session_state.user_nom
            )
            
            if saved_count > 0:
                st.success(f"✅ {saved_count} ligne(s) enregistrée(s) avec succès dans Google Sheets!")
                st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                
                # Bouton pour recommencer
                if st.button("🔄 Scanner un autre document", use_container_width=True):
                    st.session_state.uploaded_file = None
                    st.session_state.ocr_result = None
                    st.session_state.show_results = False
                    st.rerun()
            
            elif duplicate_count > 0:
                st.warning("⚠️ Ce document existe déjà dans la base de données")
            
            else:
                st.error("❌ Aucune donnée valide à enregistrer")
                
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

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
    if st.button("🔄 Nouveau scan", use_container_width=True):
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
st.markdown(f"""
<p style='text-align: center; color: var(--muted); font-size: 0.9rem;'>
    {BRAND_TITLE} • Scanner Pro • {datetime.now().strftime("%Y")}
</p>
""", unsafe_allow_html=True)
