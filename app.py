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
import time
from dateutil import parser
from typing import List, Tuple, Dict, Any
import hashlib

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
# SYSTÈME DE LOGIN
# ============================================================
USERS = {
    "Pathou M": "CF3",
    "Elodie R": "CF2", 
    "Laetitia C": "CF1"
}

# ============================================================
# PALETTE DE COULEURS OPTIMISÉE POUR LISIBILITÉ
# ============================================================
LOGO_FILENAME = "CF_LOGOS.png"
BRAND_TITLE = "CHAN FOUI ET FILS"
BRAND_SUB = "Google Vision AI — Scanner Intelligent"

# Palette inspirée du logo Chan Foui (tons terreux et élégants)
PALETTE = {
    "dark_brown": "#2C1810",      # Marron foncé du logo
    "light_brown": "#8B4513",     # Marron clair
    "gold": "#C9A86A",            # Or élégant
    "cream": "#F8F4E6",           # Crème pour fond
    "white": "#FFFFFF",           # Blanc pur
    "black": "#000000",           # Noir pour textes
    "red_accent": "#B22222",      # Rouge bordeaux discret
    "gray_light": "#F5F5F5",      # Gris très clair
    "gray_dark": "#333333",       # Gris foncé
    "success_green": "#228B22",   # Vert succès
    "warning_orange": "#FF8C00",  # Orange attention
}

# CSS personnalisé OPTIMISÉ POUR LISIBILITÉ
st.markdown(f"""
<style>
    /* Design général - FOND CLAIR POUR MEILLEURE LISIBILITÉ */
    .main {{
        background: {PALETTE['cream']};
    }}
    
    .stApp {{
        background: {PALETTE['cream']};
        font-family: 'Montserrat', 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    
    /* Header élégant avec couleurs du logo */
    .header-container {{
        background: linear-gradient(135deg, {PALETTE['dark_brown']} 0%, {PALETTE['light_brown']} 100%);
        padding: 1.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(44, 24, 16, 0.15);
        text-align: center;
        border: 3px solid {PALETTE['gold']};
    }}
    
    .logo-title-wrapper {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.5rem;
    }}
    
    .logo-img {{
        height: 100px;
        width: auto;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
        background: rgba(255, 255, 255, 0.1);
        padding: 10px;
        border-radius: 12px;
    }}
    
    .brand-title {{
        color: {PALETTE['white']};
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
        letter-spacing: 1px;
    }}
    
    .brand-sub {{
        color: {PALETTE['gold']};
        font-size: 1rem;
        margin-top: 0.2rem;
        font-weight: 500;
        letter-spacing: 0.5px;
    }}
    
    /* Zone login */
    .login-container {{
        background: {PALETTE['white']};
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(44, 24, 16, 0.1);
        margin: 2rem auto;
        max-width: 500px;
        border: 2px solid {PALETTE['gold']};
    }}
    
    .login-title {{
        color: {PALETTE['dark_brown']};
        text-align: center;
        font-size: 1.8rem;
        margin-bottom: 1.5rem;
        font-weight: 700;
    }}
    
    /* Info utilisateur connecté */
    .user-info {{
        background: linear-gradient(135deg, {PALETTE['gold']} 0%, #D4B483 100%);
        color: {PALETTE['dark_brown']};
        padding: 0.8rem 1.5rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1rem;
        text-align: center;
        margin: 0.5rem 0 1.5rem 0;
        box-shadow: 0 4px 12px rgba(201, 168, 106, 0.2);
        border: 2px solid {PALETTE['light_brown']};
    }}
    
    /* Sous-titre document */
    .document-title {{
        background: linear-gradient(135deg, {PALETTE['light_brown']} 0%, #A0522D 100%);
        color: {PALETTE['white']};
        padding: 1rem 2rem;
        border-radius: 15px;
        font-weight: 700;
        font-size: 1.3rem;
        text-align: center;
        margin: 1rem 0 1.5rem 0;
        box-shadow: 0 6px 20px rgba(139, 69, 19, 0.2);
        border: 2px solid {PALETTE['gold']};
    }}
    
    /* Boutons avec couleurs optimisées pour lisibilité */
    .stButton > button {{
        background: linear-gradient(135deg, {PALETTE['light_brown']} 0%, #A0522D 100%);
        color: {PALETTE['white']} !important;
        font-weight: 700;
        border: 2px solid {PALETTE['gold']} !important;
        padding: 0.9rem 1.8rem;
        border-radius: 12px;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 6px 15px rgba(139, 69, 19, 0.2);
        font-size: 1rem;
        min-height: 60px;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(139, 69, 19, 0.3);
        border-color: {PALETTE['white']} !important;
    }}
    
    /* Boutons secondaires */
    .secondary-btn {{
        background: linear-gradient(135deg, {PALETTE['gray_dark']} 0%, #555555 100%) !important;
        border-color: {PALETTE['gray_light']} !important;
    }}
    
    .danger-btn {{
        background: linear-gradient(135deg, {PALETTE['red_accent']} 0%, #8B0000 100%) !important;
        border-color: #FF6B6B !important;
    }}
    
    /* Cartes avec fond blanc pour meilleur contraste */
    .card {{
        background: {PALETTE['white']};
        padding: 1.8rem;
        border-radius: 18px;
        box-shadow: 0 8px 25px rgba(44, 24, 16, 0.08);
        margin-bottom: 1.5rem;
        border: 1px solid rgba(201, 168, 106, 0.3);
    }}
    
    .card h4 {{
        color: {PALETTE['dark_brown']};
        margin-bottom: 1.2rem;
        font-weight: 700;
    }}
    
    /* Zone de dépôt */
    .upload-box {{
        border: 3px dashed {PALETTE['light_brown']};
        border-radius: 18px;
        padding: 2.5rem;
        text-align: center;
        background: rgba(139, 69, 19, 0.05);
        margin: 1.5rem 0;
        transition: all 0.3s ease;
    }}
    
    .upload-box:hover {{
        background: rgba(139, 69, 19, 0.08);
        border-color: {PALETTE['gold']};
    }}
    
    /* Barre de progression */
    .progress-container {{
        background: linear-gradient(135deg, {PALETTE['dark_brown']} 0%, {PALETTE['light_brown']} 100%);
        color: {PALETTE['white']};
        padding: 2rem;
        border-radius: 18px;
        text-align: center;
        margin: 2rem 0;
        box-shadow: 0 8px 25px rgba(44, 24, 16, 0.15);
        border: 2px solid {PALETTE['gold']};
    }}
    
    /* Sélecteur de document */
    .doc-selector {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.2rem;
        margin: 1.5rem 0;
    }}
    
    .doc-option {{
        background: {PALETTE['white']};
        color: {PALETTE['dark_brown']};
        padding: 1.5rem 1rem;
        border-radius: 15px;
        border: 2px solid {PALETTE['gold']};
        transition: all 0.3s ease;
        cursor: pointer;
        text-align: center;
        box-shadow: 0 6px 15px rgba(201, 168, 106, 0.1);
        min-height: 120px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-weight: 600;
    }}
    
    .doc-option:hover {{
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(201, 168, 106, 0.2);
        background: rgba(201, 168, 106, 0.1);
    }}
    
    .doc-option.selected {{
        background: linear-gradient(135deg, {PALETTE['gold']} 0%, #D4B483 100%);
        color: {PALETTE['dark_brown']};
        border-color: {PALETTE['light_brown']};
        box-shadow: 0 8px 20px rgba(201, 168, 106, 0.3);
    }}
    
    /* Image preview permanent */
    .image-preview-container {{
        background: {PALETTE['white']};
        border-radius: 18px;
        padding: 1.5rem;
        box-shadow: 0 8px 25px rgba(44, 24, 16, 0.1);
        margin-bottom: 1.5rem;
        border: 2px solid {PALETTE['gold']};
    }}
    
    /* Alertes avec bon contraste */
    .duplicate-alert {{
        background: linear-gradient(135deg, #FFF3CD 0%, #FFEAA7 100%);
        border: 2px solid {PALETTE['warning_orange']};
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        color: {PALETTE['dark_brown']};
    }}
    
    .success-alert {{
        background: linear-gradient(135deg, #D4EDDA 0%, #C3E6CB 100%);
        border: 2px solid {PALETTE['success_green']};
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        color: {PALETTE['dark_brown']};
    }}
    
    .info-alert {{
        background: linear-gradient(135deg, #D1ECF1 0%, #BEE5EB 100%);
        border: 2px solid {PALETTE['light_brown']};
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        color: {PALETTE['dark_brown']};
    }}
    
    /* Champs de formulaire */
    .stTextInput > div > div > input {{
        border: 2px solid {PALETTE['gold']};
        border-radius: 10px;
        padding: 0.5rem 1rem;
    }}
    
    .stSelectbox > div > div > div {{
        border: 2px solid {PALETTE['gold']};
        border-radius: 10px;
    }}
    
    /* Data Editor */
    .stDataFrame {{
        border: 1px solid {PALETTE['gold']};
        border-radius: 10px;
    }}
    
    /* Responsive Design */
    @media (max-width: 768px) {{
        .header-container {{
            padding: 1.2rem;
            margin: 0.5rem;
        }}
        
        .brand-title {{
            font-size: 1.8rem;
        }}
        
        .logo-img {{
            height: 80px;
        }}
        
        .brand-sub {{
            font-size: 0.9rem;
        }}
        
        .document-title {{
            font-size: 1.1rem;
            padding: 0.8rem 1.2rem;
            margin: 0.8rem 0.5rem 1.2rem 0.5rem;
        }}
        
        .doc-option {{
            min-height: 100px;
            padding: 1.2rem 0.8rem;
            font-size: 0.9rem;
        }}
        
        .card {{
            padding: 1.5rem;
            margin: 0.5rem;
            border-radius: 15px;
        }}
        
        .upload-box {{
            padding: 2rem;
            margin: 1rem;
        }}
        
        .stButton > button {{
            min-height: 55px;
            padding: 0.8rem 1.5rem;
            font-size: 0.95rem;
        }}
        
        .image-preview-container {{
            margin: 1rem 0.5rem;
            padding: 1.2rem;
        }}
        
        .login-container {{
            padding: 1.5rem;
            margin: 1.5rem 0.5rem;
        }}
        
        .login-title {{
            font-size: 1.5rem;
        }}
    }}
    
    @media (max-width: 480px) {{
        .brand-title {{
            font-size: 1.5rem;
        }}
        
        .logo-img {{
            height: 70px;
        }}
        
        .doc-selector {{
            grid-template-columns: 1fr;
        }}
        
        .doc-option {{
            min-height: 90px;
        }}
        
        .brand-sub {{
            font-size: 0.85rem;
        }}
    }}
    
    /* Labels et textes toujours noirs pour meilleure lisibilité */
    label {{
        color: {PALETTE['black']} !important;
        font-weight: 600 !important;
    }}
    
    p, span, div {{
        color: {PALETTE['dark_brown']} !important;
    }}
    
    /* Amélioration de la visibilité du texte dans les boutons */
    .stButton > button span {{
        color: {PALETTE['white']} !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================
SHEET_ID = "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"

SHEET_GIDS = {
    "FACTURE EN COMPTE": 16102465,  # Onglet FACT
    "BDC LEADERPRICE": 954728911,    # Onglet BDC
    "BDC S2M": 954728911,           # Changé de SUPERMAKI à S2M
    "BDC ULYS": 954728911            # Onglet BDC
}

# ============================================================
# FONCTIONS UTILITAIRES (inchangées)
# ============================================================
def preprocess_image(b: bytes, radius=1.2, percent=180) -> bytes:
    img = Image.open(BytesIO(b)).convert("RGB")
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

def format_date_french(date_str: str) -> str:
    try:
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d %m %Y",
            "%d/%m/%y", "%d-%m-%y", "%d %m %y",
            "%d %B %Y", "%d %b %Y"
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except:
                continue
        
        try:
            date_obj = parser.parse(date_str, dayfirst=True)
            return date_obj.strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")

def get_month_from_date(date_str: str) -> str:
    months_fr = {
        1: "janvier", 2: "février", 3: "mars", 4: "avril",
        5: "mai", 6: "juin", 7: "juillet", 8: "août",
        9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
    }
    
    try:
        date_obj = parser.parse(date_str, dayfirst=True)
        return months_fr[date_obj.month]
    except:
        return months_fr[datetime.now().month]

def format_quantity(qty: Any) -> str:
    if qty is None:
        return "0"
    
    qty_str = str(qty)
    qty_str = qty_str.replace(".", ",")
    
    if "," in qty_str:
        parts = qty_str.split(",")
        if len(parts) == 2 and parts[1] == "000":
            qty_str = parts[0]
    
    return qty_str

def map_client(client: str) -> str:
    client_upper = client.upper()
    
    if "ULYS" in client_upper:
        return "ULYS"
    elif "SUPERMAKI" in client_upper or "S2M" in client_upper:
        return "S2M"
    elif "LEADER" in client_upper or "LEADERPRICE" in client_upper:
        return "DLP"
    else:
        return client

# ============================================================
# FONCTIONS D'EXTRACTION (avec modification S2M)
# ============================================================
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
    
    m = re.search(r"le\s+(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    if m:
        date_text = m.group(1)
        result["date"] = date_text
        
        months_fr = {
            "janvier": "janvier", "février": "février", "fevrier": "février",
            "mars": "mars", "avril": "avril", "mai": "mai",
            "juin": "juin", "juillet": "juillet", "août": "août",
            "aout": "août", "septembre": "septembre", "octobre": "octobre",
            "novembre": "novembre", "décembre": "décembre", "decembre": "décembre"
        }
        for month_fr, month_norm in months_fr.items():
            if month_fr in date_text.lower():
                result["mois"] = month_norm
                break
    
    m = re.search(r"FACTURE EN COMPTE\s+N[°o]?\s*(\d+)", text, re.IGNORECASE)
    if m:
        result["facture_numero"] = m.group(1)
    
    m = re.search(r"DOIT\s*:\s*(S2M|ULYS|DLP)", text, re.IGNORECASE)
    if m:
        result["doit"] = m.group(1)
    
    m = re.search(r"Adresse de livraison\s*:\s*(.+)", text, re.IGNORECASE)
    if m:
        result["adresse_livraison"] = m.group(1).strip()
    
    patterns = [
        r"Suivant votre bon de commande\s*[:\-]?\s*([0-9A-Za-z\-\/]+)",
        r"bon de commande\s*[:\-]?\s*(.+)"
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            result["bon_commande"] = m.group(1).strip().split()[0]
            break
    
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

def extract_leaderprice(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {
        "client": "LEADERPRICE",
        "numero": "",
        "date": "",
        "adresse_livraison": "SCORE TALATAMATY",
        "articles": []
    }
    
    m = re.search(r"BCD\d+", text)
    if m:
        result["numero"] = m.group(0)
    
    m = re.search(r"Date\s*(\d{2}/\d{2}/\d{2,4})", text)
    if m:
        date_str = re.sub(r"\s+", "", m.group(1))
        parts = re.split(r"[/\-]", date_str)
        if len(parts) == 3:
            day = parts[0].zfill(2)
            mon = parts[1].zfill(2)
            year = parts[2] if len(parts[2]) == 4 else "20" + parts[2]
            result["date"] = f"{day}/{mon}/{year}"
    
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

def extract_bdc_s2m(text: str):  # Changé le nom de SUPERMAKI à S2M
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {
        "client": "S2M",  # Changé de SUPERMAKI à S2M
        "numero": "",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "adresse_livraison": "",
        "articles": []
    }
    
    m = re.search(r"Bon de commande n[°o]\s*(\d{8})", text)
    if m:
        result["numero"] = m.group(1)
    
    m = re.search(r"Date\s+[ée]mission\s*(\d{2}/\d{2}/\d{4})", text)
    if m:
        result["date"] = m.group(1)
    
    for i, l in enumerate(lines):
        if "Adresse de livraison" in l and i + 1 < len(lines):
            result["adresse_livraison"] = lines[i + 1]
            break
    
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

def extract_bdc_ulys(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {
        "client": "ULYS",
        "numero": "",
        "date": datetime.now().strftime("%d/%m/%Y"),
        "articles": []
    }
    
    m = re.search(r"N[°o]\s*(\d{8,})", text)
    if m:
        result["numero"] = m.group(1)
    
    m = re.search(r"Date de la Commande\s*:?[\s\-]*(\d{2}/\d{2}/\d{4})", text)
    if m:
        result["date"] = m.group(1)
    
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

EXTRACTION_FUNCTIONS = {
    "FACTURE EN COMPTE": extract_facture,
    "BDC LEADERPRICE": extract_leaderprice,
    "BDC S2M": extract_bdc_s2m,  # Changé de BDC SUPERMAKI à BDC S2M
    "BDC ULYS": extract_bdc_ulys
}

# ============================================================
# FONCTION : DÉTECTION DE DOUBLONS
# ============================================================
def check_duplicates_in_sheet(document_type: str, data: dict) -> Tuple[bool, List[Dict], List[str]]:
    """Vérifie si les données existent déjà dans Google Sheets"""
    try:
        if "gcp_sheet" not in st.secrets:
            return False, [], ["Credentials manquants"]
        
        sa_info = dict(st.secrets["gcp_sheet"])
        gc = gspread.service_account_from_dict(sa_info)
        sh = gc.open_by_key(SHEET_ID)
        
        target_gid = SHEET_GIDS.get(document_type)
        worksheet = None
        
        for ws in sh.worksheets():
            if int(ws.id) == target_gid:
                worksheet = ws
                break
        
        if not worksheet:
            return False, [], ["Feuille non trouvée"]
        
        existing_data = worksheet.get_all_values()
        if len(existing_data) <= 1:
            return False, [], []
        
        duplicates = []
        duplicate_messages = []
        
        headers = existing_data[0]
        
        if document_type == "FACTURE EN COMPTE":
            nf_to_find = data.get("facture_numero", "")
            client_to_find = data.get("doit", "")
            
            if not nf_to_find:
                return False, [], ["Numéro de facture manquant"]
            
            for idx, row in enumerate(existing_data[1:], start=2):
                if len(row) >= 5:
                    existing_nf = row[4] if len(row) > 4 else ""
                    existing_client = row[1] if len(row) > 1 else ""
                    
                    if existing_nf == nf_to_find and existing_client == client_to_find:
                        duplicate_info = {
                            "row": idx,
                            "data": row,
                            "reason": f"Facture {nf_to_find} existe déjà pour {client_to_find}"
                        }
                        duplicates.append(duplicate_info)
                        duplicate_messages.append(f"📌 Ligne {idx}: Facture {nf_to_find} pour {client_to_find}")
        
        else:
            nbc_to_find = data.get("numero", "")
            client_to_find = map_client(data.get("client", ""))
            
            if not nbc_to_find:
                return False, [], ["Numéro BDC manquant"]
            
            for idx, row in enumerate(existing_data[1:], start=2):
                if len(row) >= 4:
                    existing_nbc = row[3] if len(row) > 3 else ""
                    existing_client = row[1] if len(row) > 1 else ""
                    
                    if existing_nbc == nbc_to_find and existing_client == client_to_find:
                        duplicate_info = {
                            "row": idx,
                            "data": row,
                            "reason": f"BDC {nbc_to_find} existe déjà pour {client_to_find}"
                        }
                        duplicates.append(duplicate_info)
                        duplicate_messages.append(f"📌 Ligne {idx}: BDC {nbc_to_find} pour {client_to_find}")
        
        has_duplicates = len(duplicates) > 0
        return has_duplicates, duplicates, duplicate_messages
        
    except Exception as e:
        return False, [], [f"Erreur lors de la vérification: {str(e)}"]

# ============================================================
# GOOGLE SHEETS FUNCTIONS
# ============================================================
def get_worksheet(document_type: str):
    try:
        if "gcp_sheet" not in st.secrets:
            st.error("❌ Les credentials Google Sheets ne sont pas configurés dans st.secrets")
            return None
        
        sa_info = dict(st.secrets["gcp_sheet"])
        gc = gspread.service_account_from_dict(sa_info)
        sh = gc.open_by_key(SHEET_ID)
        
        target_gid = SHEET_GIDS.get(document_type)
        
        for worksheet in sh.worksheets():
            if int(worksheet.id) == target_gid:
                return worksheet
        
        st.error(f"❌ La feuille avec GID {target_gid} n'a pas été trouvée")
        return None
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la connexion à Google Sheets: {str(e)}")
        return None

def find_table_range(worksheet):
    try:
        all_data = worksheet.get_all_values()
        
        if not all_data:
            return "A1:I1"
        
        headers = ["Mois", "Client", "date", "NBC", "NF", "lien", "Magasin", "Produit", "Quantite"]
        first_row = all_data[0] if all_data else []
        header_found = any(header in str(first_row) for header in headers)
        
        if header_found:
            last_row = len(all_data) + 1
            if len(all_data) <= 1:
                return "A2:I2"
            else:
                return f"A{last_row}:I{last_row}"
        else:
            for i, row in enumerate(all_data, start=1):
                if not any(cell.strip() for cell in row):
                    return f"A{i}:I{i}"
            return f"A{len(all_data)+1}:I{len(all_data)+1}"
            
    except Exception as e:
        return "A2:I2"

def prepare_rows_for_sheet(document_type: str, data: dict, edited_df: pd.DataFrame) -> List[List[str]]:
    rows = []
    
    try:
        if document_type == "FACTURE EN COMPTE":
            mois = data.get("mois", "")
            client = data.get("doit", "")
            date = format_date_french(data.get("date", ""))
            nbc = data.get("bon_commande", "")
            nf = data.get("facture_numero", "")
            magasin = data.get("adresse_livraison", "")
            
            for _, row in edited_df.iterrows():
                article = str(row.get("article", "")).strip()
                quantite = format_quantity(row.get("bouteilles", ""))
                
                rows.append([
                    mois,
                    client,
                    date,
                    nbc,
                    nf,
                    "",
                    magasin,
                    article,
                    quantite
                ])
        
        else:
            date_emission = data.get("date", "")
            mois = get_month_from_date(date_emission)
            client = map_client(data.get("client", ""))
            date = format_date_french(date_emission)
            nbc = data.get("numero", "")
            magasin = data.get("adresse_livraison", "")
            
            for _, row in edited_df.iterrows():
                article = str(row.get("Désignation", "")).strip()
                quantite = format_quantity(row.get("Qté", ""))
                
                rows.append([
                    mois,
                    client,
                    date,
                    nbc,
                    "",
                    magasin,
                    article,
                    quantite
                ])
        
        return rows
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la préparation des données: {str(e)}")
        return []

def save_to_google_sheets_with_duplicate_check(document_type: str, data: dict, edited_df: pd.DataFrame, overwrite_duplicates: bool = False):
    """Sauvegarde dans Google Sheets avec gestion des doublons"""
    try:
        has_duplicates, duplicates, duplicate_messages = check_duplicates_in_sheet(document_type, data)
        
        if has_duplicates and not overwrite_duplicates:
            return False, "Doublons détectés", duplicates, duplicate_messages
        
        ws = get_worksheet(document_type)
        if not ws:
            return False, "Connexion échouée", [], []
        
        new_rows = prepare_rows_for_sheet(document_type, data, edited_df)
        if not new_rows:
            return False, "Aucune donnée", [], []
        
        if has_duplicates and overwrite_duplicates:
            rows_to_delete = sorted([dup["row"] for dup in duplicates], reverse=True)
            for row_idx in rows_to_delete:
                try:
                    ws.delete_rows(row_idx)
                except:
                    pass
        
        table_range = find_table_range(ws)
        
        try:
            if ":" in table_range and table_range.count(":") == 1:
                ws.append_rows(new_rows, table_range=table_range)
            else:
                ws.append_rows(new_rows)
            
            success_message = f"✅ {len(new_rows)} ligne(s) enregistrée(s) avec succès!"
            if has_duplicates and overwrite_duplicates:
                success_message += f" ({len(duplicates)} doublon(s) écrasé(s))"
            
            return True, success_message, [], []
            
        except Exception as e:
            return False, f"Erreur d'enregistrement: {str(e)}", [], []
                
    except Exception as e:
        return False, f"Erreur générale: {str(e)}", [], []

# ============================================================
# SESSION STATE
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "document_type" not in st.session_state:
    st.session_state.document_type = ""
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = None
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "processing" not in st.session_state:
    st.session_state.processing = False
if "show_duplicate_dialog" not in st.session_state:
    st.session_state.show_duplicate_dialog = False
if "duplicate_data" not in st.session_state:
    st.session_state.duplicate_data = None

# ============================================================
# FONCTION DE LOGIN
# ============================================================
def login():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="login-title">🔐 Connexion</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        name = st.selectbox(
            "Nom",
            options=["", "Pathou M", "Elodie R", "Laetitia C"],
            key="login_name"
        )
    
    with col2:
        code = st.text_input("Code", type="password", key="login_code")
    
    if st.button("🔓 Se connecter", use_container_width=True, key="login_button"):
        if name and code:
            if name in USERS and code == USERS[name]:
                st.session_state.logged_in = True
                st.session_state.current_user = name
                st.success(f"✅ Connecté en tant que {name}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Nom ou code incorrect")
        else:
            st.warning("⚠️ Veuillez remplir tous les champs")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# HEADER AVEC LOGO - SEULEMENT SI CONNECTÉ
# ============================================================
if st.session_state.logged_in:
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="logo-title-wrapper">', unsafe_allow_html=True)
    
    # Logo
    if os.path.exists(LOGO_FILENAME):
        st.image(LOGO_FILENAME, width=120)
    else:
        st.markdown("🍷")
    
    # Titre en majuscules et noir (dans le CSS c'est blanc sur fond foncé)
    st.markdown(f'<h1 class="brand-title">{BRAND_TITLE}</h1>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sous-titre
    st.markdown(f'<p class="brand-sub">{BRAND_SUB}</p>', unsafe_allow_html=True)
    
    # Info utilisateur connecté
    st.markdown(f'<div class="user-info">👤 Connecté en tant que : {st.session_state.current_user}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bouton déconnexion
    if st.button("🚪 Déconnexion", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.current_user = ""
        st.session_state.document_type = ""
        st.session_state.uploaded_file = None
        st.session_state.uploaded_image = None
        st.session_state.ocr_result = None
        st.session_state.show_results = False
        st.rerun()

# ============================================================
# PAGE PRINCIPALE - SEULEMENT SI CONNECTÉ
# ============================================================
if st.session_state.logged_in:
    # ============================================================
    # APERÇU D'IMAGE PERMANENT
    # ============================================================
    if st.session_state.uploaded_file is not None and st.session_state.uploaded_image is not None:
        st.markdown('<div class="image-preview-container">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: var(--dark-brown); text-align: center;">👁️ Aperçu du document</h4>', unsafe_allow_html=True)
        st.image(st.session_state.uploaded_image, use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ============================================================
    # SÉLECTION DU TYPE DE DOCUMENT
    # ============================================================
    if not st.session_state.document_type:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4 style="text-align: center; color: var(--dark-brown);">📋 Sélectionnez le type de document</h4>', unsafe_allow_html=True)
        
        # Options avec S2M au lieu de SUPERMAKI
        doc_types = [
            {"name": "FACTURE EN COMPTE", "icon": "🧾", "desc": "Facture client"},
            {"name": "BDC LEADERPRICE", "icon": "🏪", "desc": "Bon de commande"},
            {"name": "BDC S2M", "icon": "🛒", "desc": "Bon de commande"},  # Changé de SUPERMAKI à S2M
            {"name": "BDC ULYS", "icon": "🏢", "desc": "Bon de commande"}
        ]
        
        st.markdown('<div class="doc-selector">', unsafe_allow_html=True)
        
        cols = st.columns(len(doc_types))
        for idx, doc in enumerate(doc_types):
            with cols[idx]:
                if st.button(
                    f"{doc['icon']}\n\n**{doc['name']}**\n\n_{doc['desc']}_",
                    use_container_width=True,
                    key=f"doc_{idx}"
                ):
                    st.session_state.document_type = doc["name"]
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        # ============================================================
        # SOUS-TITRE DU MODE ACTUEL
        # ============================================================
        doc_icons = {
            "FACTURE EN COMPTE": "🧾",
            "BDC LEADERPRICE": "🏪",
            "BDC S2M": "🛒",  # Changé de SUPERMAKI à S2M
            "BDC ULYS": "🏢"
        }
        
        st.markdown(f'''
        <div class="document-title">
            {doc_icons[st.session_state.document_type]} Mode : {st.session_state.document_type}
        </div>
        ''', unsafe_allow_html=True)
        
        # ============================================================
        # ZONE DE TÉLÉCHARGEMENT
        # ============================================================
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h4>📤 Téléchargement du document</h4>', unsafe_allow_html=True)
        
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            f"**Glissez-déposez votre document {st.session_state.document_type} ici**",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed",
            help="Formats supportés : JPG, JPEG, PNG",
            key="file_uploader"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ============================================================
        # TRAITEMENT AUTOMATIQUE DE L'IMAGE
        # ============================================================
        if uploaded and uploaded != st.session_state.uploaded_file:
            st.session_state.uploaded_file = uploaded
            st.session_state.uploaded_image = Image.open(uploaded)
            st.session_state.ocr_result = None
            st.session_state.show_results = False
            st.session_state.processing = True
            st.session_state.show_duplicate_dialog = False
            
            # Barre de progression
            progress_container = st.empty()
            with progress_container.container():
                st.markdown('<div class="progress-container">', unsafe_allow_html=True)
                st.markdown('<div style="font-size: 2.5rem; margin-bottom: 1rem; animation: pulse 1.5s infinite;">🔍</div>', unsafe_allow_html=True)
                st.markdown('<h3 style="color: white;">Analyse en cours...</h3>', unsafe_allow_html=True)
                st.markdown('<p style="color: rgba(255,255,255,0.9);">Google Vision AI traite votre document</p>', unsafe_allow_html=True)
                
                progress_bar = st.progress(0)
                for percent_complete in range(0, 101, 10):
                    time.sleep(0.1)
                    progress_bar.progress(percent_complete)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Traitement OCR
            try:
                buf = BytesIO()
                st.session_state.uploaded_image.save(buf, format="JPEG")
                image_bytes = buf.getvalue()
                
                # Prétraitement spécifique
                if st.session_state.document_type == "FACTURE EN COMPTE":
                    img_processed = preprocess_image(image_bytes, radius=1.1, percent=160)
                elif st.session_state.document_type == "BDC LEADERPRICE":
                    img_processed = preprocess_image(image_bytes, radius=1.2, percent=170)
                else:
                    img_processed = preprocess_image(image_bytes, radius=1.2, percent=180)
                
                if "gcp_vision" not in st.secrets:
                    st.error("❌ Credentials Google Vision manquants")
                    st.stop()
                
                creds = dict(st.secrets["gcp_vision"])
                raw_text = vision_ocr(img_processed, creds)
                raw_text = clean_text(raw_text)
                
                extract_func = EXTRACTION_FUNCTIONS[st.session_state.document_type]
                result = extract_func(raw_text)
                result["raw_text"] = raw_text
                
                st.session_state.ocr_result = result
                st.session_state.show_results = True
                st.session_state.processing = False
                
                progress_container.empty()
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
                st.session_state.processing = False
        
        # ============================================================
        # AFFICHAGE DES RÉSULTATS
        # ============================================================
        if st.session_state.show_results and st.session_state.ocr_result and not st.session_state.processing:
            result = st.session_state.ocr_result
            
            # Message de succès
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="success-alert">', unsafe_allow_html=True)
            st.markdown(f'<h4 style="color: #228B22;">✅ Analyse terminée avec succès !</h4>', unsafe_allow_html=True)
            st.markdown(f'<p>Document analysé : {st.session_state.document_type} à {datetime.now().strftime("%H:%M:%S")}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Informations extraites
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<h4>📋 Informations extraites</h4>', unsafe_allow_html=True)
            
            if st.session_state.document_type == "FACTURE EN COMPTE":
                col1, col2 = st.columns(2)
                with col1:
                    mois = st.text_input("Mois", value=result.get("mois", ""), key="facture_mois")
                    doit = st.text_input("DOIT", value=result.get("doit", ""), key="facture_doit")
                    bon_commande = st.text_input("Bon de commande", value=result.get("bon_commande", ""), key="facture_bdc")
                
                with col2:
                    adresse = st.text_input("Adresse de livraison", value=result.get("adresse_livraison", ""), key="facture_adresse")
                    facture = st.text_input("Numéro de facture", value=result.get("facture_numero", ""), key="facture_num")
                
                data_for_sheets = {
                    "mois": mois,
                    "doit": doit,
                    "date": result.get("date", ""),
                    "bon_commande": bon_commande,
                    "facture_numero": facture,
                    "adresse_livraison": adresse
                }
            
            else:
                col1, col2 = st.columns(2)
                with col1:
                    date_emission = st.text_input("Date émission", value=result.get("date", datetime.now().strftime("%d/%m/%Y")), key="bdc_date")
                    client = st.text_input("Client", value=result.get("client", ""), key="bdc_client")
                
                with col2:
                    numero = st.text_input("Numéro BDC", value=result.get("numero", ""), key="bdc_numero")
                    
                    if st.session_state.document_type == "BDC S2M":  # Changé de SUPERMAKI à S2M
                        adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", ""), key="bdc_adresse")
                    else:
                        adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", "SCORE TALATAMATY"), key="bdc_adresse")
                
                data_for_sheets = {
                    "client": client,
                    "date": date_emission,
                    "numero": numero,
                    "adresse_livraison": adresse
                }
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Articles détectés
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<h4>🛒 Articles détectés</h4>', unsafe_allow_html=True)
            
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
                        use_container_width=True,
                        key="facture_articles_editor"
                    )
                else:
                    st.warning("⚠️ Aucun article détecté")
                    df = pd.DataFrame(columns=["article", "bouteilles"])
                    edited_df = st.data_editor(
                        df,
                        num_rows="dynamic",
                        column_config={
                            "article": st.column_config.TextColumn("Article"),
                            "bouteilles": st.column_config.NumberColumn("Bouteilles", min_value=0)
                        },
                        use_container_width=True,
                        key="facture_articles_editor_empty"
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
                        use_container_width=True,
                        key="bdc_articles_editor"
                    )
                else:
                    st.warning("⚠️ Aucun article détecté")
                    df = pd.DataFrame(columns=["Désignation", "Qté"])
                    edited_df = st.data_editor(
                        df,
                        num_rows="dynamic",
                        column_config={
                            "Désignation": st.column_config.TextColumn("Article"),
                            "Qté": st.column_config.TextColumn("Quantité")
                        },
                        use_container_width=True,
                        key="bdc_articles_editor_empty"
                    )
            
            # Statistiques
            if articles:
                total_items = len(articles)
                if st.session_state.document_type == "FACTURE EN COMPTE":
                    total_qty = sum(item.get("bouteilles", 0) for item in articles)
                else:
                    total_qty = sum(float(str(item.get("Qté", "0")).split(".")[0]) for item in articles)
                
                col_stat1, col_stat2 = st.columns(2)
                with col_stat1:
                    st.markdown(f'<div class="info-alert"><strong>{total_items}</strong> articles détectés</div>', unsafe_allow_html=True)
                
                with col_stat2:
                    st.markdown(f'<div class="info-alert"><strong>{total_qty}</strong> unités totales</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # ============================================================
            # GESTION DES DOUBLONS
            # ============================================================
            if st.session_state.show_duplicate_dialog and st.session_state.duplicate_data:
                duplicates = st.session_state.duplicate_data.get("duplicates", [])
                duplicate_messages = st.session_state.duplicate_data.get("messages", [])
                
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<div class="duplicate-alert">', unsafe_allow_html=True)
                st.markdown('<h4 style="color: #FF8C00;">⚠️ Doublons détectés !</h4>', unsafe_allow_html=True)
                st.markdown('<p>Les données suivantes existent déjà dans Google Sheets :</p>', unsafe_allow_html=True)
                
                for msg in duplicate_messages:
                    st.markdown(f'<p>• {msg}</p>', unsafe_allow_html=True)
                
                st.markdown('<p><strong>Que souhaitez-vous faire ?</strong></p>', unsafe_allow_html=True)
                
                col_overwrite, col_cancel = st.columns(2)
                
                with col_overwrite:
                    if st.button("✅ Écraser les doublons", use_container_width=True):
                        success, message, _, _ = save_to_google_sheets_with_duplicate_check(
                            st.session_state.document_type,
                            data_for_sheets,
                            edited_df,
                            overwrite_duplicates=True
                        )
                        
                        if success:
                            st.success(message)
                            st.session_state.show_duplicate_dialog = False
                            st.session_state.duplicate_data = None
                            st.balloons()
                        else:
                            st.error(message)
                
                with col_cancel:
                    if st.button("❌ Refuser l'insertion", use_container_width=True):
                        st.warning("❌ Insertion annulée. Les doublons n'ont pas été écrasés.")
                        st.session_state.show_duplicate_dialog = False
                        st.session_state.duplicate_data = None
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            else:
                # Bouton d'export Google Sheets avec vérification de doublons
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown('<h4>📤 Export vers Google Sheets</h4>', unsafe_allow_html=True)
                
                if st.button("💾 Enregistrer dans Google Sheets", use_container_width=True, key="save_to_sheets"):
                    # Vérifier d'abord les doublons
                    has_duplicates, duplicates, duplicate_messages = check_duplicates_in_sheet(
                        st.session_state.document_type,
                        data_for_sheets
                    )
                    
                    if has_duplicates:
                        st.session_state.show_duplicate_dialog = True
                        st.session_state.duplicate_data = {
                            "duplicates": duplicates,
                            "messages": duplicate_messages
                        }
                        st.rerun()
                    else:
                        # Pas de doublons, procéder à l'enregistrement
                        success, message, _, _ = save_to_google_sheets_with_duplicate_check(
                            st.session_state.document_type,
                            data_for_sheets,
                            edited_df,
                            overwrite_duplicates=False
                        )
                        
                        if success:
                            st.success(message)
                            
                            # Afficher le lien vers le sheet
                            sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={SHEET_GIDS[st.session_state.document_type]}"
                            st.markdown(f'<div class="info-alert">🔗 <a href="{sheet_url}" target="_blank">Ouvrir Google Sheets</a></div>', unsafe_allow_html=True)
                            
                            st.balloons()
                        else:
                            st.error(f"❌ Erreur: {message}")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # OCR brut (optionnel)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            with st.expander("🔍 Voir le texte OCR brut"):
                st.text_area("Texte OCR extrait", value=result.get("raw_text", ""), height=200)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # ============================================================
        # MENU DE NAVIGATION
        # ============================================================
        if st.session_state.document_type:
            st.markdown("---")
            col_nav1, col_nav2 = st.columns([1, 1])
            
            with col_nav1:
                if st.button("⬅️ Changer de type", use_container_width=True, type="secondary"):
                    st.session_state.document_type = ""
                    st.session_state.uploaded_file = None
                    st.session_state.uploaded_image = None
                    st.session_state.ocr_result = None
                    st.session_state.show_results = False
                    st.session_state.show_duplicate_dialog = False
                    st.rerun()
            
            with col_nav2:
                if st.button("🔄 Recommencer", use_container_width=True, type="secondary"):
                    st.session_state.uploaded_file = None
                    st.session_state.uploaded_image = None
                    st.session_state.ocr_result = None
                    st.session_state.show_results = False
                    st.session_state.show_duplicate_dialog = False
                    st.rerun()

# ============================================================
# PAGE DE LOGIN - SI NON CONNECTÉ
# ============================================================
else:
    login()

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: {PALETTE['dark_brown']}; font-size: 0.9rem; padding: 1rem; background: rgba(201, 168, 106, 0.1); border-radius: 12px;">
    <p><strong>{BRAND_TITLE}</strong> • Scanner Pro • © {datetime.now().strftime("%Y")}</p>
    <p style="font-size: 0.8rem; opacity: 0.8;">Optimisé pour la lisibilité • Interface professionnelle • S2M</p>
</div>
""", unsafe_allow_html=True)

