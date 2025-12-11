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
        overflow-x: auto;
    }}
    .table-header {{
        background-color: var(--petrol);
        color: white;
        font-weight: bold;
        padding: 10px;
        text-align: left;
    }}
    .table-row {{
        border-bottom: 1px solid #eee;
    }}
    .table-row:nth-child(even) {{
        background-color: #f9f9f9;
    }}
    .table-cell {{
        padding: 8px 10px;
        vertical-align: top;
    }}
    .article-count {{
        display: inline-block;
        background: var(--gold);
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin-left: 8px;
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
    max_w = 2800
    if img.width > max_w:
        ratio = max_w / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_w, new_height), Image.LANCZOS)
    
    # Amélioration du contraste
    img = ImageOps.autocontrast(img, cutoff=2)
    
    # Filtre pour accentuer les contours
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=180, threshold=2))
    
    # Amélioration de la netteté
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.8)
    
    # Amélioration de la luminosité
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    
    # Conversion en niveaux de gris
    img_gray = img.convert('L')
    
    # Sauvegarde
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
    """OCR avec des hints pour améliorer la reconnaissance"""
    
    client = get_vision_client()
    image = vision.Image(content=img_bytes)
    
    # Configuration spécifique
    context = vision.ImageContext(
        language_hints=["fr", "en"],
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
    
    # Extraire les informations de mise en page
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

# ---------------------------
# LISTE COMPLÈTE DES ARTICLES POSSIBLES POUR SUPERMAKI
# ---------------------------
SUPERMAKI_ARTICLES_LIST = [
    "Vin rouge Côte de fianar btl 75 CL nu",
    "Vin rouge Côte de fianar btl 37 CL nu",
    "Vin rouge 3l cote de fianar",
    "Vin blanc 3l cote de fianar",
    "Vin Rose 3L COTE DE FIANAR",
    "Vin blanc côte de fianar btl 75 CL nu",
    "Vin rose cote de fianar btl 75 CL nu",
    "Vin Gris côte de fianar btl 75 CL nu",
    "VIN APERITIF ROUGE MAROPARASY 75CL",
    "VIN BLANC DOUX MAROPARASY 75CL",
    "Vin rouge coteau d'amb/vao btl 75 CL",
    "Vin Blanc Ambalavao 750ML NU",
    "Côteau d'Ambalavao Cuvee Spécial Rouge 75 CL",
    "JUS DE RAISIN ROUGE 75CL LP7",
    "JUS DE RAISIN BLANC 75CL LP7",
    "VIN ROUGE COTE DE FIANARA 750 ML NU",
    "VIN ROUGE COTE DE FIANARA 370 ML NU",
    "VIN BLANC COTE DE FIANARA 750 ML NU",
    "VIN ROSE COTE DE FIANARA 750 ML NU",
    "VIN GRIS COTE DE FIANARA 750 ML NU",
    "APERITIF MAROPARASY 75 CL",
    "VIN BLANC DOUX MAROPARASY 750 ML NU",
    "VIN DE MADAGASCAR 75 CL ROUGE",
    "VIN DE MADAGASCAR 75 CL ROSE",
    "Vin rouge cuvee special Ambalavao 750 ML NU",
    "JUS DE RAISIN 70cl",
    "VIN ROUGE DOUX MAROPARASY 750 ML NU",
    "Coteau d'Ambalavao Cuvée special RGE 75 CL",
    "CONS 2000 CHANFOUI"
]

def normalize_designation_supermaki(raw_designation: str) -> str:
    """Normalise une désignation brute en utilisant la liste des articles possibles"""
    raw = raw_designation.upper().strip()
    
    # Correspondances exactes ou partielles
    if "COTE DE FIANAR ROUGE 75" in raw or "COTE DE FIANAR ROUGE 75" in raw:
        return "Vin rouge Côte de fianar btl 75 CL nu"
    elif "COTE DE FIANAR ROUGE 37" in raw or "COTE DE FIANAR ROUGE 370" in raw:
        return "Vin rouge Côte de fianar btl 37 CL nu"
    elif "COTE DE FIANAR ROUGE 3" in raw and ("L" in raw or "LITRE" in raw):
        return "Vin rouge 3l cote de fianar"
    elif "COTE DE FIANAR BLANC 3" in raw and ("L" in raw or "LITRE" in raw):
        return "Vin blanc 3l cote de fianar"
    elif "COTE DE FIANAR ROSE 3" in raw and ("L" in raw or "LITRE" in raw):
        return "Vin Rose 3L COTE DE FIANAR"
    elif "COTE DE FIANAR BLANC 75" in raw:
        return "Vin blanc côte de fianar btl 75 CL nu"
    elif "COTE DE FIANAR ROSE 75" in raw:
        return "Vin rose cote de fianar btl 75 CL nu"
    elif "COTE DE FIANAR GRIS 75" in raw:
        return "Vin Gris côte de fianar btl 75 CL nu"
    elif "MAROPARASY" in raw and "APERITIF" in raw and "ROUGE" in raw:
        return "VIN APERITIF ROUGE MAROPARASY 75CL"
    elif "MAROPARASY" in raw and "BLANC" in raw and "DOUX" in raw:
        return "VIN BLANC DOUX MAROPARASY 75CL"
    elif "COTEAU D'AMB/VAO" in raw or "COTEAU D'AMBALAVAO" in raw:
        if "CUVEE" in raw or "CUVE" in raw or "SPECIAL" in raw:
            return "Côteau d'Ambalavao Cuvee Spécial Rouge 75 CL"
        else:
            return "Vin rouge coteau d'amb/vao btl 75 CL"
    elif "AMBALAVAO" in raw and "BLANC" in raw:
        return "Vin Blanc Ambalavao 750ML NU"
    elif "JUS DE RAISIN ROUGE" in raw:
        return "JUS DE RAISIN ROUGE 75CL LP7"
    elif "JUS DE RAISIN BLANC" in raw:
        return "JUS DE RAISIN BLANC 75CL LP7"
    elif "COTE DE FIANARA ROUGE 750" in raw:
        return "VIN ROUGE COTE DE FIANARA 750 ML NU"
    elif "COTE DE FIANARA ROUGE 370" in raw or "COTE DE FIANARA ROUGE 37" in raw:
        return "VIN ROUGE COTE DE FIANARA 370 ML NU"
    elif "COTE DE FIANARA BLANC 750" in raw:
        return "VIN BLANC COTE DE FIANARA 750 ML NU"
    elif "COTE DE FIANARA ROSE 750" in raw:
        return "VIN ROSE COTE DE FIANARA 750 ML NU"
    elif "COTE DE FIANARA GRIS 750" in raw:
        return "VIN GRIS COTE DE FIANARA 750 ML NU"
    elif "APERITIF MAROPARASY" in raw:
        return "APERITIF MAROPARASY 75 CL"
    elif "VIN BLANC DOUX MAROPARASY 750" in raw:
        return "VIN BLANC DOUX MAROPARASY 750 ML NU"
    elif "VIN DE MADAGASCAR ROUGE" in raw:
        return "VIN DE MADAGASCAR 75 CL ROUGE"
    elif "VIN DE MADAGASCAR ROSE" in raw:
        return "VIN DE MADAGASCAR 75 CL ROSE"
    elif "AMBALAVAO" in raw and "CUVEE" in raw and "SPECIAL" in raw:
        return "Vin rouge cuvee special Ambalavao 750 ML NU"
    elif "JUS DE RAISIN 70" in raw:
        return "JUS DE RAISIN 70cl"
    elif "VIN ROUGE DOUX MAROPARASY" in raw:
        return "VIN ROUGE DOUX MAROPARASY 750 ML NU"
    elif "COTEAU D'AMBALAVAO CUVEE SPECIAL RGE" in raw:
        return "Coteau d'Ambalavao Cuvée special RGE 75 CL"
    elif "CONS 2000" in raw and "CHAN" in raw:
        return "CONS 2000 CHANFOUI"
    
    # Fallback: chercher la meilleure correspondance
    for article in SUPERMAKI_ARTICLES_LIST:
        article_upper = article.upper()
        words_article = set(article_upper.split())
        words_raw = set(raw.split())
        
        # Si au moins 3 mots en commun, c'est probablement une bonne correspondance
        common_words = words_article.intersection(words_raw)
        if len(common_words) >= 3:
            return article
    
    # Si aucune correspondance, retourner l'original nettoyé
    return raw_designation.strip()

# ---------------------------
# FONCTIONS D'EXTRACTION ULTRA-PRÉCISES POUR SUPERMAKI
# ---------------------------

def extract_bdc_supermaki_precise(text: str):
    """Extraction PRÉCISE pour SUPERMAKI avec liste d'articles"""
    result = {
        "client": "SUPERMAKI",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "adresse_fournisseur": "",
        "articles": []
    }
    
    # 1. Extraire numéro BDC
    bdc_match = re.search(r'Bon de commande n[°o]\s*(\d{8})', text, re.IGNORECASE)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    else:
        bdc_match = re.search(r'n[°o]\s*(\d{8})', text, re.IGNORECASE)
        if bdc_match:
            result["numero"] = bdc_match.group(1)
    
    # 2. Extraire date
    date_match = re.search(r'Date\s+[ée]mission\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if date_match:
        result["date"] = date_match.group(1)
    else:
        # Chercher d'autres formats de date
        date_match = re.search(r'(\d{2}/\d{2}/\d{4})\s+Secteur', text, re.IGNORECASE)
        if date_match:
            result["date"] = date_match.group(1)
    
    # 3. Extraire adresse livraison
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'adresse de livraison' in line.lower():
            if i + 1 < len(lines):
                result["adresse_livraison"] = lines[i + 1].strip()
                break
    
    # 4. EXTRACTION ROBUSTE DES ARTICLES
    # Méthode 1: Chercher les lignes de tableau structurées
    for line in lines:
        line_clean = line.strip()
        
        # Ignorer les lignes trop courtes ou les entêtes
        if len(line_clean) < 15 or line_clean.startswith('REF') or line_clean.startswith('Désignation'):
            continue
        
        # Chercher un pattern de ligne d'article (doit contenir des mots-clés)
        has_product_keyword = any(keyword in line_clean.upper() for keyword in 
                                 ['COTE', 'FIANAR', 'MAROPARASY', 'AMBALAVAO', 'JUS', 'RAISIN', 'CONS', 'VIN'])
        
        if has_product_keyword:
            # Chercher tous les nombres dans la ligne
            numbers = re.findall(r'\b\d+\b', line_clean)
            
            if len(numbers) >= 3:  # Au moins 3 nombres = probablement une ligne d'article
                # Chercher la quantité (généralement un nombre de 1-4 chiffres)
                # Priorité: chercher un nombre autour de 2-3 chiffres (quantité typique)
                qte = ""
                for num in numbers:
                    if 10 <= int(num) <= 999:  # Quantités typiques
                        qte = num
                        break
                
                if not qte and len(numbers) >= 2:
                    # Si pas trouvé, prendre le 2ème ou 3ème nombre
                    qte = numbers[1] if len(numbers) > 1 else numbers[0]
                
                # Extraire la désignation
                # Enlever tous les nombres et caractères spéciaux inutiles
                designation_raw = re.sub(r'\b\d+\b', ' ', line_clean)
                designation_raw = re.sub(r'[\.\-\*]', ' ', designation_raw)
                designation_raw = re.sub(r'\s+', ' ', designation_raw).strip()
                
                # Nettoyer et normaliser
                designation = normalize_designation_supermaki(designation_raw)
                
                # Extraire REF si présente (premier nombre de 5-6 chiffres)
                ref_match = re.search(r'\b(\d{5,6})\b', line_clean)
                ref = ref_match.group(1) if ref_match else ""
                
                # Extraire EAN si présent (13 chiffres)
                ean_match = re.search(r'\b(\d{13})\b', line_clean)
                ean = ean_match.group(1) if ean_match else ""
                
                article_data = {
                    "Désignation": designation,
                    "Qté": qte if qte else "1",
                    "Type": "consigne" if "CONS" in designation.upper() else "article"
                }
                
                if ref:
                    article_data["REF"] = ref
                if ean:
                    article_data["EAN"] = ean
                
                # Vérifier que nous avons une désignation valide
                if designation and len(designation.strip()) > 5:
                    # Éviter les doublons
                    if not any(a.get("Désignation") == designation for a in result["articles"]):
                        result["articles"].append(article_data)
    
    # Méthode 2: Si pas d'articles trouvés, chercher par structure de tableau
    if not result["articles"]:
        # Chercher la section tableau (après les en-têtes)
        in_table = False
        for line in lines:
            line_clean = line.strip()
            
            # Détecter le début du tableau
            if 'REF' in line_clean and 'EAN' in line_clean and 'Désignation' in line_clean:
                in_table = True
                continue
            
            if in_table and line_clean and not line_clean.startswith(('Montant', 'TOTAL', 'Seul')):
                # Essayer d'extraire avec un pattern spécifique
                pattern = r'(\d{6})\s+(\d{13})\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)'
                match = re.search(pattern, line_clean)
                
                if match:
                    ref = match.group(1)
                    ean = match.group(2)
                    designation_raw = match.group(3).strip()
                    # pcb = match.group(4)
                    # nb_colis = match.group(5)
                    qte = match.group(6)
                    
                    designation = normalize_designation_supermaki(designation_raw)
                    
                    article_data = {
                        "REF": ref,
                        "EAN": ean,
                        "Désignation": designation,
                        "Qté": qte,
                        "Type": "consigne" if "CONS" in designation.upper() else "article"
                    }
                    
                    result["articles"].append(article_data)
    
    # Méthode 3: Extraction par recherche de motifs spécifiques
    if not result["articles"]:
        # Chercher directement les articles connus dans le texte
        text_upper = text.upper()
        
        for article_name in SUPERMAKI_ARTICLES_LIST:
            article_upper = article_name.upper()
            
            # Vérifier si l'article est présent dans le texte
            keywords = article_upper.split()
            if len(keywords) >= 2:
                # Créer un pattern de recherche flexible
                search_terms = []
                for kw in keywords:
                    if len(kw) > 2:  # Ignorer les mots trop courts
                        search_terms.append(re.escape(kw))
                
                if search_terms:
                    # Chercher avec tolérance (mots dans n'importe quel ordre)
                    found = True
                    for term in search_terms[:3]:  # Prendre les 3 premiers termes significatifs
                        if not re.search(term, text_upper):
                            found = False
                            break
                    
                    if found:
                        # Trouver la quantité associée
                        # Chercher autour de la position de l'article
                        article_pattern = '.*?'.join(search_terms[:3])
                        match = re.search(article_pattern, text_upper)
                        
                        if match:
                            # Chercher un nombre dans les 30 caractères après l'article
                            start_pos = match.end()
                            end_pos = min(len(text_upper), start_pos + 50)
                            context = text_upper[start_pos:end_pos]
                            
                            qty_match = re.search(r'\b(\d{1,4})\b', context)
                            qte = qty_match.group(1) if qty_match else "1"
                            
                            result["articles"].append({
                                "Désignation": article_name,
                                "Qté": qte,
                                "Type": "consigne" if "CONS" in article_name.upper() else "article"
                            })
    
    return result

def extract_bdc_leader_price_precise(text: str):
    """Extraction PRÉCISE pour LEADER PRICE basée sur votre exemple exact"""
    result = {
        "client": "LEADER PRICE",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "articles": []
    }
    
    # 1. Extraire numéro BDC - Basé sur votre exemple exact
    # Votre exemple: "N° de Commande BCD169602"
    bdc_match = re.search(r'N[°o]\s+de\s+Commande\s+(BCD\d+)', text, re.IGNORECASE)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    else:
        bdc_match = re.search(r'BCD(\d+)', text, re.IGNORECASE)
        if bdc_match:
            result["numero"] = f"BCD{bdc_match.group(1)}"
    
    # 2. Extraire date - Basé sur votre exemple exact
    # Votre exemple: "Date 28/11/25"
    date_match = re.search(r'Date\s+(\d{2}/\d{2}/\d{2})', text, re.IGNORECASE)
    if date_match:
        date_str = date_match.group(1)
        day, month, year = date_str.split('/')
        year = "20" + year if len(year) == 2 else year
        result["date"] = f"{day}/{month}/{year}"
    
    # 3. Extraire adresse livraison
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'a livrer a' in line.lower() or 'à livrer à' in line.lower():
            address_lines = []
            for j in range(1, 4):
                if i + j < len(lines) and lines[i + j].strip():
                    address_lines.append(lines[i + j].strip())
            if address_lines:
                result["adresse_livraison"] = " ".join(address_lines)
                break
    
    # 4. EXTRACTION PRÉCISE DES ARTICLES - BASÉE SUR VOTRE EXEMPLE EXACT
    # Votre exemple montre clairement le format:
    # "17920 VIN APERITIF ROUGE MAROPARASY 75CL 360.000 Plèces 30C/12 17 740,00 5% 6 067 080.00"
    # "8431 CONSIGNE BLLE CHAN FOUI 75CL 360.000 Plèces 2 000,00 720 000.00"
    
    lines = text.split('\n')
    
    for line in lines:
        line_clean = line.strip()
        
        # Chercher les lignes avec format quantité.000 (ex: 360.000)
        qty_match = re.search(r'(\d+)\.(\d{3})', line_clean)
        if qty_match:
            qte = qty_match.group(1) + qty_match.group(2)  # Combiner pour avoir "360000"
            
            # Chercher la référence (4-5 chiffres au début)
            ref_match = re.match(r'^(\d{4,5})\s+', line_clean)
            ref = ref_match.group(1) if ref_match else ""
            
            # Extraire la désignation
            # Tout entre la référence et la quantité
            if ref:
                line_after_ref = line_clean[len(ref):].strip()
            else:
                line_after_ref = line_clean
            
            # Trouver où commence la quantité
            qty_pos = line_after_ref.find(qty_match.group(0))
            if qty_pos > 0:
                designation = line_after_ref[:qty_pos].strip()
                
                # Nettoyer la désignation
                designation = re.sub(r'\s{2,}', ' ', designation)
                
                # Déterminer le type
                if 'CONSIGNE' in designation.upper():
                    article_type = "consigne"
                    # Standardiser la désignation
                    designation = "CONSIGNE BLLE CHAN FOUI 75CL"
                else:
                    article_type = "article"
                    # Nettoyer les désignations de vin
                    designation = re.sub(r'\s+75CL$', ' 75CL', designation)
                
                article_data = {
                    "Désignation": designation,
                    "Qté": qte,
                    "Type": article_type
                }
                
                if ref:
                    article_data["Réf"] = ref
                
                result["articles"].append(article_data)
    
    # Méthode alternative pour les cas simples
    if not result["articles"]:
        # Chercher pattern: référence + texte + quantité
        for line in lines:
            # Pattern: 4-5 chiffres + espace + texte + espace + nombre avec .000
            match = re.search(r'(\d{4,5})\s+([A-Z\s]+?75CL?)\s+(\d+)\.(\d{3})', line, re.IGNORECASE)
            if match:
                ref = match.group(1)
                designation = match.group(2).strip()
                qte = match.group(3) + match.group(4)
                
                article_type = "consigne" if "CONSIGNE" in designation.upper() else "article"
                
                result["articles"].append({
                    "Réf": ref,
                    "Désignation": designation,
                    "Qté": qte,
                    "Type": article_type
                })
    
    return result

def extract_bdc_ulys_precise(text: str):
    """Extraction PRÉCISE pour ULYS basée sur votre exemple exact"""
    result = {
        "client": "ULYS",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "nom_magasin": "",
        "nom_fournisseur": "",
        "articles": []
    }
    
    # 1. Extraire numéro BDC - Basé sur votre exemple exact
    # Votre exemple: "N° 4500264466"
    bdc_match = re.search(r'N[°o]\s+(\d{10})', text)
    if bdc_match:
        result["numero"] = bdc_match.group(1)
    
    # 2. Extraire date - Basé sur votre exemple exact
    # Votre exemple: "Date de la Commande: 30/11/2025"
    date_match = re.search(r'Date de la Commande\s*[:\.]\s*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if date_match:
        result["date"] = date_match.group(1)
    
    # 3. Extraire nom magasin
    magasin_match = re.search(r'Nom du Magasin\s*[:\.]\s*(.+)', text, re.IGNORECASE)
    if magasin_match:
        result["nom_magasin"] = magasin_match.group(1).strip()
        result["adresse_livraison"] = result["nom_magasin"]
    
    # 4. EXTRACTION PRÉCISE DES ARTICLES - BASÉE SUR VOTRE EXEMPLE EXACT
    # Votre exemple montre clairement le format:
    # "0796554900148 10043907 VIN ROUGE CUVEE SPEC AMBALAVAO 750ML NU PAQ 2 1 PAQ = 12 /PC 05.12.2025"
    # "2200072684704 10002012 CONS. CHAN FOUI 75CL /PC 72 1/PC=1/PC 05.12.2025"
    
    lines = text.split('\n')
    current_category = ""
    
    for line in lines:
        # Chercher les catégories (ex: "122111 - VINS ROUGES")
        category_match = re.match(r'(\d{6})\s*-\s*([A-Z\s]+)', line.strip())
        if category_match:
            current_category = category_match.group(2).strip()
            continue
        
        # Chercher GTIN (13-14 chiffres) - marqueur d'article
        gtin_match = re.search(r'\b(\d{13,14})\b', line)
        if gtin_match:
            gtin = gtin_match.group(1)
            
            # Chercher la quantité
            # Dans votre exemple, la quantité est après "PAQ" ou "/PC"
            qty_match = None
            
            # Pattern 1: PAQ suivi d'un nombre
            qty_match = re.search(r'PAQ\s+(\d+)', line)
            if not qty_match:
                # Pattern 2: /PC suivi d'un nombre
                qty_match = re.search(r'/PC\s+(\d+)', line)
            
            if qty_match:
                qte = qty_match.group(1)
                
                # Extraire la désignation
                # Tout entre le GTIN et "PAQ" ou "/PC" est la désignation
                line_after_gtin = line[line.find(gtin) + len(gtin):].strip()
                
                # Enlever Article No (8 chiffres) si présent
                line_after_gtin = re.sub(r'^\d{8}\s*', '', line_after_gtin)
                
                # Trouver où commence "PAQ" ou "/PC"
                paq_pos = line_after_gtin.find('PAQ')
                pc_pos = line_after_gtin.find('/PC')
                
                end_pos = min(paq_pos if paq_pos > 0 else len(line_after_gtin),
                            pc_pos if pc_pos > 0 else len(line_after_gtin))
                
                if end_pos > 0:
                    designation = line_after_gtin[:end_pos].strip()
                    
                    # Nettoyer la désignation
                    designation = re.sub(r'\s{2,}', ' ', designation)
                    
                    # Ajouter la catégorie si disponible
                    if current_category and not current_category in designation:
                        designation = f"{current_category} - {designation}"
                    
                    # Déterminer le type
                    if 'CONS.' in designation or 'CONSIGNE' in designation:
                        article_type = "consigne"
                        # Standardiser la désignation
                        designation = "CONS. CHAN FOUI 75CL"
                    else:
                        article_type = "article"
                        # Nettoyer les désignations de vin
                        designation = re.sub(r'\s+750?ML\s+NU$', ' 750ML NU', designation)
                    
                    article_data = {
                        "Désignation": designation,
                        "Qté": qte,
                        "Type": article_type
                    }
                    
                    article_data["GTIN"] = gtin
                    
                    result["articles"].append(article_data)
    
    # Méthode alternative plus simple
    if not result["articles"]:
        for line in lines:
            # Chercher pattern simple: GTIN + texte + PAQ/PC + quantité
            if 'PAQ' in line or '/PC' in line:
                # Chercher GTIN
                gtin_match = re.search(r'\b(\d{13,14})\b', line)
                if gtin_match:
                    gtin = gtin_match.group(1)
                    
                    # Chercher quantité (nombre après PAQ ou /PC)
                    if 'PAQ' in line:
                        qty_part = line.split('PAQ')[1]
                    else:
                        qty_part = line.split('/PC')[1]
                    
                    qty_match = re.search(r'\b(\d+)\b', qty_part)
                    if qty_match:
                        qte = qty_match.group(1)
                        
                        # Extraire désignation approximative
                        # Tout entre GTIN et PAQ/PC
                        if 'PAQ' in line:
                            desig_part = line.split('PAQ')[0]
                        else:
                            desig_part = line.split('/PC')[0]
                        
                        # Enlever GTIN
                        desig_part = desig_part.replace(gtin, '').strip()
                        # Enlever Article No si présent (8 chiffres)
                        desig_part = re.sub(r'\d{8}', '', desig_part).strip()
                        
                        if desig_part:
                            result["articles"].append({
                                "GTIN": gtin,
                                "Désignation": desig_part,
                                "Qté": qte,
                                "Type": "consigne" if "CONS" in desig_part.upper() else "article"
                            })
    
    return result

def enhanced_bdc_pipeline_precise(image_bytes: bytes, client_type: str = "auto"):
    """Pipeline BDC ultra-précis avec améliorations"""
    
    # 1. Prétraitement
    processed_img = advanced_preprocess_image(image_bytes)
    
    # 2. OCR
    ocr_result = google_vision_ocr_with_hints(processed_img, client_type)
    raw_text = ocr_result["raw_text"]
    raw_text = clean_text(raw_text)
    
    # Sauvegarder le texte brut pour debug
    debug_text = raw_text
    
    # 3. Détection automatique du client
    if client_type == "auto":
        if "SUPERMAKI" in raw_text or "AMBOHIBAO" in raw_text:
            client_type = "SUPERMAKI"
        elif "LEADER PRICE" in raw_text or "D.L.P.M" in raw_text:
            client_type = "LEADER PRICE"
        elif "ULYS" in raw_text or "SUPER U" in raw_text:
            client_type = "ULYS"
        else:
            client_type = "SUPERMAKI"
    
    # 4. Extraction PRÉCISE selon le client
    if client_type == "SUPERMAKI":
        result = extract_bdc_supermaki_precise(raw_text)
    elif client_type == "LEADER PRICE":
        result = extract_bdc_leader_price_precise(raw_text)
    elif client_type == "ULYS":
        result = extract_bdc_ulys_precise(raw_text)
    else:
        result = extract_bdc_supermaki_precise(raw_text)
    
    # 5. Nettoyer et valider les données
    if result["articles"]:
        # Nettoyer les quantités
        for article in result["articles"]:
            if "Qté" in article:
                # Convertir "360.000" en "360000"
                qte = str(article["Qté"])
                qte = qte.replace('.', '').replace(',', '').strip()
                if qte.isdigit():
                    article["Qté"] = qte
                else:
                    # Si la quantité n'est pas valide, essayer de la trouver dans le texte brut
                    designation = article.get("Désignation", "")
                    if designation:
                        # Chercher la quantité près de la désignation dans le texte brut
                        short_desig = designation[:30]
                        if short_desig:
                            pattern = re.escape(short_desig[:20]) + r'.*?(\d{1,4})\b'
                            qty_match = re.search(pattern, debug_text, re.IGNORECASE)
                            if qty_match:
                                article["Qté"] = qty_match.group(1)
        
        # Filtrer les articles sans désignation valide
        result["articles"] = [a for a in result["articles"] if a.get("Désignation") and a.get("Désignation").strip()]
        
        # Calculer un score de confiance
        total_articles = len(result["articles"])
        valid_articles = sum(1 for a in result["articles"] if a.get("Qté") and a.get("Désignation"))
        confidence = valid_articles / total_articles if total_articles > 0 else 0
        
        result["overall_confidence"] = confidence
        result["article_count"] = total_articles
    else:
        result["overall_confidence"] = 0
        result["article_count"] = 0
    
    # 6. Ajouter métadonnées
    result["raw"] = debug_text
    result["client_type"] = client_type
    
    return result

def display_table_preview_enhanced(articles, client_type):
    """Affiche un aperçu formaté du tableau extrait avec plus de détails"""
    
    if not articles:
        return "<div class='table-preview'><p style='color: #666; text-align: center; padding: 20px;'>Aucun article détecté dans le document</p></div>"
    
    # Déterminer les colonnes selon le client
    columns = []
    column_titles = []
    
    if client_type == "SUPERMAKI":
        columns = ["Désignation", "Qté", "Type"]
        column_titles = ["Désignation", "Quantité", "Type"]
    elif client_type == "LEADER PRICE":
        columns = ["Réf", "Désignation", "Qté", "Type"]
        column_titles = ["Réf", "Désignation", "Quantité", "Type"]
    elif client_type == "ULYS":
        columns = ["GTIN", "Désignation", "Qté", "Type"]
        column_titles = ["GTIN", "Désignation", "Quantité", "Type"]
    else:
        columns = ["Désignation", "Qté", "Type"]
        column_titles = ["Désignation", "Quantité", "Type"]
    
    # Générer le HTML du tableau
    html = f"""
    <div class='table-preview'>
        <div style='margin-bottom: 15px; font-weight: bold; color: var(--petrol);'>
            📋 {len(articles)} article(s) détecté(s) - Format {client_type}
        </div>
        <div style='display: grid; grid-template-columns: repeat({len(columns)}, auto); gap: 1px; background: #ddd;'>
    """
    
    # En-tête
    for title in column_titles:
        html += f'<div class="table-header">{title}</div>'
    
    # Lignes de données
    for i, item in enumerate(articles):
        for col in columns:
            value = item.get(col, "")
            
            # Formater les valeurs
            if col == "Qté" and value:
                try:
                    # Essayer de formater en nombre avec séparateur de milliers
                    num_value = int(str(value).replace('.', '').replace(',', ''))
                    value = f"{num_value:,}".replace(",", " ")
                except:
                    pass
            
            if col == "Type" and value:
                if value == "consigne":
                    value = f"<span style='color: #e67e22; font-weight: bold;'>CONSIGNE</span>"
                else:
                    value = f"<span style='color: #27ae60;'>ARTICLE</span>"
            
            html += f'<div class="table-cell">{value}</div>'
    
    html += "</div>"
    
    # Calculer les totaux
    total_qty = 0
    articles_count = 0
    consignes_count = 0
    
    for item in articles:
        qte = item.get("Qté", "0")
        try:
            qte_num = int(str(qte).replace('.', '').replace(',', ''))
            total_qty += qte_num
            
            if item.get("Type") == "consigne":
                consignes_count += 1
            else:
                articles_count += 1
        except:
            pass
    
    html += f"""
        <div style='margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px;'>
            <div style='display: flex; justify-content: space-between;'>
                <div>
                    <strong>Total articles:</strong> {articles_count}
                </div>
                <div>
                    <strong>Total consignes:</strong> {consignes_count}
                </div>
                <div>
                    <strong>Quantité totale:</strong> {total_qty:,} unités
                </div>
            </div>
        </div>
    """
    
    html += "</div>"
    
    return html

# ---------------------------
# Le reste du code reste EXACTEMENT le même que votre version précédente
# ---------------------------

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
        if st.button("📝 Scanner BDC (Version Ultra-Précise)", use_container_width=True):
            st.session_state.mode = "bdc"
            st.rerun()
    
    st.markdown("<p style='text-align:center;font-size:0.9em;color:var(--muted)'>"
                "Version BDC avec extraction ultra-précise basée sur vos exemples réels</p>", unsafe_allow_html=True)
    
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
# NOUVEAU MODE BDC AVEC EXTRACTION ULTRA-PRÉCISE
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
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format avec REF, EAN, Désignation</p>", unsafe_allow_html=True)
            if st.button("Sélectionner SUPERMAKI", key="select_supermaki", use_container_width=True):
                st.session_state.bdc_client_type = "SUPERMAKI"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🏪 LEADER PRICE</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format avec Réf, Désignation, Qté</p>", unsafe_allow_html=True)
            if st.button("Sélectionner LEADER PRICE", key="select_leader", use_container_width=True):
                st.session_state.bdc_client_type = "LEADER PRICE"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='scan-option-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align:center'>🛒 ULYS</h4>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center;font-size:0.9em'>Format avec GTIN, Description, Qté</p>", unsafe_allow_html=True)
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
            
            with st.spinner(f"🔍 Extraction ultra-précise pour {client_name} en cours..."):
                try:
                    result = enhanced_bdc_pipeline_precise(img_bytes, st.session_state.bdc_client_type)
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
        
        # APERÇU DU TABLEAU EXTRACTION PRÉCISE
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<h4>📊 Tableau des articles détectés</h4>", unsafe_allow_html=True)
        
        # Afficher le tableau formaté
        table_html = display_table_preview_enhanced(result.get("articles", []), result.get("client_type", ""))
        st.markdown(table_html, unsafe_allow_html=True)
        
        # Indicateur de confiance
        overall_confidence = result.get("overall_confidence", 0)
        article_count = result.get("article_count", 0)
        
        if article_count > 0:
            if overall_confidence > 0.8:
                confidence_class = "confidence-high"
                confidence_text = "Élevée"
            elif overall_confidence > 0.6:
                confidence_class = "confidence-medium"
                confidence_text = "Moyenne"
            else:
                confidence_class = "confidence-low"
                confidence_text = "À vérifier"
            
            st.markdown(f"""
                <div class="{confidence_class}" style="margin-top: 15px;">
                    <strong>Confiance d'extraction : {overall_confidence:.0%} ({confidence_text})</strong><br>
                    <small>Basée sur {article_count} article(s) détecté(s) - Format {result.get('client_type', '')}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Aucun article détecté. Vérifiez la qualité de l'image ou essayez un autre type de BDC.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section informations détectées
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>📋 Informations du BDC</h4>", unsafe_allow_html=True)
        
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
        
        # Section articles éditable
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h4>🛒 Édition des articles (si nécessaire)</h4>", unsafe_allow_html=True)
        
        articles = result.get("articles", [])
        if articles:
            # Préparer les données pour l'affichage
            display_data = []
            for i, item in enumerate(articles):
                display_item = item.copy()
                display_data.append(display_item)
            
            df = pd.DataFrame(display_data)
            
            # Déterminer les colonnes à afficher
            if result.get("client_type") == "SUPERMAKI":
                column_order = ["Désignation", "Qté", "Type"]
            elif result.get("client_type") == "LEADER PRICE":
                column_order = ["Réf", "Désignation", "Qté", "Type"]
            elif result.get("client_type") == "ULYS":
                column_order = ["GTIN", "Désignation", "Qté", "Type"]
            else:
                column_order = [col for col in df.columns]
            
            # Réorganiser les colonnes
            existing_cols = [col for col in column_order if col in df.columns]
            df = df.reindex(columns=existing_cols)
            
            # Configurer les colonnes pour l'édition
            column_config = {}
            for col in df.columns:
                if col == "Qté":
                    column_config[col] = st.column_config.NumberColumn("Quantité", min_value=0)
                elif col == "Type":
                    column_config[col] = st.column_config.SelectboxColumn("Type", options=["article", "consigne"])
                else:
                    column_config[col] = st.column_config.TextColumn(col)
            
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config=column_config,
                use_container_width=True,
                key="bdc_articles_editor"
            )
        else:
            st.info("💡 Pour ajouter des articles manuellement, utilisez le tableau ci-dessous.")
            df = pd.DataFrame(columns=["Désignation", "Qté", "Type"])
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                column_config={
                    "Désignation": st.column_config.TextColumn("Article (Désignation)"),
                    "Qté": st.column_config.NumberColumn("Quantité", min_value=0),
                    "Type": st.column_config.SelectboxColumn("Type", options=["article", "consigne"])
                },
                use_container_width=True,
                key="bdc_articles_empty"
            )
        
        if st.button("➕ Ajouter une ligne manuellement", key="bdc_add_line"):
            new_row = {"Désignation": "", "Qté": 0, "Type": "article"}
            if 'edited_df' in locals():
                edited_df = pd.concat([edited_df, pd.DataFrame([new_row])], ignore_index=True)
            else:
                edited_df = pd.DataFrame([new_row])
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Section debug OCR
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        with st.expander("🔍 Voir le texte OCR brut pour vérification"):
            st.text_area("Texte OCR complet", value=result.get("raw", ""), height=300, key="bdc_raw")
        
        # Bouton pour forcer la réextraction avec un autre algorithme
        if st.button("🔄 Réessayer l'extraction avec un autre algorithme", key="bdc_retry"):
            st.session_state.show_ocr_results = False
            st.rerun()
        
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
                        # Préparer les données à partir du dataframe édité
                        articles_to_save = []
                        if 'edited_df' in locals():
                            for _, row in edited_df.iterrows():
                                article_data = {}
                                for col in edited_df.columns:
                                    article_data[col] = row[col]
                                articles_to_save.append(article_data)
                        
                        if articles_to_save:
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
                                st.info(f"📝 Format: Date | Client | Numéro BDC | Adresse | Article | Qte | Editeur")
                                st.info(f"👤 Enregistré par: {st.session_state.user_nom}")
                                st.info(f"🏷️ Type: {result.get('client_type', 'Inconnu')}")
                                
                                # Afficher un récapitulatif
                                st.markdown("---")
                                st.markdown("### 📋 Récapitulatif enregistré:")
                                for i, article in enumerate(articles_to_save[:5]):  # Montrer les 5 premiers
                                    st.write(f"**{i+1}.** {article.get('Désignation', '')} - Qté: {article.get('Qté', '')}")
                                
                                if len(articles_to_save) > 5:
                                    st.write(f"... et {len(articles_to_save) - 5} autres articles")
                                
                                if st.button("🗑️ Effacer et scanner un nouveau BDC", use_container_width=True, type="secondary"):
                                    st.session_state.uploaded_file = None
                                    st.session_state.show_ocr_results = False
                                    st.session_state.ocr_result = None
                                    st.rerun()
                                    
                            elif duplicate_count > 0:
                                st.warning("⚠️ Ce BDC existe déjà dans la base de données.")
                            else:
                                st.warning("⚠️ Aucune donnée valide à enregistrer")
                        else:
                            st.error("❌ Aucun article à enregistrer. Ajoutez des articles dans le tableau ci-dessus.")
                            
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'enregistrement: {str(e)}")
            
            # Boutons de contrôle
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🗑️ Effacer et recommencer", use_container_width=True, type="secondary", key="bdc_clear"):
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
                if st.button("📤 Tester avec autre image", use_container_width=True, type="secondary", key="bdc_test_another"):
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
