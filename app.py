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
# THÈME CHAN FOUI & FILS OPTIMISÉ POUR LISIBILITÉ
# ============================================================
LOGO_FILENAME = "CF_LOGOS.png"
BRAND_TITLE = "CHAN FOUI ET FILS"
BRAND_SUB = "Google Vision AI — Scanner Intelligent"

# Palette de couleurs optimisée pour lisibilité
PALETTE = {
    "primary_dark": "#27414A",    # Bleu foncé élégant
    "primary_light": "#1F2F35",   # Bleu encore plus foncé pour accents
    "background": "#F5F5F3",      # Fond principal très clair
    "card_bg": "#FFFFFF",         # Blanc pur pour les cartes
    "card_bg_alt": "#F4F6F3",     # Variante pour contrastes
    "text_dark": "#1A1A1A",       # Noir pour texte principal (EXTRÊMEMENT LISIBLE)
    "text_medium": "#333333",     # Gris foncé pour texte secondaire
    "accent": "#2C5F73",          # Bleu accent discret
    "success": "#2E7D32",         # Vert succès
    "warning": "#ED6C02",         # Orange attention
    "error": "#D32F2F",           # Rouge erreur
    "border": "#D1D5DB",          # Gris clair pour bordures
    "hover": "#F9FAFB",           # Gris très clair pour hover
}

# CSS personnalisé - DESIGN ULTRA LISIBLE
st.markdown(f"""
<style>
    /* Design général - FOND CLAIR POUR MAXIMUM DE LISIBILITÉ */
    .main {{
        background: {PALETTE['background']};
    }}
    
    .stApp {{
        background: {PALETTE['background']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
    }}
    
    /* Header élégant avec titre en majuscules noires */
    .header-container {{
        background: {PALETTE['card_bg']};
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(39, 65, 74, 0.08);
        text-align: center;
        border: 1px solid {PALETTE['border']};
    }}
    
    .logo-title-wrapper {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.2rem;
        margin-bottom: 0.5rem;
    }}
    
    .logo-img {{
        height: 100px;
        width: auto;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        border-radius: 12px;
        padding: 8px;
        background: {PALETTE['card_bg']};
    }}
    
    .brand-title {{
        color: {PALETTE['text_dark']} !important;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: 1px;
        text-transform: uppercase;
        line-height: 1.2;
    }}
    
    .brand-sub {{
        color: {PALETTE['text_medium']} !important;
        font-size: 1.1rem;
        margin-top: 0.2rem;
        font-weight: 400;
        opacity: 0.9;
    }}
    
    /* Sous-titre document */
    .document-title {{
        background: {PALETTE['primary_dark']};
        color: {PALETTE['card_bg']} !important;
        padding: 1.2rem 2rem;
        border-radius: 16px;
        font-weight: 700;
        font-size: 1.4rem;
        text-align: center;
        margin: 1.5rem 0 2rem 0;
        box-shadow: 0 4px 12px rgba(39, 65, 74, 0.15);
        border: none;
    }}
    
    /* Cartes avec fond blanc pour lisibilité optimale */
    .card {{
        background: {PALETTE['card_bg']};
        padding: 2rem;
        border-radius: 18px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        margin-bottom: 1.8rem;
        border: 1px solid {PALETTE['border']};
        transition: all 0.2s ease;
    }}
    
    .card:hover {{
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }}
    
    .card h4 {{
        color: {PALETTE['text_dark']} !important;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        border-bottom: 2px solid {PALETTE['accent']};
        padding-bottom: 0.8rem;
    }}
    
    /* ============================================================ */
    /* BOUTONS AVEC TEXTE BLANC - CORRECTION DE LISIBILITÉ */
    /* ============================================================ */
    .stButton > button {{
        background: {PALETTE['primary_dark']};
        color: white !important;
        font-weight: 600;
        border: 1px solid {PALETTE['primary_dark']};
        padding: 0.9rem 1.8rem;
        border-radius: 12px;
        transition: all 0.2s ease;
        width: 100%;
        font-size: 1rem;
    }}
    
    .stButton > button:hover {{
        background: {PALETTE['primary_light']};
        border-color: {PALETTE['primary_light']};
        color: white !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(39, 65, 74, 0.2);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
        color: white !important;
    }}
    
    /* FORCE le texte blanc dans TOUS les éléments des boutons */
    .stButton > button,
    .stButton > button *,
    .stButton > button span,
    .stButton > button div,
    .stButton > button p,
    .stButton > button i,
    .stButton > button em {{
        color: white !important;
        fill: white !important;
    }}
    
    /* S'assurer que le texte reste blanc au survol */
    .stButton > button:hover,
    .stButton > button:hover *,
    .stButton > button:hover span,
    .stButton > button:hover div {{
        color: white !important;
        fill: white !important;
    }}
    
    /* Zone de dépôt */
    .upload-box {{
        border: 2px dashed {PALETTE['accent']};
        border-radius: 18px;
        padding: 3rem;
        text-align: center;
        background: {PALETTE['card_bg']};
        margin: 1.5rem 0;
        transition: all 0.3s ease;
    }}
    
    .upload-box:hover {{
        background: {PALETTE['hover']};
        border-color: {PALETTE['primary_dark']};
    }}
    
    /* Barre de progression */
    .progress-container {{
        background: {PALETTE['primary_dark']};
        color: {PALETTE['card_bg']} !important;
        padding: 2.5rem;
        border-radius: 18px;
        text-align: center;
        margin: 2rem 0;
        box-shadow: 0 4px 20px rgba(39, 65, 74, 0.15);
    }}
    
    /* Sélecteur de document */
    .doc-selector {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.2rem;
        margin: 2rem 0;
    }}
    
    .doc-option {{
        background: {PALETTE['card_bg']};
        color: {PALETTE['text_dark']} !important;
        padding: 1.8rem 1.2rem;
        border-radius: 16px;
        border: 1px solid {PALETTE['border']};
        transition: all 0.2s ease;
        cursor: pointer;
        text-align: center;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.04);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        min-height: 130px;
    }}
    
    .doc-option:hover {{
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
        border-color: {PALETTE['accent']};
        background: {PALETTE['hover']};
        color: {PALETTE['text_dark']} !important;
    }}
    
    .doc-option.selected {{
        background: {PALETTE['primary_dark']};
        color: {PALETTE['card_bg']} !important;
        border-color: {PALETTE['primary_dark']};
        box-shadow: 0 6px 20px rgba(39, 65, 74, 0.2);
    }}
    
    /* Image preview permanent */
    .image-preview-container {{
        background: {PALETTE['card_bg']};
        border-radius: 18px;
        padding: 1.8rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        margin-bottom: 2rem;
        border: 1px solid {PALETTE['border']};
    }}
    
    /* Alertes avec bon contraste */
    .info-box {{
        background: #E8F4F8;
        border-left: 4px solid {PALETTE['accent']};
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: {PALETTE['text_dark']} !important;
    }}
    
    .success-box {{
        background: #E8F5E9;
        border-left: 4px solid {PALETTE['success']};
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: {PALETTE['text_dark']} !important;
    }}
    
    .warning-box {{
        background: #FFF3E0;
        border-left: 4px solid {PALETTE['warning']};
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Champs de formulaire */
    .stTextInput > div > div > input {{
        border: 1px solid {PALETTE['border']};
        border-radius: 10px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        color: {PALETTE['text_dark']} !important;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: {PALETTE['accent']};
        box-shadow: 0 0 0 2px rgba(44, 95, 115, 0.1);
    }}
    
    /* Labels toujours noirs pour lisibilité */
    label {{
        color: {PALETTE['text_dark']} !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
    }}
    
    /* Textes dans l'application */
    p, span, div {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    .stMarkdown p, .stMarkdown li {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Data Editor */
    .stDataFrame {{
        border: 1px solid {PALETTE['border']};
        border-radius: 12px;
    }}
    
    /* Responsive Design */
    @media (max-width: 768px) {{
        .header-container {{
            padding: 1.5rem;
            margin: 1rem 0.5rem;
        }}
        
        .brand-title {{
            font-size: 2rem;
        }}
        
        .logo-img {{
            height: 80px;
        }}
        
        .brand-sub {{
            font-size: 1rem;
        }}
        
        .document-title {{
            font-size: 1.2rem;
            padding: 1rem 1.5rem;
            margin: 1rem 0.5rem 1.5rem 0.5rem;
        }}
        
        .doc-option {{
            min-height: 110px;
            padding: 1.5rem 1rem;
        }}
        
        .card {{
            padding: 1.5rem;
            margin: 0.5rem;
            border-radius: 16px;
        }}
        
        .upload-box {{
            padding: 2rem;
            margin: 1rem;
        }}
        
        .stButton > button {{
            padding: 0.8rem 1.5rem;
            font-size: 0.95rem;
        }}
        
        .image-preview-container {{
            margin: 1rem 0.5rem;
            padding: 1.5rem;
        }}
    }}
    
    @media (max-width: 480px) {{
        .brand-title {{
            font-size: 1.6rem;
        }}
        
        .logo-img {{
            height: 70px;
        }}
        
        .doc-selector {{
            grid-template-columns: 1fr;
        }}
        
        .doc-option {{
            min-height: 100px;
        }}
        
        .brand-sub {{
            font-size: 0.9rem;
        }}
        
        .card {{
            padding: 1.2rem;
        }}
    }}
    
    /* Styles spécifiques pour les éléments Streamlit */
    .st-bb {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    .css-1d391kg p {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Contraste amélioré pour toutes les sections */
    section.main > div {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Style pour les textes d'erreur/succès */
    .stAlert {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    .st-emotion-cache-1q7spjk p {{
        color: {PALETTE['text_dark']} !important;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================
SHEET_ID = "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"

SHEET_GIDS = {
    "FACTURE EN COMPTE": 16102465,
    "BDC LEADERPRICE": 954728911,
    "BDC S2M": 954728911,  # Changé de SUPERMAKI à S2M
    "BDC ULYS": 954728911
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

def save_to_google_sheets_with_table(document_type: str, data: dict, edited_df: pd.DataFrame):
    try:
        ws = get_worksheet(document_type)
        
        if not ws:
            st.error("❌ Impossible de se connecter à Google Sheets. Vérifiez les credentials.")
            return False, "Erreur de connexion"
        
        new_rows = prepare_rows_for_sheet(document_type, data, edited_df)
        
        if not new_rows:
            st.warning("⚠️ Aucune donnée à enregistrer")
            return False, "Aucune donnée"
        
        st.info("📋 **Aperçu des données à enregistrer:**")
        
        if document_type == "FACTURE EN COMPTE":
            columns = ["Mois", "Client", "Date", "NBC", "NF", "Lien", "Magasin", "Produit", "Quantité"]
        else:
            columns = ["Mois", "Client", "Date émission", "NBC", "Lien", "Magasin", "Produit", "Quantité"]
        
        preview_df = pd.DataFrame(new_rows, columns=columns)
        st.dataframe(preview_df, use_container_width=True)
        
        table_range = find_table_range(ws)
        
        try:
            if ":" in table_range and table_range.count(":") == 1:
                ws.append_rows(new_rows, table_range=table_range)
            else:
                ws.append_rows(new_rows)
            
            st.success(f"✅ {len(new_rows)} ligne(s) enregistrée(s) avec succès dans Google Sheets!")
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={SHEET_GIDS[document_type]}"
            st.markdown(f'<div class="info-box">🔗 <a href="{sheet_url}" target="_blank">Ouvrir Google Sheets</a></div>', unsafe_allow_html=True)
            
            st.balloons()
            return True, f"{len(new_rows)} lignes enregistrées"
            
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement dans le tableau: {str(e)}")
            
            try:
                st.info("🔄 Tentative alternative d'enregistrement...")
                
                all_data = ws.get_all_values()
                
                for row in new_rows:
                    all_data.append(row)
                
                ws.update('A1', all_data)
                
                st.success(f"✅ {len(new_rows)} ligne(s) enregistrée(s) avec méthode alternative!")
                return True, f"{len(new_rows)} lignes enregistrées (méthode alternative)"
                
            except Exception as e2:
                st.error(f"❌ Échec de la méthode alternative: {str(e2)}")
                return False, str(e)
                
    except Exception as e:
        st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
        return False, str(e)

# ============================================================
# SESSION STATE
# ============================================================
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

# ============================================================
# HEADER AVEC LOGO - DESIGN OPTIMISÉ
# ============================================================
st.markdown('<div class="header-container">', unsafe_allow_html=True)

st.markdown('<div class="logo-title-wrapper">', unsafe_allow_html=True)

# Logo
if os.path.exists(LOGO_FILENAME):
    st.image(LOGO_FILENAME, width=120)
else:
    st.markdown("🍷")

# Titre en majuscules et noir (extrêmement lisible)
st.markdown(f'<h1 class="brand-title">{BRAND_TITLE}</h1>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Sous-titre
st.markdown(f'<p class="brand-sub">{BRAND_SUB}</p>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# APERÇU D'IMAGE PERMANENT
# ============================================================
if st.session_state.uploaded_file is not None and st.session_state.uploaded_image is not None:
    st.markdown('<div class="image-preview-container">', unsafe_allow_html=True)
    st.markdown('<h4 style="color: var(--text-dark); text-align: center;">👁️ Aperçu du document</h4>', unsafe_allow_html=True)
    st.image(st.session_state.uploaded_image, use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# SÉLECTION DU TYPE DE DOCUMENT
# ============================================================
if not st.session_state.document_type:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4 style="text-align: center;">📋 Sélectionnez le type de document</h4>', unsafe_allow_html=True)
    
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
    st.stop()

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
    
    # Affichage de l'aperçu
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>👁️ Aperçu du document</h4>', unsafe_allow_html=True)
    
    st.image(st.session_state.uploaded_image, use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
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
    st.markdown('<div class="success-box">', unsafe_allow_html=True)
    st.markdown(f'<h4 style="color: #2E7D32;">✅ Analyse terminée avec succès !</h4>', unsafe_allow_html=True)
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
            st.markdown(f'<div class="info-box"><strong>{total_items}</strong> articles détectés</div>', unsafe_allow_html=True)
        
        with col_stat2:
            st.markdown(f'<div class="info-box"><strong>{total_qty}</strong> unités totales</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bouton d'export Google Sheets
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h4>📤 Export vers Google Sheets</h4>', unsafe_allow_html=True)
    
    if st.button("💾 Enregistrer dans Google Sheets", use_container_width=True, key="save_to_sheets"):
        try:
            success, message = save_to_google_sheets_with_table(
                st.session_state.document_type,
                data_for_sheets,
                edited_df
            )
            
        except Exception as e:
            st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # OCR brut (optionnel)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.expander("🔍 Voir le texte OCR brut"):
        st.text_area("Texte OCR extrait", value=result.get("raw_text", ""), height=200)
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# MENU DE NAVIGATION
# ============================================================
st.markdown("---")
col_nav1, col_nav2 = st.columns([1, 1])

with col_nav1:
    if st.button("⬅️ Changer de type", use_container_width=True, type="secondary"):
        st.session_state.document_type = ""
        st.session_state.uploaded_file = None
        st.session_state.uploaded_image = None
        st.session_state.ocr_result = None
        st.session_state.show_results = False
        st.rerun()

with col_nav2:
    if st.button("🔄 Recommencer", use_container_width=True, type="secondary"):
        st.session_state.uploaded_file = None
        st.session_state.uploaded_image = None
        st.session_state.ocr_result = None
        st.session_state.show_results = False
        st.rerun()

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: {PALETTE['text_medium']}; font-size: 0.9rem; padding: 1.5rem; background: {PALETTE['card_bg']}; border-radius: 12px; margin-top: 2rem; border-top: 1px solid {PALETTE['border']}">
    <p><strong>{BRAND_TITLE}</strong> • Scanner Pro • © {datetime.now().strftime("%Y")}</p>
    <p style="font-size: 0.8rem; margin-top: 0.5rem; opacity: 0.8;">Design optimisé pour la lisibilité • Interface S2M</p>
</div>
""", unsafe_allow_html=True)
