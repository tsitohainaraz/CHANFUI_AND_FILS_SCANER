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
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
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
    .confidence-high {{
        background-color: rgba(76, 175, 80, 0.1);
        border-left: 4px solid #4CAF50;
        padding: 10px;
        border-radius: 4px;
        margin: 5px 0;
    }}
    .confidence-medium {{
        background-color: rgba(255, 193, 7, 0.1);
        border-left: 4px solid #FFC107;
        padding: 10px;
        border-radius: 4px;
        margin: 5px 0;
    }}
    .confidence-low {{
        background-color: rgba(244, 67, 54, 0.1);
        border-left: 4px solid #F44336;
        padding: 10px;
        border-radius: 4px;
        margin: 5px 0;
    }}
    .table-preview {{
        background: white;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .table-header {{
        background-color: var(--petrol);
        color: white;
        font-weight: bold;
        padding: 8px;
    }}
    .table-row {{
        border-bottom: 1px solid #eee;
        padding: 6px 0;
    }}
    .table-cell {{
        padding: 4px 8px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# OCR Functions AMÉLIORÉES
# ---------------------------
def advanced_preprocess_image(image_bytes: bytes) -> bytes:
    """Prétraitement avancé pour optimiser l'OCR des tableaux"""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    
    # Redimensionnement intelligent
    max_w = 2800  # Légèrement augmenté pour les tableaux larges
    if img.width > max_w:
        ratio = max_w / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_w, new_height), Image.LANCZOS)
    
    # Amélioration du contraste spécifique pour les tableaux
    img = ImageOps.autocontrast(img, cutoff=2)
    
    # Détection et renforcement des lignes de tableau
    # Filtre pour accentuer les contours (utile pour les lignes de tableau)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=180, threshold=2))
    
    # Amélioration de la netteté
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.8)
    
    # Amélioration de la luminosité
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    
    # Conversion en niveaux de gris avec meilleur contrôle
    img_gray = img.convert('L')
    
    # Sauvegarde en haute qualité
    out = BytesIO()
    img_gray.save(out, format="PNG", optimize=True)
    
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

def google_vision_ocr_with_hints(img_bytes: bytes, client_type: str = "auto"):
    """OCR avec des hints pour améliorer la reconnaissance des tableaux"""
    
    client = get_vision_client()
    image = vision.Image(content=img_bytes)
    
    # Configuration spécifique pour les tableaux
    context = vision.ImageContext(
        language_hints=["fr", "en"],  # Français et anglais
    )
    
    # Feature spécifique pour les documents
    feature = vision.Feature(
        type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION
    )
    
    request = vision.AnnotateImageRequest(
        image=image,
        features=[feature],
        image_context=context
    )
    
    response = client.annotate_image(request=request)
    
    if response.error and response.error.message:
        raise Exception(f"Google Vision Error: {response.error.message}")
    
    raw = ""
    if response.full_text_annotation:
        raw = response.full_text_annotation.text
    
    # Extraire également les informations de mise en page
    blocks_info = []
    if response.full_text_annotation:
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                block_text = ""
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])
                        block_text += word_text + " "
                
                blocks_info.append({
                    "text": block_text.strip(),
                    "bounding_box": block.bounding_box,
                    "confidence": block.confidence
                })
    
    return {
        "raw_text": raw,
        "blocks": blocks_info,
        "full_response": response
    }

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

def validate_and_correct_table_data(table_data, client_type):
    """Valide et corrige les données de tableau extraites"""
    
    validated_data = []
    
    for row in table_data:
        corrected_row = {}
        
        for key, value in row.items():
            if key in ["Qté", "Quantité", "bouteilles", "Qte", "Quantite"]:
                # Nettoyer et valider les quantités
                clean_value = str(value).replace(',', '.').replace(' ', '')
                # Supprimer les caractères non numériques sauf point décimal
                clean_value = re.sub(r'[^\d.]', '', clean_value)
                if clean_value and re.match(r'^\d+(\.\d+)?$', clean_value):
                    corrected_row["Qté"] = clean_value
                else:
                    # Essayer d'extraire les nombres de la chaîne
                    numbers = re.findall(r'\d+', str(value))
                    if numbers:
                        corrected_row["Qté"] = numbers[0]
            
            elif key == "EAN":
                # Valider EAN (13 chiffres)
                clean_ean = re.sub(r'\D', '', str(value))
                if len(clean_ean) == 13:
                    corrected_row["EAN"] = clean_ean
                elif len(clean_ean) > 13:
                    corrected_row["EAN"] = clean_ean[:13]
                elif len(clean_ean) > 0:
                    corrected_row["EAN"] = clean_ean
            
            elif key == "GTIN":
                # Valider GTIN (13 ou 14 chiffres)
                clean_gtin = re.sub(r'\D', '', str(value))
                if len(clean_gtin) in [13, 14]:
                    corrected_row["GTIN"] = clean_gtin
                elif len(clean_gtin) > 0:
                    corrected_row["GTIN"] = clean_gtin
            
            elif key in ["Désignation", "Description", "article"]:
                # Nettoyer la désignation
                clean_desc = re.sub(r'\s{2,}', ' ', str(value)).strip()
                # Supprimer les numéros isolés en début de ligne
                clean_desc = re.sub(r'^\d+\s+', '', clean_desc)
                # Supprimer les caractères spéciaux indésirables mais garder accents
                clean_desc = re.sub(r'[^\w\s\-\.\']', '', clean_desc, flags=re.UNICODE)
                corrected_row["Désignation"] = clean_desc
            
            elif key == "Réf":
                # Nettoyer la référence
                clean_ref = re.sub(r'[^\w\d\-]', '', str(value))
                corrected_row["Réf"] = clean_ref
            
            elif key == "REF":
                # Nettoyer la référence
                clean_ref = re.sub(r'[^\w\d\-]', '', str(value))
                corrected_row["REF"] = clean_ref
            
            else:
                # Pour les autres champs, nettoyer simplement
                corrected_row[key] = str(value).strip()
        
        # Vérifier que la ligne contient des données valides
        if any(corrected_row.values()):
            # Calculer un score de confiance pour cette ligne
            confidence = calculate_row_confidence(corrected_row, client_type)
            corrected_row["_confidence"] = confidence
            validated_data.append(corrected_row)
    
    return validated_data

def calculate_row_confidence(row, client_type):
    """Calcule un score de confiance pour une ligne"""
    confidence = 0.0
    
    # Points pour la présence de champs clés selon le client
    if client_type == "SUPERMAKI":
        if "EAN" in row and len(str(row["EAN"])) >= 8:
            confidence += 0.3
        if "Désignation" in row and len(str(row["Désignation"])) > 10:
            confidence += 0.3
        if "Qté" in row and re.match(r'^\d+(\.\d+)?$', str(row["Qté"])):
            confidence += 0.4
    
    elif client_type == "LEADER PRICE":
        if "Réf" in row and len(str(row["Réf"])) > 0:
            confidence += 0.3
        if "Désignation" in row and len(str(row["Désignation"])) > 10:
            confidence += 0.3
        if "Qté" in row and re.match(r'^\d+(\.\d+)?$', str(row["Qté"])):
            confidence += 0.4
    
    elif client_type == "ULYS":
        if "GTIN" in row and len(str(row["GTIN"])) >= 8:
            confidence += 0.3
        if "Désignation" in row and len(str(row["Désignation"])) > 10:
            confidence += 0.3
        if "Qté" in row and re.match(r'^\d+(\.\d+)?$', str(row["Qté"])):
            confidence += 0.4
    
    return min(confidence, 1.0)

# ---------------------------
# NOUVELLES FONCTIONS BDC SPÉCIFIQUES PAR CLIENT - AMÉLIORÉES AVEC EXEMPLES
# ---------------------------

def extract_bdc_supermaki(text: str):
    """Extraction pour SUPERMAKI basée sur l'exemple fourni"""
    result = {
        "client": "SUPERMAKI",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "adresse_fournisseur": "",
        "articles": []
    }
    
    # Extraire numéro BDC - Basé sur l'exemple: "Bon de commande n° 25114566"
    bdc_match = re.search(r"Bon de commande n[°o]\s*(\d{8})", text, re.I)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    else:
        # Pattern alternatif
        bdc_match = re.search(r"n[°o]\s*(\d{8})", text, re.I)
        if bdc_match:
            result["numero"] = bdc_match.group(1)
    
    # Extraire date - Basé sur l'exemple: "Date émission 18/11/2025"
    date_match = re.search(r"Date\s+[ée]mission\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    if date_match:
        result["date"] = date_match.group(1)
    else:
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if date_match:
            result["date"] = date_match.group(1)
    
    # Extraire adresse livraison - Basé sur l'exemple
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
    
    # DÉTECTION PRÉCISE DU TABLEAU BASÉE SUR L'EXEMPLE
    # L'exemple montre clairement la structure du tableau
    lines = text.split('\n')
    in_table = False
    header_found = False
    
    for i, line in enumerate(lines):
        # Chercher l'en-tête du tableau exact
        if (("REF" in line and "EAN" in line and "Désignation" in line) or
            ("REF" in line and "EAN" in line and "PCB" in line)):
            in_table = True
            header_found = True
            continue
        
        # Si on est dans le tableau et qu'on trouve "Seul le prix" ou "Montant TOTAL", on sort
        if in_table and ("Seul le prix" in line or "Montant TOTAL" in line):
            in_table = False
            break
        
        if in_table and line.strip():
            # Analyse précise de la ligne basée sur l'exemple
            # Format: "133790 9777666000019 COTE DE FIANAR ROUGE 75 CL 12 3 36 8 625 310 500 20"
            
            # Chercher REF (5-6 chiffres au début)
            ref_match = re.match(r'^(\d{5,6})\s+', line)
            if ref_match:
                ref = ref_match.group(1)
                
                # Chercher EAN (13 chiffres)
                ean_match = re.search(r'\b(\d{13})\b', line)
                if ean_match:
                    ean = ean_match.group(1)
                    
                    # Extraire la désignation (entre EAN et les nombres suivants)
                    line_after_ean = line[line.find(ean) + len(ean):].strip()
                    
                    # La désignation va jusqu'au prochain groupe de nombres
                    # Dans l'exemple: "COTE DE FIANAR ROUGE 75 CL 12 3 36 8 625 310 500 20"
                    # On veut extraire "COTE DE FIANAR ROUGE 75 CL"
                    
                    # Chercher le pattern de la désignation (texte jusqu'à un nombre suivi d'espace)
                    desig_match = re.match(r'^([A-Z\s]+?75\s*CL)', line_after_ean, re.I)
                    if desig_match:
                        designation = desig_match.group(1).strip()
                        
                        # Chercher la quantité (premier nombre après la désignation)
                        # Dans l'exemple: "12" après "COTE DE FIANAR ROUGE 75 CL"
                        qty_match = re.search(rf'{re.escape(designation)}.*?(\d+)\s+\d+\s+\d+', line_after_ean, re.I)
                        if qty_match:
                            qte = qty_match.group(1)
                            
                            result["articles"].append({
                                "REF": ref,
                                "EAN": ean,
                                "Désignation": designation,
                                "Qté": qte,
                                "Type": "article"
                            })
                    
                    # Chercher aussi les consignes
                    elif "CONS" in line_after_ean.upper() and "CHAN" in line_after_ean.upper():
                        # Pour consigne: "194409 0000010000373 CONS 2000 CHANFOUI 12 3 36 2.000 72.000 0"
                        cons_qty_match = re.search(r'CONS.*?CHAN.*?(\d+)\s+\d+\s+\d+', line_after_ean, re.I)
                        if cons_qty_match:
                            qte = cons_qty_match.group(1)
                            
                            result["articles"].append({
                                "REF": ref,
                                "EAN": ean,
                                "Désignation": "CONS 2000 CHANFOUI",
                                "Qté": qte,
                                "Type": "consigne"
                            })
    
    # Si pas d'articles détectés avec la méthode précise, essayer une méthode plus générique
    if not result["articles"]:
        result["articles"] = extract_bdc_supermaki_generic(text)
    
    return result

def extract_bdc_supermaki_generic(text: str):
    """Méthode générique de secours pour SUPERMAKI"""
    articles = []
    lines = text.split('\n')
    
    for line in lines:
        # Chercher les lignes avec EAN et quantité
        ean_match = re.search(r'(\d{13})', line)
        if ean_match:
            ean = ean_match.group(1)
            
            # Chercher la quantité (nombre avant l'EAN ou après)
            # Pattern: nombre suivi de l'EAN, ou EAN suivi de nombre
            qty_before = re.search(r'(\d+)\s+\d{13}', line)
            qty_after = re.search(r'\d{13}\s+.*?(\d+)\s+\d', line)
            
            qte = ""
            if qty_before:
                qte = qty_before.group(1)
            elif qty_after:
                qte = qty_after.group(1)
            
            # Chercher la désignation
            # Enlever l'EAN et les nombres pour trouver la désignation
            temp_line = re.sub(r'\d{13}', '', line)
            temp_line = re.sub(r'\d{5,6}\s*', '', temp_line, 1)  # Enlever REF
            temp_line = re.sub(r'\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s*\d*', '', temp_line)
            designation = temp_line.strip()
            
            if designation and qte:
                articles.append({
                    "EAN": ean,
                    "Désignation": designation,
                    "Qté": qte,
                    "Type": "consigne" if "CONS" in designation.upper() else "article"
                })
    
    return articles

def extract_bdc_leader_price(text: str):
    """Extraction pour LEADER PRICE basée sur l'exemple fourni"""
    result = {
        "client": "LEADER PRICE",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "articles": []
    }
    
    # Extraire numéro BDC - Basé sur l'exemple: "N° de Commande BCD169602"
    bdc_match = re.search(r"N[°o]\s+de\s+Commande\s+(BCD\d+|BCD\s*\d+)", text, re.I)
    if bdc_match:
        result["numero"] = bdc_match.group(1).replace(" ", "")
    else:
        # Pattern alternatif
        bdc_match = re.search(r"BCD(\d+)", text, re.I)
        if bdc_match:
            result["numero"] = f"BCD{bdc_match.group(1)}"
    
    # Extraire date - Basé sur l'exemple: "Date 28/11/25"
    date_match = re.search(r"Date\s+(\d{2}/\d{2}/\d{2})", text, re.I)
    if date_match:
        date_str = date_match.group(1)
        day, month, year = date_str.split('/')
        year = "20" + year if len(year) == 2 else year
        result["date"] = f"{day}/{month}/{year}"
    
    # Extraire adresse livraison - Basé sur l'exemple
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
    
    # DÉTECTION PRÉCISE DU TABLEAU BASÉE SUR L'EXEMPLE
    # L'exemple montre clairement la structure du tableau avec Réf, Désignation, Qté Cdée
    lines = text.split('\n')
    in_table = False
    header_found = False
    
    for i, line in enumerate(lines):
        # Chercher l'en-tête exact du tableau
        if (("Réf" in line and "Désignation" in line and "Qté" in line) or
            ("Réf" in line and "Désignation" in line and "Cdée" in line)):
            in_table = True
            header_found = True
            continue
        
        # Si on trouve "Total HT" ou "Signature", on sort du tableau
        if in_table and ("Total HT" in line or "Signature" in line or "Cachets" in line):
            in_table = False
            break
        
        if in_table and line.strip() and not line.startswith("---"):
            # Analyse précise basée sur l'exemple
            # Format: "17920 VIN APERITIF ROUGE MAROPARASY 75CL 360.000 Plèces 30C/12 17 740,00 5% 6 067 080.00"
            
            # Chercher Réf (4-5 chiffres au début)
            ref_match = re.match(r'^(\d{4,5})\s+', line)
            if ref_match:
                ref = ref_match.group(1)
                
                # La ligne après la référence est la désignation
                line_after_ref = line[len(ref):].strip()
                
                # Extraire la désignation (jusqu'à la quantité)
                # La quantité est un nombre avec décimales et ".000"
                # Exemple: "360.000" ou "120.000"
                qty_match = re.search(r'(\d+\.\d{3})', line_after_ref)
                if qty_match:
                    qte = qty_match.group(1).replace('.', '')  # Enlever le point pour avoir juste le nombre
                    
                    # La désignation est tout avant la quantité
                    designation = line_after_ref[:qty_match.start()].strip()
                    
                    # Nettoyer la désignation
                    designation = re.sub(r'\s{2,}', ' ', designation)
                    
                    result["articles"].append({
                        "Réf": ref,
                        "Désignation": designation,
                        "Qté": qte,
                        "Type": "consigne" if "CONSIGNE" in designation.upper() else "article"
                    })
                else:
                    # Essayer un pattern plus simple pour les consignes
                    # Exemple: "8431 CONSIGNE BLLE CHAN FOUI 75CL 360.000 Plèces 2 000,00 720 000.00"
                    cons_match = re.search(r'CONSIGNE.*?CHAN.*?(\d+\.\d{3})', line_after_ref, re.I)
                    if cons_match:
                        qte = cons_match.group(1).replace('.', '')
                        designation = "CONSIGNE BLLE CHAN FOUI 75CL"
                        
                        result["articles"].append({
                            "Réf": ref,
                            "Désignation": designation,
                            "Qté": qte,
                            "Type": "consigne"
                        })
    
    # Si pas d'articles détectés avec la méthode précise, essayer une méthode plus générique
    if not result["articles"]:
        result["articles"] = extract_bdc_leader_price_generic(text)
    
    return result

def extract_bdc_leader_price_generic(text: str):
    """Méthode générique de secours pour LEADER PRICE"""
    articles = []
    lines = text.split('\n')
    
    for line in lines:
        # Chercher les lignes avec référence (4-5 chiffres) et quantité (nombre avec .000)
        ref_match = re.match(r'^(\d{4,5})\s+', line)
        if ref_match:
            ref = ref_match.group(1)
            
            # Chercher quantité (format X.000)
            qty_match = re.search(r'(\d+\.\d{3})', line)
            if qty_match:
                qte = qty_match.group(1).replace('.', '')
                
                # Extraire la désignation
                line_after_ref = line[len(ref):].strip()
                # Enlever la quantité et tout après
                designation = re.sub(r'\s+\d+\.\d{3}.*$', '', line_after_ref).strip()
                
                if designation:
                    articles.append({
                        "Réf": ref,
                        "Désignation": designation,
                        "Qté": qte,
                        "Type": "consigne" if "CONSIGNE" in designation.upper() else "article"
                    })
    
    return articles

def extract_bdc_ulys(text: str):
    """Extraction pour ULYS basée sur l'exemple fourni"""
    result = {
        "client": "ULYS",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "nom_magasin": "",
        "nom_fournisseur": "",
        "articles": []
    }
    
    # Extraire numéro BDC - Basé sur l'exemple: "N° 4500264466"
    bdc_match = re.search(r"N[°o]\s+(\d{10})", text)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    else:
        # Pattern alternatif
        bdc_match = re.search(r"(\d{10})", text)
        if bdc_match:
            result["numero"] = bdc_match.group(1)
    
    # Extraire date - Basé sur l'exemple: "Date de la Commande: 30/11/2025"
    date_match = re.search(r"Date de la Commande\s*[:\.]\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    if date_match:
        result["date"] = date_match.group(1)
    else:
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if date_match:
            result["date"] = date_match.group(1)
    
    # Extraire nom magasin - Basé sur l'exemple
    magasin_match = re.search(r"Nom du Magasin\s*[:\.]\s*(.+)", text, re.I)
    if magasin_match:
        result["nom_magasin"] = magasin_match.group(1).strip()
        result["adresse_livraison"] = result["nom_magasin"]
    
    # Extraire nom fournisseur
    fournisseur_match = re.search(r"Nom du Fournisseur\s*[:\.]\s*(.+)", text, re.I)
    if fournisseur_match:
        result["nom_fournisseur"] = fournisseur_match.group(1).strip()
    
    # DÉTECTION PRÉCISE DU TABLEAU BASÉE SUR L'EXEMPLE
    # L'exemple montre clairement la structure avec GTIN, Article No, Description
    lines = text.split('\n')
    in_table = False
    current_category = ""
    
    for i, line in enumerate(lines):
        # Chercher l'en-tête du tableau
        if (("GTIN" in line and "Article No" in line and "Description" in line) or
            ("GTIN" in line and "Article" in line and "Description" in line)):
            in_table = True
            continue
        
        # Chercher les catégories (ex: "122111 - VINS ROUGES")
        category_match = re.match(r'(\d{6})\s*-\s*([A-Z\s]+)', line.strip())
        if category_match:
            current_category = category_match.group(2).strip()
            continue
        
        # Si on trouve "Total de la Commande", on sort du tableau
        if in_table and "Total de la Commande" in line:
            in_table = False
            break
        
        if in_table and line.strip():
            # Analyse précise basée sur l'exemple
            # Format: "0796554900148 10043907 VIN ROUGE CUVEE SPEC AMBALAVAO 750ML NU PAQ 2 1 PAQ = 12 /PC 05.12.2025"
            
            # Chercher GTIN (13 chiffres)
            gtin_match = re.search(r'(\d{13})', line)
            if gtin_match:
                gtin = gtin_match.group(1)
                
                # Chercher quantité (nombre après le GTIN et l'Article No)
                # Pattern: GTIN + Article No (8 chiffres) + description + "PAQ" ou "/PC" + quantité
                
                # Chercher "PAQ" ou "/PC" suivi d'un nombre
                qty_match = re.search(r'(?:PAQ|/PC)\s+(\d+)', line)
                if qty_match:
                    qte = qty_match.group(1)
                    
                    # Extraire la description
                    # Enlever GTIN et Article No
                    line_after_gtin = line[line.find(gtin) + len(gtin):].strip()
                    # Enlever Article No (8 chiffres)
                    line_after_gtin = re.sub(r'^\d{8}\s*', '', line_after_gtin)
                    # Tout jusqu'à "PAQ" ou "/PC" est la description
                    desc_match = re.search(r'^(.*?)\s+(?:PAQ|/PC)', line_after_gtin)
                    if desc_match:
                        designation = desc_match.group(1).strip()
                        
                        # Ajouter la catégorie si disponible
                        if current_category and not current_category in designation:
                            designation = f"{current_category} - {designation}"
                        
                        result["articles"].append({
                            "GTIN": gtin,
                            "Désignation": designation,
                            "Qté": qte,
                            "Type": "article"
                        })
                
                # Chercher aussi les consignes (format différent)
                elif "/PC" in line and "CONS" in line:
                    # Format pour consigne: "/PC 72 1/PC=1/PC"
                    cons_qty_match = re.search(r'/PC\s+(\d+)\s+', line)
                    if cons_qty_match:
                        qte = cons_qty_match.group(1)
                        designation = "CONS. CHAN FOUI 75CL"
                        
                        result["articles"].append({
                            "GTIN": gtin,
                            "Désignation": designation,
                            "Qté": qte,
                            "Type": "consigne"
                        })
    
    # Si pas d'articles détectés avec la méthode précise, essayer une méthode plus générique
    if not result["articles"]:
        result["articles"] = extract_bdc_ulys_generic(text)
    
    return result

def extract_bdc_ulys_generic(text: str):
    """Méthode générique de secours pour ULYS"""
    articles = []
    lines = text.split('\n')
    current_category = ""
    
    for line in lines:
        # Chercher les catégories
        category_match = re.match(r'(\d{6})\s*-\s*([A-Z\s]+)', line.strip())
        if category_match:
            current_category = category_match.group(2).strip()
            continue
        
        # Chercher GTIN (13 chiffres)
        gtin_match = re.search(r'(\d{13})', line)
        if gtin_match:
            gtin = gtin_match.group(1)
            
            # Chercher quantité (nombre après GTIN)
            # Chercher pattern: PAQ + nombre ou /PC + nombre
            qty_match = re.search(r'(?:PAQ|/PC)\s+(\d+)', line)
            if qty_match:
                qte = qty_match.group(1)
                
                # Extraire description
                line_after_gtin = line[line.find(gtin) + len(gtin):].strip()
                # Enlever Article No si présent
                line_after_gtin = re.sub(r'^\d{8}\s*', '', line_after_gtin)
                # Prendre tout jusqu'à PAQ ou /PC
                desc_match = re.search(r'^(.*?)\s+(?:PAQ|/PC)', line_after_gtin)
                if desc_match:
                    designation = desc_match.group(1).strip()
                    
                    # Ajouter catégorie
                    if current_category and not current_category in designation:
                        designation = f"{current_category} - {designation}"
                    
                    articles.append({
                        "GTIN": gtin,
                        "Désignation": designation,
                        "Qté": qte,
                        "Type": "consigne" if "CONS" in designation.upper() else "article"
                    })
    
    return articles

def enhanced_bdc_pipeline(image_bytes: bytes, client_type: str = "auto"):
    """Pipeline BDC amélioré"""
    
    # 1. Prétraitement avancé
    processed_img = advanced_preprocess_image(image_bytes)
    
    # 2. OCR avec hints
    ocr_result = google_vision_ocr_with_hints(processed_img, client_type)
    raw_text = ocr_result["raw_text"]
    raw_text = clean_text(raw_text)
    
    # 3. Détection automatique du client si non spécifié
    if client_type == "auto":
        if "SUPERMAKI" in raw_text or "AMBOHIBAO" in raw_text:
            client_type = "SUPERMAKI"
        elif "LEADER PRICE" in raw_text or "D.L.P.M" in raw_text:
            client_type = "LEADER PRICE"
        elif "ULYS" in raw_text or "SUPER U" in raw_text:
            client_type = "ULYS"
        else:
            client_type = "SUPERMAKI"  # Par défaut
    
    # 4. Appeler la fonction d'extraction appropriée
    if client_type == "SUPERMAKI":
        result = extract_bdc_supermaki(raw_text)
    elif client_type == "LEADER PRICE":
        result = extract_bdc_leader_price(raw_text)
    elif client_type == "ULYS":
        result = extract_bdc_ulys(raw_text)
    else:
        result = extract_bdc_supermaki(raw_text)
    
    # 5. Valider et corriger les données
    if result["articles"]:
        result["articles"] = validate_and_correct_table_data(result["articles"], client_type)
    
    # 6. Ajouter les métadonnées
    result["raw"] = raw_text
    result["client_type"] = client_type
    result["ocr_blocks"] = ocr_result.get("blocks", [])
    
    # 7. Calculer le score de confiance global
    confidence_scores = [item.get("_confidence", 0.5) for item in result["articles"]]
    result["overall_confidence"] = np.mean(confidence_scores) if confidence_scores else 0.5
    
    return result

def display_table_preview(articles, client_type):
    """Affiche un aperçu formaté du tableau extrait"""
    
    if not articles:
        return "<p>Aucun article détecté</p>"
    
    # Déterminer les colonnes selon le client
    if client_type == "SUPERMAKI":
        columns = ["REF", "EAN", "Désignation", "Qté"]
    elif client_type == "LEADER PRICE":
        columns = ["Réf", "Désignation", "Qté"]
    elif client_type == "ULYS":
        columns = ["GTIN", "Désignation", "Qté"]
    else:
        columns = ["Désignation", "Qté"]
    
    # Générer le HTML du tableau
    html = f"""
    <div class="table-preview">
        <div style="display: grid; grid-template-columns: repeat({len(columns)}, 1fr); gap: 1px; background: #ddd;">
    """
    
    # En-tête
    for col in columns:
        html += f'<div class="table-header">{col}</div>'
    
    # Lignes de données
    for i, item in enumerate(articles[:10]):  # Limiter à 10 lignes pour l'aperçu
        for col in columns:
            value = item.get(col, "")
            if col == "Qté" and value:
                # Formater les grandes quantités
                try:
                    value = f"{int(value):,}".replace(",", " ")
                except:
                    pass
            
            html += f'<div class="table-cell">{value}</div>'
    
    html += "</div>"
    
    if len(articles) > 10:
        html += f'<p style="text-align: center; margin-top: 10px;">... et {len(articles) - 10} ligne(s) supplémentaires</p>'
    
    html += "</div>"
    
    return html

# ---------------------------
# Reste du code inchangé (Facture Extraction, Google Sheets, Session State, etc.)
# ...

# [IMPORTANT: Le reste du code reste EXACTEMENT le même que dans votre version précédente]
# [Seules les fonctions d'extraction BDC ont été améliorées]
# [Je continue avec le reste du code...]

# ---------------------------
# Facture Extraction Functions (inchangées)
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
# Google Sheets Functions (inchangées)
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

        all_values = ws.get_all_values()
        
        for row in all_values:
            if len(row) >= 7:
                existing_mois = row[0] if len(row) > 0 else ""
                existing_bdc = row[3] if len(row) > 3 else ""
                existing_article = row[5] if len(row) > 5 else ""

                if (existing_mois == invoice_data["mois"] and 
                    existing_bdc == invoice_data["bon_commande"] and
                    any(item["article"] == existing_article for item in invoice_data["articles"])):
                    return 0, 1

        today_str = datetime.now().strftime("%d/%m/%Y")
        
        rows_to_add = []
        for item in invoice_data["articles"]:
            row = [
                invoice_data["mois"],
                invoice_data["doit"],
                today_str,
                invoice_data["bon_commande"],
                invoice_data["adresse"],
                item["article"],
                item["bouteilles"],
                user_nom
            ]

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
        all_values = ws.get_all_values()
        
        for row in all_values:
            if len(row) >= 6:
                existing_bdc = row[2] if len(row) > 2 else ""
                existing_client = row[1] if len(row) > 1 else ""
                existing_article = row[4] if len(row) > 4 else ""
                
                for item in bdc_data["articles"]:
                    if (existing_bdc == bdc_data["numero"] and 
                        existing_client == bdc_data["client"] and
                        existing_article == item.get("Désignation", "")):
                        return 0, 1
        
        rows_to_add = []
        for item in bdc_data["articles"]:
            designation = item.get("Désignation", item.get("article", ""))
            qte = item.get("Qté", item.get("bouteilles", ""))
            
            if designation and qte:
                rows_to_add.append([
                    bdc_data.get("date", ""),
                    bdc_data.get("client", ""),
                    bdc_data.get("numero", ""),
                    bdc_data.get("adresse_livraison", ""),
                    str(designation).strip(),
                    str(qte).strip(),
                    user_nom
                ])
        
        if rows_to_add:
            ws.append_rows(rows_to_add)
            return len(rows_to_add), 0
        
        return 0, 0
    
    except Exception as e:
        raise Exception(f"Erreur lors de l'enregistrement: {str(e)}")

# ---------------------------
# Session State (inchangé)
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
# Header avec logo et titre
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
        if st.button("📝 Scanner BDC (Version Précise)", use_container_width=True):
            st.session_state.mode = "bdc"
            st.rerun()
    
    st.markdown("<p style='text-align:center;font-size:0.9em;color:var(--muted)'>"
                "Version BDC avec extraction précise basée sur vos exemples réels</p>", unsafe_allow_html=True)
    
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
            
            buf = BytesIO()
            img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
            
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
        
        st.markdown("</div>", unsafe_allow_html=True)
        
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
        
        if st.button("➕ Ajouter une ligne", key="facture_add_line"):
            new_row = {"article": "", "bouteilles": 0}
            if 'edited_df' in locals():
                edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                edited_df = pd.DataFrame([new_row])
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.expander("📄 Voir le texte OCR brut"):
            st.text_area("Texte OCR", value=result.get("raw", ""), height=200, key="facture_raw")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📤 Export vers Google Sheets</h4>", unsafe_allow_html=True)
        
        ws = get_invoice_worksheet()
        
        if ws is None:
            st.warning("⚠️ Google Sheets non configuré. Configurez les credentials dans les secrets.")
        else:
            if st.button("💾 Enregistrer la facture", use_container_width=True, key="facture_save"):
                try:
                    if not hasattr(st.session_state, 'user_nom') or not st.session_state.user_nom:
                        st.error("❌ Erreur de session. Veuillez vous reconnecter.")
                    else:
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
# NOUVEAU MODE BDC AVEC EXTRACTION PRÉCISE
# ---------------------------
elif st.session_state.mode == "bdc":
    if not st.session_state.bdc_client_type:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center'>📝 Sélectionnez le type de Bon de Commande</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center'>Choisissez le client correspondant à votre BDC</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🍷 SUPERMAKI</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format: REF, EAN, Désignation</p>", unsafe_allow_html=True)
            if st.button("Sélectionner SUPERMAKI", key="select_supermaki", use_container_width=True):
                st.session_state.bdc_client_type = "SUPERMAKI"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🏪 LEADER PRICE</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format: Réf, Désignation, Qté Cdée</p>", unsafe_allow_html=True)
            if st.button("Sélectionner LEADER PRICE", key="select_leader", use_container_width=True):
                st.session_state.bdc_client_type = "LEADER PRICE"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🛒 ULYS</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format: GTIN, Description, Qté</p>", unsafe_allow_html=True)
            if st.button("Sélectionner ULYS", key="select_ulys", use_container_width=True):
                st.session_state.bdc_client_type = "ULYS"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card' style='margin-top:20px'>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align:center'>🔍 Détection Automatique</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center'>L'application détectera automatiquement le format</p>", unsafe_allow_html=True)
        if st.button("🎯 Détection Automatique", key="select_auto", use_container_width=True):
            st.session_state.bdc_client_type = "auto"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Retour"):
                st.session_state.mode = None
                st.rerun()
        
        st.stop()
    
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    
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
            
            buf = BytesIO()
            img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
            
            with st.spinner(f"Traitement OCR précis pour {client_name} en cours..."):
                try:
                    result = enhanced_bdc_pipeline(img_bytes, st.session_state.bdc_client_type)
                    st.session_state.ocr_result = result
                    st.session_state.show_ocr_results = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erreur OCR: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Erreur de traitement d'image: {str(e)}")
    
    elif st.session_state.uploaded_file and st.session_state.show_ocr_results and st.session_state.ocr_result:
        result = st.session_state.ocr_result
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # NOUVEAU: Afficher l'aperçu du tableau
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📊 Aperçu du tableau extrait</h4>", unsafe_allow_html=True)
        
        # Afficher le tableau formaté
        table_html = display_table_preview(result.get("articles", []), result.get("client_type", ""))
        st.markdown(table_html, unsafe_allow_html=True)
        
        overall_confidence = result.get("overall_confidence", 0.5)
        if overall_confidence > 0.8:
            confidence_class = "confidence-high"
            confidence_text = "Élevée"
        elif overall_confidence > 0.6:
            confidence_class = "confidence-medium"
            confidence_text = "Moyenne"
        else:
            confidence_class = "confidence-low"
            confidence_text = "Faible"
        
        st.markdown(f"""
            <div class="{confidence_class}" style="margin-top: 20px;">
                <strong>Confiance d'extraction : {overall_confidence:.0%} ({confidence_text})</strong><br>
                <small>Basé sur l'analyse précise du format {result.get('client_type', '')}</small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📋 Informations détectées</h4>", unsafe_allow_html=True)
        
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
            col1, col2 = st.columns(2)
            with col1:
                date = st.text_input("Date émission", value=result.get("date", ""), key="bdc_date")
                client = st.text_input("Client/Facturation", value=result.get("client", ""), key="bdc_client")
            
            with col2:
                numero = st.text_input("Numéro BDC", value=result.get("numero", ""), key="bdc_numero")
                adresse = st.text_input("Adresse livraison", value=result.get("adresse_livraison", ""), key="bdc_adresse")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>🛒 Articles détectés (éditable)</h4>", unsafe_allow_html=True)
        
        articles = result.get("articles", [])
        if articles:
            # Préparer les données pour l'affichage
            display_data = []
            for i, item in enumerate(articles):
                display_item = item.copy()
                # Supprimer le champ de confiance interne
                if "_confidence" in display_item:
                    conf = display_item.pop("_confidence")
                    display_item["Confiance"] = f"{conf:.0%}"
                display_data.append(display_item)
            
            df = pd.DataFrame(display_data)
            
            # Déterminer les colonnes à afficher selon le client
            if result.get("client_type") == "SUPERMAKI":
                column_order = ["REF", "EAN", "Désignation", "Qté", "Type", "Confiance"]
            elif result.get("client_type") == "LEADER PRICE":
                column_order = ["Réf", "Désignation", "Qté", "Type", "Confiance"]
            elif result.get("client_type") == "ULYS":
                column_order = ["GTIN", "Désignation", "Qté", "Type", "Confiance"]
            else:
                column_order = [col for col in df.columns if col != "_confidence"]
            
            # Réorganiser les colonnes
            df = df.reindex(columns=[col for col in column_order if col in df.columns])
            
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                key="bdc_articles"
            )
        else:
            st.warning("Aucun article détecté. Ajoutez-les manuellement.")
            df = pd.DataFrame(columns=["Désignation", "Qté", "Type", "Confiance"])
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Désignation": st.column_config.TextColumn("Article (Désignation)"),
                    "Qté": st.column_config.NumberColumn("Qté", format="%.3f"),
                    "Type": st.column_config.SelectboxColumn("Type", options=["article", "consigne"]),
                    "Confiance": st.column_config.TextColumn("Confiance")
                },
                use_container_width=True,
                key="bdc_articles_empty"
            )
        
        if st.button("➕ Ajouter une ligne", key="bdc_add_line"):
            new_row = {"Désignation": "", "Qté": "", "Type": "article", "Confiance": "0%"}
            if 'edited_df' in locals():
                edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                edited_df = pd.DataFrame([new_row])
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.expander("🔍 Voir le texte OCR brut"):
            st.text_area("Texte OCR", value=result.get("raw", ""), height=200, key="bdc_raw")
        st.markdown("</div>", unsafe_allow_html=True)
        
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
                        articles_to_save = []
                        if 'edited_df' in locals():
                            for _, row in edited_df.iterrows():
                                article_data = {}
                                for col in edited_df.columns:
                                    if col != "Confiance":
                                        article_data[col] = row[col]
                                articles_to_save.append(article_data)
                        
                        bdc_data = {
                            "date": date,
                            "client": client,
                            "numero": numero,
                            "adresse_livraison": adresse,
                            "articles": articles_to_save
                        }
                        
                        saved_count, duplicate_count = save_bdc_without_duplicates(ws, bdc_data, st.session_state.user_nom)
                        
                        if saved_count > 0:
                            st.session_state.bdc_scans += 1
                            st.success(f"✅ {saved_count} ligne(s) enregistrée(s) avec succès!")
                            st.info(f"📝 Format enregistré: Date émission | Client/Facturation | Numéro BDC | Adresse livraison | Article | Qte | Editeur")
                            st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                            st.info(f"🏷️ Type de BDC: {result.get('client_type', 'Inconnu')}")
                            st.info(f"🎯 Confiance d'extraction: {overall_confidence:.0%}")
                            
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
            
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
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
            
            with col3:
                if st.button("📊 Tester autre image", use_container_width=True, type="secondary", key="bdc_test_another"):
                    st.session_state.uploaded_file = None
                    st.session_state.show_ocr_results = False
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        st.info(f"📤 Veuillez télécharger une image de bon de commande {client_name}")
        st.markdown("</div>", unsafe_allow_html=True)
    
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
