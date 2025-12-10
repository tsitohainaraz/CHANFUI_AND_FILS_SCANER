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
import json

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
    "LATITIA": "CFF1",
    "ELODIE": "CFF2",
    "PATHOU": "CFF3",
    "ADMIN": "CFF4"
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
    .client-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }}
    .badge-supermaki {{
        background-color: #FF6B6B;
        color: white;
    }}
    .badge-leader {{
        background-color: #4ECDC4;
        color: white;
    }}
    .badge-ulys {{
        background-color: #45B7D1;
        color: white;
    }}
    .scan-option-card {{
        border: 2px solid transparent;
        transition: all 0.3s ease;
        cursor: pointer;
    }}
    .scan-option-card:hover {{
        border-color: var(--gold);
        transform: translateY(-2px);
    }}
    .scan-option-card.selected {{
        border-color: var(--gold);
        background-color: rgba(212, 175, 55, 0.05);
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
# NOUVELLES FONCTIONS BDC SPÉCIFIQUES PAR CLIENT
# ---------------------------

def extract_bdc_supermaki(text: str):
    """Extraction pour SUPERMAKI"""
    result = {
        "client": "SUPERMAKI",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "adresse_fournisseur": "",
        "articles": []
    }
    
    # Extraire numéro BDC
    bdc_match = re.search(r"Bon de commande n[°o]\s*(\d+)", text, re.I)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    
    # Extraire date
    date_match = re.search(r"Date diffusion\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    if date_match:
        result["date"] = date_match.group(1)
    
    # Extraire adresse livraison
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "adresse de livraison" in line.lower():
            if i + 1 < len(lines):
                result["adresse_livraison"] = lines[i + 1].strip()
                break
    
    # Extraire adresse fournisseur
    for i, line in enumerate(lines):
        if "adresse fournisseur" in line.lower():
            if i + 1 < len(lines):
                result["adresse_fournisseur"] = lines[i + 1].strip()
                break
    
    # Extraire les articles (format spécifique SUPERMAKI)
    table_pattern = r"REF\s+EAN\s+Désignation\s+PGB\s+Nb Colis\s+Quantité\s+PA Unitaire\s+PA Fact\s+TVA"
    lines = text.split('\n')
    in_table = False
    current_article = {}
    
    for line in lines:
        if re.search(table_pattern, line, re.I):
            in_table = True
            continue
        
        if in_table and line.strip() and not line.startswith("---"):
            # Chercher EAN
            ean_match = re.search(r"(\d{13})", line)
            if ean_match:
                ean = ean_match.group(1)
                # Chercher désignation après EAN
                parts = line.split(ean)
                if len(parts) > 1:
                    designation = parts[1].strip()
                    # Chercher quantité
                    qty_match = re.search(r"(\d+)\s+\d+$", line)
                    if qty_match:
                        qte = qty_match.group(1)
                        result["articles"].append({
                            "EAN": ean,
                            "Désignation": designation,
                            "Qté": qte,
                            "Type": "article"
                        })
            # Chercher consigne
            elif "CONS" in line and "CHANFOUI" in line.upper():
                cons_match = re.search(r"(\d+)\s+(\d{3,})", line)
                if cons_match:
                    result["articles"].append({
                        "EAN": "0000010000373",
                        "Désignation": "CONS 2000 CHANFOUI",
                        "Qté": cons_match.group(1),
                        "Type": "consigne"
                    })
    
    return result

def extract_bdc_leader_price(text: str):
    """Extraction pour LEADER PRICE"""
    result = {
        "client": "LEADER PRICE",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "articles": []
    }
    
    # Extraire numéro BDC
    bdc_match = re.search(r"N[°o]\s+de\s+Commande\s+(\S+)", text, re.I)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    
    # Extraire date
    date_match = re.search(r"Date\s+(\d{2}/\d{2}/\d{2})", text, re.I)
    if date_match:
        date_str = date_match.group(1)
        # Convertir format JJ/MM/AA en JJ/MM/AAAA
        day, month, year = date_str.split('/')
        year = "20" + year if len(year) == 2 else year
        result["date"] = f"{day}/{month}/{year}"
    
    # Extraire adresse livraison
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if "a livrer a" in line.lower() or "à livrer à" in line.lower():
            address_lines = []
            for j in range(1, 4):
                if i + j < len(lines) and lines[i + j].strip():
                    address_lines.append(lines[i + j].strip())
            if address_lines:
                result["adresse_livraison"] = " ".join(address_lines)
                break
    
    # Extraire les articles (format spécifique LEADER PRICE)
    lines = text.split('\n')
    in_table = False
    
    for line in lines:
        # Chercher le début du tableau
        if any(x in line.lower() for x in ["réf", "désignation", "qté cdée"]):
            in_table = True
            continue
        
        if in_table and line.strip() and not any(x in line.lower() for x in ["total", "signature", "cachet"]):
            # Format: Réf | Désignation | Qté Cdée | Qté livrée | Condiment | Px unitaire | Rem | Montant HT
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) >= 3:
                ref = parts[0].strip()
                designation = parts[1].strip()
                qte = parts[2].strip().replace(".000", "").replace(",", ".")
                
                # Filtrer les lignes vides ou sans quantité
                if qte and qte != "Plèces" and not qte.endswith(".00"):
                    result["articles"].append({
                        "Réf": ref,
                        "Désignation": designation,
                        "Qté": qte,
                        "Type": "consigne" if "CONSIGNE" in designation.upper() else "article"
                    })
    
    return result

def extract_bdc_ulys(text: str):
    """Extraction pour ULYS"""
    result = {
        "client": "ULYS",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "nom_magasin": "",
        "nom_fournisseur": "",
        "articles": []
    }
    
    # Extraire numéro BDC
    bdc_match = re.search(r"N[°o]\s+(\d{10})", text)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    
    # Extraire date
    date_match = re.search(r"Date de la Commande\s*:\s*(\d{2}\.\d{2}\.\d{4})", text)
    if date_match:
        date_str = date_match.group(1).replace(".", "/")
        result["date"] = date_str
    
    # Extraire nom magasin
    magasin_match = re.search(r"Nom du Magasin\s*:\s*(.+)", text, re.I)
    if magasin_match:
        result["nom_magasin"] = magasin_match.group(1).strip()
        result["adresse_livraison"] = result["nom_magasin"]
    
    # Extraire nom fournisseur
    fournisseur_match = re.search(r"Nom du Fournisseur\s*:\s*(.+)", text, re.I)
    if fournisseur_match:
        result["nom_fournisseur"] = fournisseur_match.group(1).strip()
    
    # Extraire les articles (format spécifique ULYS)
    lines = text.split('\n')
    in_table = False
    
    for i, line in enumerate(lines):
        # Chercher le début du tableau (header avec GTIN, Article No, etc.)
        if "GTIN" in line and "Article No" in line and "Description" in line:
            in_table = True
            continue
        
        if in_table and line.strip() and not any(x in line.lower() for x in ["total", "document", "page"]):
            # Format: GTIN | Article No | Description | Unité | Qté | Conv. Factor | Date Livraison
            # OU Catégorie (122111 - VINS ROUGES)
            
            # Vérifier si c'est une catégorie
            if re.match(r'\d{6}\s*-\s*[A-Z\s]+', line):
                current_category = line.strip()
                continue
            
            # C'est une ligne d'article
            # Chercher GTIN (13 chiffres)
            gtin_match = re.search(r'(\d{13})', line)
            if gtin_match:
                gtin = gtin_match.group(1)
                # Chercher quantité
                qty_match = re.search(r'(\d+)\s+\d+\s*[PAQ/PC]', line)
                if qty_match:
                    qte = qty_match.group(1)
                    # Chercher description
                    # Enlever GTIN, Article No, etc. pour trouver description
                    temp_line = line.replace(gtin, "")
                    # Chercher le prochain nombre (Article No)
                    temp_line = re.sub(r'\d{8}', '', temp_line, 1)
                    # Prendre le texte jusqu'à "PAQ" ou "/PC"
                    desc_match = re.search(r'([A-Z\s]+?)\s+(PAQ|/PC)', temp_line)
                    if desc_match:
                        designation = desc_match.group(1).strip()
                        result["articles"].append({
                            "GTIN": gtin,
                            "Désignation": designation,
                            "Qté": qte,
                            "Unité": desc_match.group(2),
                            "Type": "article"
                        })
    
    return result

def bdc_pipeline(image_bytes: bytes, client_type: str = "auto"):
    """Pipeline BDC principal avec détection automatique ou choix spécifique"""
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)
    
    # Détection automatique du client si non spécifié
    if client_type == "auto":
        if "SUPERMAKI" in raw or "AMBOHIBAO" in raw:
            client_type = "SUPERMAKI"
        elif "LEADER PRICE" in raw or "D.L.P.M" in raw:
            client_type = "LEADER PRICE"
        elif "ULYS" in raw or "SUPER U" in raw:
            client_type = "ULYS"
        else:
            client_type = "SUPERMAKI"  # Par défaut
    
    # Appeler la fonction d'extraction appropriée
    if client_type == "SUPERMAKI":
        result = extract_bdc_supermaki(raw)
    elif client_type == "LEADER PRICE":
        result = extract_bdc_leader_price(raw)
    elif client_type == "ULYS":
        result = extract_bdc_ulys(raw)
    else:
        # Fallback à l'ancienne méthode
        result = extract_bdc_supermaki(raw)
    
    # Ajouter le texte brut OCR
    result["raw"] = raw
    result["client_type"] = client_type
    
    return result

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

def save_invoice_without_duplicates(ws, invoice_data, user_nom):
    try:
        # Fonction pour nettoyer les valeurs NaN / None / inf
        def clean_value(v):
            try:
                if v is None:
                    return ""
                if isinstance(v, float):
                    if np.isnan(v) or np.isinf(v):
                        return ""
                return v
            except:
                return ""

        # Récupérer toutes les données existantes
        all_values = ws.get_all_values()
        
        # Vérifier les doublons (basé sur mois + bon de commande + article)
        for row in all_values:
            if len(row) >= 7:
                existing_mois = row[0] if len(row) > 0 else ""
                existing_bdc = row[3] if len(row) > 3 else ""
                existing_article = row[5] if len(row) > 5 else ""

                if (existing_mois == invoice_data["mois"] and 
                    existing_bdc == invoice_data["bon_commande"] and
                    any(item["article"] == existing_article for item in invoice_data["articles"])):
                    return 0, 1  # doublon

        # Préparer les données - ORDRE POUR FACTURES
        # Mois | Doit | Date | Bon de commande | Adresse de livraison | Article | Bouteille | Editeur
        today_str = datetime.now().strftime("%d/%m/%Y")
        
        rows_to_add = []
        for item in invoice_data["articles"]:
            row = [
                invoice_data["mois"],           # Colonne A: Mois
                invoice_data["doit"],           # Colonne B: Doit
                today_str,                      # Colonne C: Date d'enregistrement
                invoice_data["bon_commande"],   # Colonne D: Bon de commande
                invoice_data["adresse"],        # Colonne E: Adresse de livraison
                item["article"],                # Colonne F: Article
                item["bouteilles"],             # Colonne G: Bouteilles
                user_nom                        # Colonne H: Editeur
            ]

            # Nettoyage pour éviter NaN
            row = [clean_value(x) for x in row]
            rows_to_add.append(row)

        if rows_to_add:
            ws.append_rows(rows_to_add)
            return len(rows_to_add), 0

        return 0, 0

    except Exception as e:
        raise Exception(f"Erreur lors de l'enregistrement: {str(e)}")

def save_bdc_without_duplicates(ws, bdc_data, user_nom):
    try:
        # Récupérer toutes les données existantes
        all_values = ws.get_all_values()
        
        # Vérifier les doublons (basé sur numéro BDC + client + article)
        for row in all_values:
            if len(row) >= 6:
                existing_bdc = row[2] if len(row) > 2 else ""  # Numéro BDC
                existing_client = row[1] if len(row) > 1 else ""  # Client
                existing_article = row[4] if len(row) > 4 else ""  # Article
                
                for item in bdc_data["articles"]:
                    if (existing_bdc == bdc_data["numero"] and 
                        existing_client == bdc_data["client"] and
                        existing_article == item.get("Désignation", "")):
                        return 0, 1  # doublon
        
        # Préparer les données - NOUVEL ORDRE POUR BDC
        # Date émission | Client/Facturation | Numéro BDC | Adresse livraison | Article | Qte | Editeur
        rows_to_add = []
        for item in bdc_data["articles"]:
            # Utiliser Désignation ou Article selon ce qui existe
            designation = item.get("Désignation", item.get("article", ""))
            qte = item.get("Qté", item.get("bouteilles", ""))
            
            if designation and qte:
                rows_to_add.append([
                    bdc_data.get("date", ""),               # Colonne A: Date émission
                    bdc_data.get("client", ""),             # Colonne B: Client/Facturation
                    bdc_data.get("numero", ""),             # Colonne C: Numéro BDC
                    bdc_data.get("adresse_livraison", ""),  # Colonne D: Adresse livraison
                    str(designation).strip(),               # Colonne E: Article (Désignation)
                    str(qte).strip(),                       # Colonne F: Qte
                    user_nom                                # Colonne G: Editeur
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
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "show_ocr_results" not in st.session_state:
    st.session_state.show_ocr_results = False
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = None
if "selected_client_type" not in st.session_state:
    st.session_state.selected_client_type = "auto"
if "bdc_client_type" not in st.session_state:
    st.session_state.bdc_client_type = None

# ---------------------------
# Header avec logo et titre côte à côte
# ---------------------------
col_logo, col_title = st.columns([1, 3])
with col_logo:
    if os.path.exists(LOGO_FILENAME):
        st.image(LOGO_FILENAME, width=100)
    else:
        st.markdown("🍷")

with col_title:
    st.markdown(f"<h1 class='brand-title'>{BRAND_TITLE}</h1>", unsafe_allow_html=True)

st.markdown(f"<p class='brand-sub'>{BRAND_SUB}</p>", unsafe_allow_html=True)

# ---------------------------
# Authentication
# ---------------------------
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
# Facture Mode (inchangé)
# ---------------------------
if st.session_state.mode == "facture":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📄 Scanner une Facture</h3>", unsafe_allow_html=True)
    
    uploaded = st.file_uploader("Téléchargez l'image de la facture", type=["jpg", "jpeg", "png"], 
                                key="facture_uploader")
    
    if uploaded and uploaded != st.session_state.uploaded_file:
        st.session_state.uploaded_file = uploaded
        st.session_state.show_ocr_results = False
        st.session_state.ocr_result = None
    
    if st.session_state.uploaded_file and not st.session_state.show_ocr_results:
        try:
            img = Image.open(st.session_state.uploaded_file)
            st.image(img, caption="Aperçu de la facture", use_column_width=True)
            
            # Convertir en bytes
            buf = BytesIO()
            img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
            
            # Traitement OCR
            with st.spinner("Traitement OCR en cours..."):
                try:
                    result = invoice_pipeline(img_bytes)
                    st.session_state.ocr_result = result
                    st.session_state.show_ocr_results = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erreur OCR: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Erreur de traitement d'image: {str(e)}")
    
    elif st.session_state.uploaded_file and st.session_state.show_ocr_results and st.session_state.ocr_result:
        result = st.session_state.ocr_result
        
        # Afficher les résultats
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section informations détectées
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📋 Informations détectées</h4>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            mois = st.text_input("Mois", value=result.get("mois", ""), key="facture_mois")
            doit = st.text_input("DOIT", value=result.get("doit", ""), key="facture_doit")
            bon_commande = st.text_input("Bon de commande", value=result.get("bon_commande", ""), key="facture_bdc")
        
        with col2:
            adresse = st.text_input("Adresse de livraison", value=result.get("adresse", ""), key="facture_adresse")
            facture = st.text_input("Numéro de facture (pour référence)", value=result.get("facture", ""), key="facture_num")
        
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
        
        # Bouton ajouter ligne
        if st.button("➕ Ajouter une ligne", key="facture_add_line"):
            new_row = {"article": "", "bouteilles": 0}
            if 'edited_df' in locals():
                edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                edited_df = pd.DataFrame([new_row])
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section OCR brut
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.expander("📄 Voir le texte OCR brut"):
            st.text_area("Texte OCR", value=result.get("raw", ""), height=200, key="facture_raw")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section export Google Sheets
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📤 Export vers Google Sheets</h4>", unsafe_allow_html=True)
        
        ws = get_invoice_worksheet()
        
        if ws is None:
            st.warning("⚠️ Google Sheets non configuré. Configurez les credentials dans les secrets.")
        else:
            if st.button("💾 Enregistrer la facture", use_container_width=True, key="facture_save"):
                try:
                    # Vérifier que user_nom existe
                    if not hasattr(st.session_state, 'user_nom') or not st.session_state.user_nom:
                        st.error("❌ Erreur de session. Veuillez vous reconnecter.")
                    else:
                        # Préparer les données avec le nouvel ordre
                        data_to_save = []
                        for _, row in edited_df.iterrows():
                            if str(row["article"]).strip() and str(row["bouteilles"]).strip():
                                data_to_save.append([
                                    mois,
                                    doit,
                                    datetime.now().strftime("%d/%m/%Y"),
                                    bon_commande,
                                    adresse,
                                    str(row["article"]).strip(),
                                    str(row["bouteilles"]).strip(),
                                    st.session_state.user_nom
                                ])
                        
                        if data_to_save:
                            # Enregistrer sans doublons
                            saved_count, duplicate_count = save_invoice_without_duplicates(ws, {
                                "mois": mois,
                                "doit": doit,
                                "bon_commande": bon_commande,
                                "adresse": adresse,
                                "articles": edited_df.to_dict('records')
                            }, st.session_state.user_nom)
                            
                            if saved_count > 0:
                                st.session_state.invoice_scans += 1
                                st.success(f"✅ {saved_count} ligne(s) enregistrée(s) avec succès!")
                                st.info(f"📝 Format enregistré: Mois | Doit | Date | Bon de commande | Adresse | Article | Bouteilles | Editeur")
                                st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                                
                                # Bouton pour effacer et recommencer
                                if st.button("🗑️ Effacer et recommencer", use_container_width=True, type="secondary"):
                                    st.session_state.uploaded_file = None
                                    st.session_state.show_ocr_results = False
                                    st.session_state.ocr_result = None
                                    st.rerun()
                                    
                            elif duplicate_count > 0:
                                st.warning("⚠️ Cette facture existe déjà dans la base de données.")
                            else:
                                st.warning("⚠️ Aucune donnée valide à enregistrer")
                                
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
            
            # Bouton Effacer et recommencer (en dessous)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Effacer et recommencer", use_container_width=True, type="secondary", key="facture_clear_bottom"):
                st.session_state.uploaded_file = None
                st.session_state.show_ocr_results = False
                st.session_state.ocr_result = None
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        st.info("📤 Veuillez télécharger une image de facture")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Boutons de navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Retour"):
            st.session_state.mode = None
            st.session_state.uploaded_file = None
            st.session_state.show_ocr_results = False
            st.session_state.ocr_result = None
            st.rerun()
    
    with col2:
        if st.button("📝 Passer aux BDC"):
            st.session_state.mode = "bdc"
            st.session_state.uploaded_file = None
            st.session_state.show_ocr_results = False
            st.session_state.ocr_result = None
            st.rerun()
    
    with col3:
        if st.button("🚪 Déconnexion"):
            st.session_state.auth = False
            st.session_state.user_nom = ""
            st.session_state.mode = None
            st.session_state.uploaded_file = None
            st.session_state.show_ocr_results = False
            st.session_state.ocr_result = None
            st.rerun()

# ---------------------------
# NOUVEAU MODE BDC AVEC CHOIX DE CLIENT
# ---------------------------
elif st.session_state.mode == "bdc":
    # Section de sélection du type de BDC
    if not st.session_state.bdc_client_type:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center'>📝 Sélectionnez le type de Bon de Commande</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center'>Choisissez le client correspondant à votre BDC</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🍷 SUPERMAKI</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format propre avec tableaux spécifiques</p>", unsafe_allow_html=True)
            if st.button("Sélectionner SUPERMAKI", key="select_supermaki", use_container_width=True):
                st.session_state.bdc_client_type = "SUPERMAKI"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🏪 LEADER PRICE</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format spécifique avec colonnes Réf/Désignation</p>", unsafe_allow_html=True)
            if st.button("Sélectionner LEADER PRICE", key="select_leader", use_container_width=True):
                st.session_state.bdc_client_type = "LEADER PRICE"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🛒 ULYS</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format avec GTIN et catégories</p>", unsafe_allow_html=True)
            if st.button("Sélectionner ULYS", key="select_ulys", use_container_width=True):
                st.session_state.bdc_client_type = "ULYS"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Option détection automatique
        st.markdown("<div class='card' style='margin-top:20px'>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align:center'>🔍 Détection Automatique</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center'>Laissez l'application détecter automatiquement le type de BDC</p>", unsafe_allow_html=True)
        if st.button("🎯 Détection Automatique", key="select_auto", use_container_width=True):
            st.session_state.bdc_client_type = "auto"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Bouton retour
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Retour"):
                st.session_state.mode = None
                st.rerun()
        
        st.stop()
    
    # Section de scan du BDC avec le type sélectionné
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
    # Afficher le badge du client sélectionné
    client_badge_class = ""
    if st.session_state.bdc_client_type == "SUPERMAKI":
        client_badge_class = "badge-supermaki"
        client_name = "SUPERMAKI"
    elif st.session_state.bdc_client_type == "LEADER PRICE":
        client_badge_class = "badge-leader"
        client_name = "LEADER PRICE"
    elif st.session_state.bdc_client_type == "ULYS":
        client_badge_class = "badge-ulys"
        client_name = "ULYS"
    else:
        client_badge_class = "badge-supermaki"
        client_name = "Détection Automatique"
    
    st.markdown(f"""
        <div style='display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 20px;'>
            <h3 style='text-align:center; margin:0'>📝 Scanner un Bon de Commande</h3>
            <span class='client-badge {client_badge_class}'>{client_name}</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Bouton pour changer de type de client
    if st.button("🔄 Changer de type de BDC"):
        st.session_state.bdc_client_type = None
        st.session_state.uploaded_file = None
        st.session_state.show_ocr_results = False
        st.session_state.ocr_result = None
        st.rerun()
    
    uploaded = st.file_uploader(f"Téléchargez l'image du BDC {client_name}", type=["jpg", "jpeg", "png"], 
                                key="bdc_uploader")
    
    if uploaded and uploaded != st.session_state.uploaded_file:
        st.session_state.uploaded_file = uploaded
        st.session_state.show_ocr_results = False
        st.session_state.ocr_result = None
    
    if st.session_state.uploaded_file and not st.session_state.show_ocr_results:
        try:
            img = Image.open(st.session_state.uploaded_file)
            st.image(img, caption=f"Aperçu du BDC {client_name}", use_column_width=True)
            
            # Convertir en bytes
            buf = BytesIO()
            img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
            
            # Traitement OCR avec le type de client sélectionné
            with st.spinner(f"Traitement OCR pour {client_name} en cours..."):
                try:
                    result = bdc_pipeline(img_bytes, st.session_state.bdc_client_type)
                    st.session_state.ocr_result = result
                    st.session_state.show_ocr_results = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erreur OCR: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Erreur de traitement d'image: {str(e)}")
    
    elif st.session_state.uploaded_file and st.session_state.show_ocr_results and st.session_state.ocr_result:
        result = st.session_state.ocr_result
        
        # Afficher les résultats
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section informations détectées
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📋 Informations détectées</h4>", unsafe_allow_html=True)
        
        # Afficher les informations selon le type de client
        if result.get("client_type") == "SUPERMAKI":
            col1, col2 = st.columns(2)
            with col1:
                date = st.text_input("Date diffusion", value=result.get("date", ""), key="bdc_date")
                numero = st.text_input("Numéro BDC", value=result.get("numero", ""), key="bdc_numero")
            
            with col2:
                adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", ""), key="bdc_adresse")
                adresse_fournisseur = st.text_input("Adresse fournisseur", value=result.get("adresse_fournisseur", ""), key="bdc_adresse_four")
            
            client = "SUPERMAKI"
        
        elif result.get("client_type") == "LEADER PRICE":
            col1, col2 = st.columns(2)
            with col1:
                date = st.text_input("Date", value=result.get("date", ""), key="bdc_date")
                numero = st.text_input("Numéro Commande", value=result.get("numero", ""), key="bdc_numero")
            
            with col2:
                adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", ""), key="bdc_adresse")
            
            client = "LEADER PRICE"
        
        elif result.get("client_type") == "ULYS":
            col1, col2 = st.columns(2)
            with col1:
                date = st.text_input("Date de la Commande", value=result.get("date", ""), key="bdc_date")
                numero = st.text_input("N°", value=result.get("numero", ""), key="bdc_numero")
            
            with col2:
                adresse = st.text_input("Nom du Magasin", value=result.get("nom_magasin", ""), key="bdc_adresse")
                nom_fournisseur = st.text_input("Nom Fournisseur", value=result.get("nom_fournisseur", ""), key="bdc_fournisseur")
            
            client = "ULYS"
        
        else:
            # Fallback générique
            col1, col2 = st.columns(2)
            with col1:
                date = st.text_input("Date émission", value=result.get("date", ""), key="bdc_date")
                client = st.text_input("Client/Facturation", value=result.get("client", ""), key="bdc_client")
            
            with col2:
                numero = st.text_input("Numéro BDC", value=result.get("numero", ""), key="bdc_numero")
                adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", ""), key="bdc_adresse")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section articles
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>🛒 Articles détectés</h4>", unsafe_allow_html=True)
        
        articles = result.get("articles", [])
        if articles:
            # Convertir en DataFrame pour l'affichage
            df_data = []
            for item in articles:
                row = {}
                for key, value in item.items():
                    row[key] = value
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # Afficher l'éditeur de données
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                key="bdc_articles"
            )
        else:
            st.warning("Aucun article détecté. Ajoutez-les manuellement.")
            df = pd.DataFrame(columns=["Désignation", "Qté", "Type"])
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Désignation": st.column_config.TextColumn("Article (Désignation)"),
                    "Qté": st.column_config.NumberColumn("Qté", format="%.3f"),
                    "Type": st.column_config.SelectboxColumn("Type", options=["article", "consigne"])
                },
                use_container_width=True,
                key="bdc_articles_empty"
            )
        
        # Bouton ajouter ligne
        if st.button("➕ Ajouter une ligne", key="bdc_add_line"):
            new_row = {"Désignation": "", "Qté": "", "Type": "article"}
            if 'edited_df' in locals():
                edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                edited_df = pd.DataFrame([new_row])
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section OCR brut
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.expander("📄 Voir le texte OCR brut"):
            st.text_area("Texte OCR", value=result.get("raw", ""), height=200, key="bdc_raw")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section export Google Sheets
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📤 Export vers Google Sheets</h4>", unsafe_allow_html=True)
        
        ws = get_bdc_worksheet()
        
        if ws is None:
            st.warning("⚠️ Google Sheets non configuré. Configurez les credentials dans les secrets.")
        else:
            if st.button("💾 Enregistrer dans Google Sheets", use_container_width=True, key="bdc_save"):
                try:
                    if not hasattr(st.session_state, 'user_nom') or not st.session_state.user_nom:
                        st.error("❌ Erreur de session. Veuillez vous reconnecter.")
                    else:
                        # Préparer les données pour l'enregistrement
                        bdc_data = {
                            "date": date,
                            "client": client,
                            "numero": numero,
                            "adresse_livraison": adresse,
                            "articles": edited_df.to_dict('records') if 'edited_df' in locals() else []
                        }
                        
                        # Enregistrer sans doublons
                        saved_count, duplicate_count = save_bdc_without_duplicates(ws, bdc_data, st.session_state.user_nom)
                        
                        if saved_count > 0:
                            st.session_state.bdc_scans += 1
                            st.success(f"✅ {saved_count} ligne(s) enregistrée(s) avec succès!")
                            st.info(f"📝 Format enregistré: Date émission | Client/Facturation | Numéro BDC | Adresse livraison | Article | Qte | Editeur")
                            st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                            st.info(f"🏷️ Type de BDC: {result.get('client_type', 'Inconnu')}")
                            
                            # Bouton pour effacer et recommencer
                            if st.button("🗑️ Effacer et recommencer", use_container_width=True, type="secondary"):
                                st.session_state.uploaded_file = None
                                st.session_state.show_ocr_results = False
                                st.session_state.ocr_result = None
                                st.rerun()
                                
                        elif duplicate_count > 0:
                            st.warning("⚠️ Ce BDC existe déjà dans la base de données.")
                        else:
                            st.warning("⚠️ Aucune donnée valide à enregistrer")
                            
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
            
            # Bouton Effacer et recommencer
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Effacer et recommencer", use_container_width=True, type="secondary", key="bdc_clear_bottom"):
                    st.session_state.uploaded_file = None
                    st.session_state.show_ocr_results = False
                    st.session_state.ocr_result = None
                    st.rerun()
            
            with col2:
                if st.button("🔄 Nouveau type de BDC", use_container_width=True, type="secondary", key="bdc_new_type"):
                    st.session_state.bdc_client_type = None
                    st.session_state.uploaded_file = None
                    st.session_state.show_ocr_results = False
                    st.session_state.ocr_result = None
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        st.info(f"📤 Veuillez télécharger une image de bon de commande {client_name}")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Boutons de navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Retour"):
            st.session_state.mode = None
            st.session_state.bdc_client_type = None
            st.session_state.uploaded_file = None
            st.session_state.show_ocr_results = False
            st.session_state.ocr_result = None
            st.rerun()
    
    with col2:
        if st.button("📄 Passer aux factures"):
            st.session_state.mode = "facture"
            st.session_state.bdc_client_type = None
            st.session_state.uploaded_file = None
            st.session_state.show_ocr_results = False
            st.session_state.ocr_result = None
            st.rerun()
    
    with col3:
        if st.button("🚪 Déconnexion"):
            st.session_state.auth = False
            st.session_state.user_nom = ""
            st.session_state.mode = None
            st.session_state.bdc_client_type = None
            st.session_state.uploaded_file = None
            st.session_state.show_ocr_results = False
            st.session_state.ocr_result = None
            st.rerun()

# ---------------------------
# Footer
# ---------------------------
st.markdown("---")
st.markdown(f"<p style='text-align:center;color:{PALETTE['muted']};font-size:0.8em'>"
            f"Session: {st.session_state.user_nom} | Factures: {st.session_state.invoice_scans} | BDC: {st.session_state.bdc_scans}</p>", 
            unsafe_allow_html=True)
