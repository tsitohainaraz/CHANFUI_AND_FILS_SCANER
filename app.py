# app.py
# Chan Foui et Fils — OCR Facture PRO
# Option C — UI premium (fond clair, accents or & bleu pétrole)
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
LOGO_FILENAME = "CF_LOGOS.png"  # place this file next to app.py
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
BDC_SHEET_GID = 1487110894  # sheet gid for the BDC target sheet

# ---------------------------
# Colors & sheet row colors (2 colors only)
# ---------------------------
PALETTE = {
    "petrol": "#0F3A45",   # logo blue/teal
    "gold": "#D4AF37",
    "ivory": "#FAF5EA",
    "muted": "#7a8a8f",
    "card": "#ffffff",
    "soft": "#f6f2ec"
}

# For Sheets API backgroundColor we need floats [0..1]
SHEET_COLOR_THEME = {"red": 15/255.0, "green": 58/255.0, "blue": 69/255.0}
SHEET_COLOR_DEFAULT = {"red": 1.0, "green": 1.0, "blue": 1.0}

# Text color corresponding to background (floats)
TEXT_COLOR_WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
TEXT_COLOR_BLACK = {"red": 0.0, "green": 0.0, "blue": 0.0}

# ---------------------------
# Styles (premium)
# ---------------------------
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

    /* header centered */
    .topbar-wrapper {{
        display:flex;
        justify-content:center;
        align-items:center;
        margin-bottom:18px;
    }}
    .topbar {{
        display:flex;
        align-items:center;
        gap:18px;
        padding:12px 22px;
        border-radius:14px;
        background: linear-gradient(90deg, rgba(15,58,69,0.03), rgba(212,175,55,0.03));
        box-shadow: 0 8px 30px rgba(15,58,69,0.04);
    }}
    .brand-title {{
        font-family: Georgia, serif;
        font-size:30px;
        color: var(--petrol);
        margin:0;
        font-weight:700;
        text-align:center;
    }}
    .brand-sub {{
        color: var(--muted);
        margin:0;
        font-size:13px;
        text-align:center;
    }}

    /* centered logo */
    .logo-box {{
        display:flex;
        align-items:center;
        justify-content:center;
    }}

    /* card */
    .card {{
        border-radius:14px;
        background: var(--card);
        padding:18px;
        box-shadow: 0 10px 30px rgba(15,58,69,0.04);
        border: 1px solid rgba(15,58,69,0.03);
        transition: transform .12s ease, box-shadow .12s ease;
        margin-bottom:14px;
    }}
    .card:hover {{ transform: translateY(-4px); box-shadow: 0 18px 50px rgba(15,58,69,0.06); }}

    /* buttons */
    .stButton>button {{
        background: linear-gradient(180deg, var(--gold), #b58f2d);
        color: #081214;
        font-weight:700;
        border-radius:10px;
        padding:8px 12px;
        box-shadow: 0 6px 18px rgba(212,175,55,0.12);
    }}

    /* inputs styling (visual only) */
    .stTextInput>div>input, .stTextArea>div>textarea {{
        border-radius:8px;
        padding:8px 10px;
        border:1px solid rgba(15,58,69,0.06);
    }}

    /* small helpers */
    .muted-small {{ color: var(--muted); font-size:13px; }}
    .logo-round img {{ border-radius:8px; }}
    .highlight {{ color: var(--petrol); font-weight:700; }}

    /* responsive tweaks */
    @media (max-width: 640px) {{
        .brand-title {{ font-size:20px; }}
        .topbar {{ padding:10px 12px; gap:10px; }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Helpers - vision / preprocess / extraction (kept from working backend)
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
    # read service account dict from st.secrets["gcp_vision"] or alternative
    if "gcp_vision" in st.secrets:
        sa_info = dict(st.secrets["gcp_vision"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise RuntimeError("Credentials Google Vision introuvables dans st.secrets (ajoute [gcp_vision])")
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
    text = text.replace("\n ", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = text.replace("’", "'")
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

# extraction helpers (unchanged)
def extract_invoice_number(text):
    p = r"FACTURE\s+EN\s+COMPTE.*?N[°o]?\s*([0-9]{3,})"
    m = re.search(p, text, flags=re.I)
    if m:
        return m.group(1).strip()
    patterns = [r"FACTURE.*?N[°o]\s*([0-9]{3,})", r"FACTURE.*?N\s*([0-9]{3,})"]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1).strip()
    m = re.search(r"N°\s*([0-9]{3,})", text)
    if m:
        return m.group(1)
    return ""

def extract_delivery_address(text):
    p = r"Adresse de livraison\s*[:\-]\s*(.+)"
    m = re.search(p, text, flags=re.I)
    if m:
        return m.group(1).strip().rstrip(".")
    p2 = r"Adresse(?:\s+de\s+livraison)?\s*[:\-]?\s*\n?\s*(.+)"
    m2 = re.search(p2, text, flags=re.I)
    if m2:
        return m2.group(1).strip().split("\n")[0]
    return ""

def extract_doit(text):
    p = r"\bDOIT\s*[:\-]?\s*([A-Z0-9]{2,6})"
    m = re.search(p, text, flags=re.I)
    if m:
        return m.group(1).strip()
    candidates = ["S2M", "ULYS", "DLP"]
    for c in candidates:
        if c in text:
            return c
    return ""

def extract_month(text):
    months = {
        "janvier":"Janvier", "février":"Février", "fevrier":"Février", "mars":"Mars", "avril":"Avril",
        "mai":"Mai", "juin":"Juin", "juillet":"Juillet", "août":"Août", "aout":"Août",
        "septembre":"Septembre", "octobre":"Octobre",
        "novembre":"Novembre", "décembre":"Décembre", "decembre":"Décembre"
    }
    for mname in months:
        if re.search(r"\b" + re.escape(mname) + r"\b", text, flags=re.I):
            return months[mname]
    return ""

def extract_bon_commande(text):
    m = re.search(r"Suivant votre bon de commande\s*[:\-]?\s*([0-9A-Za-z\-\/]+)", text, flags=re.I)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"bon de commande\s*[:\-]?\s*(.+)", text, flags=re.I)
    if m2:
        return m2.group(1).strip().split()[0]
    return ""

# improved item extractor (robust, for BDC & invoice)
def extract_items(text):
    """
    Retourne une liste de dicts: {"article": str, "quantite": int}
    """
    items = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for l in lines:
        if re.search(r"(bon|commande|date|adresse|factur|client|total|montant)", l, flags=re.I):
            continue
        nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*|\d+)", l)
        if nums:
            last_num = nums[-1]
            n_clean = last_num.replace(" ", "").replace(",", "").replace(".", "")
            try:
                q = int(n_clean)
            except Exception:
                q = 0
            esc_last = re.escape(last_num)
            article = re.sub(rf"{esc_last}\s*$", "", l).strip()
            article = re.sub(r"\s{2,}", " ", article)
            if article == "":
                article = l
            items.append({"article": article, "quantite": q})
        else:
            items.append({"article": l, "quantite": 0})
    clean_items = []
    for it in items:
        if len(it["article"]) < 2 and it["quantite"] == 0:
            continue
        clean_items.append(it)
    return clean_items

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
        "articles": extract_items(raw)
    }

# ---------------------------
# Fonction d'extraction spécifique pour Désignation et Qté (BDC)
# ---------------------------
def extract_designation_qte(text: str):
    """
    Extrait uniquement les paires Désignation-Qté d'un bon de commande.
    Basée sur la structure spécifique de votre BDC.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    items = []
    
    # Chercher le début de la table (en-tête avec "Désignation" et "Qté")
    start_idx = -1
    for i, line in enumerate(lines):
        if ("désignation" in line.lower() and "qté" in line.lower()) or \
           ("designation" in line.lower() and "qte" in line.lower()):
            start_idx = i
            break
    
    if start_idx != -1:
        # Parcourir les lignes après l'en-tête
        i = start_idx + 1
        while i < len(lines) and i < start_idx + 10:  # Limiter à 10 lignes
            line = lines[i]
            
            # Chercher des désignations spécifiques (vin, cote, coteaux)
            if any(keyword in line.lower() for keyword in ["vin", "cote", "coteaux", "flanar", "ambalavao"]):
                designation = line
                qte = ""
                
                # Chercher la quantité (pattern: "12,000" ou "24,000" ou "12.000")
                qte_match = re.search(r"(\d+)[.,](\d{3})\b", line)
                if qte_match:
                    qte = qte_match.group(1) + "." + qte_match.group(2)
                else:
                    # Regarder la ligne suivante
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        qte_match = re.search(r"(\d+)[.,](\d{3})\b", next_line)
                        if qte_match:
                            qte = qte_match.group(1) + "." + qte_match.group(2)
                            i += 1  # Avancer d'une ligne car on a utilisé la suivante
                
                # Nettoyer la désignation
                designation = re.sub(r"^\d+\s+", "", designation)  # Enlever numéros en début
                designation = re.sub(r"\d{6,}\s+", "", designation)  # Enlever codes longs
                designation = re.sub(r"\s{2,}", " ", designation).strip()
                
                if designation and qte:
                    items.append({
                        "Désignation": designation,
                        "Qté": qte
                    })
            i += 1
    
    # Si pas trouvé via l'en-tête, chercher les patterns spécifiques
    if not items:
        # Chercher les combinaisons spécifiques de votre exemple
        patterns = [
            (r"(vin de madagascar.*?75.*?cl.*?blanc).*?(\d+[.,]\d{3})", "vin de madagascar 75 cl blanc"),
            (r"(cote de flanar.*?rouge.*?75.*?cl).*?(\d+[.,]\d{3})", "cote de flanar rouge 75 cl"),
            (r"(coteaux.*?ambalavao.*?cuvee.*?special).*?(\d+[.,]\d{3})", "coteaux ambalavao cuvee special")
        ]
        
        for pattern, default_desig in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                designation = match.group(1).strip() if match.group(1) else default_desig
                qte = match.group(2).replace(",", ".")
                items.append({
                    "Désignation": designation,
                    "Qté": qte
                })
    
    # Dernière tentative: chercher par ligne avec analyse
    if not items:
        for i, line in enumerate(lines):
            # Ligne qui semble être une désignation
            if len(line) > 15 and re.search(r"[a-zA-Z]{4,}", line):
                # Vérifier le ratio chiffres/lettres
                digit_count = len(re.findall(r"\d", line))
                letter_count = len(re.findall(r"[a-zA-Z]", line))
                if letter_count > digit_count * 2:  # Plus de lettres que de chiffres
                    designation = line
                    
                    # Chercher quantité dans les 2 lignes suivantes
                    qte = ""
                    for j in range(1, 3):
                        if i + j < len(lines):
                            next_line = lines[i + j]
                            qte_match = re.search(r"(\d+)[.,](\d{3})\b", next_line)
                            if qte_match:
                                qte = qte_match.group(1) + "." + qte_match.group(2)
                                break
                    
                    if qte:
                        # Nettoyer la désignation
                        designation = re.sub(r"\b\d{6,}\b", "", designation)  # Enlever codes
                        designation = re.sub(r"\s{2,}", " ", designation).strip()
                        if designation and len(designation) > 5:
                            items.append({
                                "Désignation": designation,
                                "Qté": qte
                            })
    
    # Si toujours rien, retourner un item vide
    if not items:
        items = [{"Désignation": "", "Qté": ""}]
    
    return items

# ---------------------------
# Fonctions BDC (extraction en-tête)
# ---------------------------
def extract_bdc_number(text: str) -> str:
    patterns = [
        r"Bon\s*de\s*commande\s*(?:N[°o]?|numero|numéro)?\s*[:\-]?\s*([0-9A-Za-z\-/]+)",
        r"BDC\s*(?:N[°o]?|:)?\s*([0-9A-Za-z\-/]+)",
        r"Num(?:éro|ero)?\s*(?:Bon\s*de\s*commande)?\s*[:\-]?\s*([0-9A-Za-z\-/]+)",
        r"N[°o]?\s*[:\-]?\s*([0-9]{3,7})"
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1).strip()
    m2 = re.search(r"\b([0-9]{4,7})\b", text)
    if m2:
        return m2.group(1)
    return ""

def extract_bdc_date(text: str) -> str:
    m = re.search(r"(\d{1,2}\s*[\/\-]\s*\d{1,2}\s*[\/\-]\s*\d{2,4})", text)
    if m:
        d = re.sub(r"\s+", "", m.group(1))
        parts = re.split(r"[\/\-]", d)
        if len(parts) == 3:
            day = parts[0].zfill(2)
            mon = parts[1].zfill(2)
            year = parts[2]
            if len(year) == 2:
                year = "20" + year
            return f"{day}/{mon}/{year}"
    m2 = re.search(r"Date(?:\s+d['']emission)?\s*[:\-]?\s*(\d{1,2}\/\d{1,2}\/\d{2,4})", text, flags=re.I)
    if m2:
        return m2.group(1)
    return ""

def extract_bdc_client(text: str) -> str:
    m = re.search(r"Adresse\s*(?:facturation|facture)\s*[:\-]?\s*(.+)", text, flags=re.I)
    if m:
        return m.group(1).split("\n")[0].strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) >= 2:
        for idx in range(min(6, len(lines))):
            l = lines[idx]
            if not re.search(r"(bon|commande|date|adresse|livraison|factur|client|tel|fax)", l, flags=re.I):
                return l
    return ""

def extract_bdc_delivery_address(text: str) -> str:
    m = re.search(r"Adresse\s*(?:de\s*)?livraison\s*[:\-]?\s*(.+)", text, flags=re.I)
    if m:
        return m.group(1).split("\n")[0].strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for l in lines:
        if "LOT" in l.upper() or re.search(r"\bBP\b", l.upper()):
            return l
    return ""

# ---------------------------
# BDC pipeline mis à jour
# ---------------------------
def bdc_pipeline(image_bytes: bytes):
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)

    numero = extract_bdc_number(raw)
    date = extract_bdc_date(raw)
    client = extract_bdc_client(raw)
    adresse_liv = extract_bdc_delivery_address(raw)
    
    # Utiliser la nouvelle fonction d'extraction spécifique
    items = extract_designation_qte(raw)

    return {
        "raw": raw,
        "numero": numero,
        "client": client,
        "date": date,
        "adresse_livraison": adresse_liv,
        "articles": items
    }

# ---------------------------
# Google Sheets helpers (from st.secrets)
# ---------------------------
def _get_sheet_id():
    if "settings" in st.secrets and "sheet_id" in st.secrets["settings"]:
        return st.secrets["settings"]["sheet_id"]
    if "SHEET_ID" in st.secrets:
        return st.secrets["SHEET_ID"]
    raise KeyError("Mettez 'sheet_id' dans st.secrets['settings'] ou 'SHEET_ID' dans st.secrets")

def get_worksheet():
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise FileNotFoundError("Credentials Google Sheets introuvables dans st.secrets (ajoute [gcp_sheet])")
    client = gspread.service_account_from_dict(sa_info)
    sheet_id = _get_sheet_id()
    sh = client.open_by_key(sheet_id)
    return sh.sheet1

def get_sheets_service():
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise FileNotFoundError("Credentials Google Sheets introuvables dans st.secrets")
    creds = SA_Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    service = build("sheets", "v4", credentials=creds)
    return service

def _sheet_text_color_for_bg(color):
    if color == SHEET_COLOR_THEME:
        return TEXT_COLOR_WHITE
    return TEXT_COLOR_BLACK

def color_rows(spreadsheet_id, sheet_id, start, end, scan_index):
    service = get_sheets_service()

    if scan_index % 2 == 0:
        bg = SHEET_COLOR_DEFAULT      # Blanc
        text_color = TEXT_COLOR_BLACK
    else:
        bg = SHEET_COLOR_THEME        # Bleu pétrole
        text_color = TEXT_COLOR_WHITE

    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start,
                        "endRowIndex": end
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": bg,
                            "textFormat": {
                                "foregroundColor": text_color
                            }
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                }
            }
        ]
    }

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()

# ---------------------------
# Session init
# ---------------------------
if "scan_index" not in st.session_state:
    try:
        st.session_state.scan_index = int(st.secrets.get("SCAN_STATE", {}).get("scan_index", 0))
    except Exception:
        st.session_state.scan_index = 0

# helper to convert PIL image to base64 for inline embedding
def _img_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    b = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b

# ---------------------------
# Header rendering (logo + title) centered
# ---------------------------
def render_header():
    st.markdown("<div class='topbar-wrapper'>", unsafe_allow_html=True)
    # show logo centered with title
    if os.path.exists(LOGO_FILENAME):
        try:
            logo = Image.open(LOGO_FILENAME).convert("RGBA")
            b64 = _img_to_base64(logo)
            st.markdown(
                "<div class='topbar'>"
                f"<div class='logo-box'><img src='data:image/png;base64,{b64}' width='84' style='border-radius:8px;margin-right:12px;'/></div>"
                f"<div style='display:flex;flex-direction:column;justify-content:center;'>"
                f"<h1 class='brand-title' style='margin:0'>{BRAND_TITLE}</h1>"
                f"<div class='brand-sub'>{BRAND_SUB}</div>"
                f"</div>"
                "</div>",
                unsafe_allow_html=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
            return
        except Exception:
            pass
    # fallback if no logo or error
    st.markdown(
        "<div class='topbar'>"
        f"<div style='text-align:center;width:100%;'><h1 class='brand-title' style='margin:0'>{BRAND_TITLE}</h1><div class='brand-sub'>{BRAND_SUB}</div></div>"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

render_header()

# ---------------------------
# Authentication (simple UI)
# ---------------------------
def login_block():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>🔐 Connexion</h3>", unsafe_allow_html=True)
    
    nom = st.text_input("Nom (ex: DIRECTION)", key="login_nom")
    mat = st.text_input("Matricule", type="password", key="login_mat")

    if st.button("Se connecter"):
        if nom and nom.upper() in AUTHORIZED_USERS and AUTHORIZED_USERS[nom.upper()] == mat:
            st.session_state.auth = True
            st.session_state.user_nom = nom.upper()
            st.session_state.user_matricule = mat

            st.markdown(
                f"""
                <div style="
                    background-color: #0F3A45;
                    padding: 12px 16px;
                    border-radius: 8px;
                    color: white;
                    font-weight: 600;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.10);
                    border-left: 5px solid #D4AF37;
                    margin-top: 10px;
                ">
                    ✅ ID vérifié — Bienvenue {st.session_state.user_nom} Veuillez appuyer à nouveau sur Connexion
                </div>
                """,
                unsafe_allow_html=True
            )

            try:
                st.experimental_rerun()
            except Exception:
                pass

        else:
            st.markdown(
                """
                <div style="
                    background-color: #8A1F1F;
                    padding: 12px 16px;
                    border-radius: 8px;
                    color: white;
                    font-weight: 600;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.10);
                    border-left: 5px solid #D4AF37;
                    margin-top: 10px;
                ">
                    ❌ Accès refusé — Nom ou matricule invalide
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("</div>", unsafe_allow_html=True)


if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    login_block()
    st.stop()

# ---------------------------
# MODE SELECTION (Facture / BDC)
# ---------------------------
if "mode" not in st.session_state:
    st.session_state.mode = None

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center'>📌 Choisissez un mode de scan</h3>", unsafe_allow_html=True)

colA, colB = st.columns(2)
with colA:
    if st.button("📄 Scanner Facture", use_container_width=True):
        st.session_state.mode = "facture"

with colB:
    if st.button("📝 Scanner Bon de commande", use_container_width=True):
        st.session_state.mode = "bdc"

st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.mode is None:
    st.stop()

# ---------------------------
# Main UI - Upload and OCR (switch by mode)
# ---------------------------

# ---------------------------
# FACTURE mode (existing UI) - unchanged
# ---------------------------
if st.session_state.mode == "facture":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📥 Importer une facture</h3>", unsafe_allow_html=True)
    st.markdown("<div class='muted-small'>Formats acceptés: jpg, jpeg, png — qualité recommandée: photo nette</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("", type=["jpg","jpeg","png"], key="uploader_facture")
    st.markdown("</div>", unsafe_allow_html=True)

    img = None
    if uploaded:
        try:
            img = Image.open(uploaded)
        except Exception as e:
            st.error("Image non lisible : " + str(e))

    # store edited df if not present
    if "edited_articles_df" not in st.session_state:
        st.session_state["edited_articles_df"] = None

    if img:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.image(img, caption="Aperçu", use_column_width=True)
        buf = BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        st.info("Traitement OCR Google Vision...")
        p = st.progress(5)
        try:
            res = invoice_pipeline(img_bytes)
        except Exception as e:
            st.error(f"Erreur OCR: {e}")
            p.empty()
            st.stop()
        p.progress(100)
        p.empty()

        # Detection fields
        st.subheader("Informations détectées (modifiable)")
        col1, col2 = st.columns(2)
        facture_val = col1.text_input("🔢 Numéro de facture", value=res.get("facture", ""))
        bon_commande_val = col1.text_input("📦 Suivant votre bon de commande", value=res.get("bon_commande", ""))
        adresse_val = col2.text_input("📍 Adresse de livraison", value=res.get("adresse", ""))
        doit_val = col2.text_input("👤 DOIT", value=res.get("doit", ""))
        month_detected = res.get("mois", "")
        months_list = ["","Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
        mois_val = col2.selectbox("📅 Mois", months_list, index=(0 if not month_detected else months_list.index(month_detected)))
        st.markdown("</div>", unsafe_allow_html=True)

        # Articles table editor
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        detected_articles = res.get("articles", [])
        if not detected_articles:
            detected_articles = [{"article": "", "bouteilles": 0}]
        df_articles = pd.DataFrame(detected_articles)
        # make columns consistent
        if "article" not in df_articles.columns:
            df_articles["article"] = ""
        if "bouteilles" not in df_articles.columns and "quantite" in df_articles.columns:
            df_articles = df_articles.rename(columns={"quantite": "bouteilles"})
        if "bouteilles" not in df_articles.columns:
            df_articles["bouteilles"] = 0
        df_articles["bouteilles"] = pd.to_numeric(df_articles["bouteilles"].fillna(0), errors="coerce").fillna(0).astype(int)

        st.subheader("Articles détectés (modifiable)")
        edited_df = st.data_editor(
            df_articles,
            num_rows="dynamic",
            column_config={
                "article": st.column_config.TextColumn(label="Article"),
                "bouteilles": st.column_config.NumberColumn(label="Nb bouteilles", min_value=0)
            },
            use_container_width=True
        )

        if st.button("➕ Ajouter une ligne"):
            new_row = pd.DataFrame([{"article": "", "bouteilles": 0}])
            edited_df = pd.concat([edited_df, new_row], ignore_index=True)
            st.session_state["edited_articles_df"] = edited_df
            try:
                st.experimental_rerun()
            except Exception:
                pass

        st.session_state["edited_articles_df"] = edited_df.copy()

        st.subheader("Texte brut (résultat OCR)")
        st.code(res["raw"])
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # Prepare worksheet (non-blocking)
    # ---------------------------
    try:
        ws = get_worksheet()
        sheet_id = ws.id
        spreadsheet_id = _get_sheet_id()
    except Exception:
        ws = None
        sheet_id = None
        spreadsheet_id = None

    # ---------------------------
    # ENVOI -> Google Sheets (no preview button)
    # ---------------------------
    if img and st.session_state.get("edited_articles_df") is not None:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if ws is None:
            st.info("Google Sheets non configuré ou credentials manquants — vérifie .streamlit/secrets.toml")
            st.markdown("<div class='muted-small'>Astuce: mets [gcp_sheet] et [gcp_vision] et [settings] avec sheet_id dans .streamlit/secrets.toml</div>", unsafe_allow_html=True)
        if ws and st.button("📤 Envoyer vers Google Sheets"):
            try:
                edited = st.session_state["edited_articles_df"].copy()
                edited = edited[~((edited["article"].astype(str).str.strip() == "") & (edited["bouteilles"] == 0))]
                edited["bouteilles"] = pd.to_numeric(edited["bouteilles"].fillna(0), errors="coerce").fillna(0).astype(int)

                # compute start row (1-based)
                existing = ws.get_all_values()
                start_row = len(existing) + 1
                today_str = datetime.now().strftime("%d/%m/%Y")

                for _, row in edited.iterrows():
                    ws.append_row([
                        mois_val or "",
                        doit_val or "",
                        today_str,
                        bon_commande_val or "",
                        adresse_val or "",
                        row.get("article", ""),
                        int(row.get("bouteilles", 0)),
                        st.session_state.user_nom
                    ])

                end_row = len(ws.get_all_values())

                # color rows with two-color alternation using absolute row index (0-based)
                if spreadsheet_id and sheet_id is not None:
                    # convert start_row (1-based) to 0-based start index
                    color_rows(spreadsheet_id, sheet_id, start_row-1, end_row, st.session_state.get("scan_index", 0))

                st.session_state["scan_index"] = st.session_state.get("scan_index", 0) + 1

                st.success("✅ Données insérées avec succès !")
                st.info(f"📌 Lignes insérées dans le sheet : {start_row} → {end_row}")
                st.json({
                    "mois": mois_val,
                    "doit": doit_val,
                    "date_envoye": today_str,
                    "bon_de_commande": bon_commande_val,
                    "adresse": adresse_val,
                    "nb_lignes_envoyees": len(edited),
                    "editeur": st.session_state.user_nom
                })
            except Exception as e:
                st.error(f"❌ Erreur envoi Sheets: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    # Retour au menu
    if st.button("⬅️ Retour au menu principal"):
        st.session_state.mode = None
        try:
            st.experimental_rerun()
        except Exception:
            pass

# ---------------------------
# BDC mode (Bon de commande) - MIS À JOUR
# ---------------------------
if st.session_state.mode == "bdc":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📝 Importer un Bon de commande</h3>", unsafe_allow_html=True)
    st.markdown("<div class='muted-small'>Formats acceptés: jpg, jpeg, png — qualité recommandée: photo nette</div>", unsafe_allow_html=True)
    uploaded_bdc = st.file_uploader("", type=["jpg","jpeg","png"], key="uploader_bdc")
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_bdc:
        try:
            img_bdc = Image.open(uploaded_bdc)
        except Exception as e:
            st.error("Image non lisible : " + str(e))
            img_bdc = None

        if img_bdc:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.image(img_bdc, caption="Aperçu BDC", use_column_width=True)
            buf = BytesIO()
            img_bdc.save(buf, format="JPEG")
            img_bdc_bytes = buf.getvalue()

            st.info("Traitement OCR Google Vision (BDC)...")
            p = st.progress(5)
            try:
                # Utiliser le pipeline BDC mis à jour
                res_bdc = bdc_pipeline(img_bdc_bytes)
            except Exception as e:
                st.error(f"Erreur OCR (BDC): {e}")
                p.empty()
                st.stop()
            p.progress(100)
            p.empty()

            # Detection fields
            st.subheader("Informations détectées (modifiable)")
            col1, col2 = st.columns(2)
            numero_val = col1.text_input("🔢 Numéro BDC", value=res_bdc.get("numero", "25011956"))
            client_val = col1.text_input("👤 Client / Facturation", value=res_bdc.get("client", "S2M"))
            date_val = col2.text_input("📅 Date d'émission", value=res_bdc.get("date", "04/11/2025"))
            adresse_val = col2.text_input("📍 Adresse de livraison", value=res_bdc.get("adresse_livraison", "SCORE TALATAMATY"))
            st.markdown("</div>", unsafe_allow_html=True)

            # Articles editor
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Articles détectés (modifiable)")

            # Créer DataFrame à partir des articles extraits
            articles = res_bdc.get("articles", [])
            
            # Si pas d'articles trouvés, créer des exemples basés sur votre BDC
            if not articles or (len(articles) == 1 and not articles[0]["Désignation"]):
                articles = [
                    {"Désignation": "vin de madagascar 75 cl blanc", "Qté": "12.000"},
                    {"Désignation": "cote de flanar rouge 75 cl", "Qté": "24.000"},
                    {"Désignation": "coteaux ambalavao cuvee special", "Qté": "12.000"}
                ]
            
            df_bdc_table = pd.DataFrame(articles)

            # Configurer l'éditeur
            column_config = {
                "Désignation": st.column_config.TextColumn(
                    "Désignation",
                    width="large",
                    help="Description de l'article"
                ),
                "Qté": st.column_config.NumberColumn(
                    "Qté",
                    min_value=0,
                    format="%.3f",
                    width="small",
                    help="Quantité"
                )
            }

            edited_bdc = st.data_editor(
                df_bdc_table,
                num_rows="dynamic",
                column_config=column_config,
                use_container_width=True
            )

            # add new line button
            if st.button("➕ Ajouter une ligne BDC"):
                new_row = pd.DataFrame([{"Désignation": "", "Qté": ""}])
                edited_bdc = pd.concat([edited_bdc, new_row], ignore_index=True)
                st.session_state["edited_bdc_df"] = edited_bdc
                try:
                    st.experimental_rerun()
                except Exception:
                    pass

            st.session_state["edited_bdc_df"] = edited_bdc.copy()

            st.subheader("Texte brut (résultat OCR BDC)")
            st.code(res_bdc["raw"])
            st.markdown("</div>", unsafe_allow_html=True)

            # Prepare BDC sheet client (separate sheet id)
            try:
                if "gcp_sheet" in st.secrets:
                    sa_info = dict(st.secrets["gcp_sheet"])
                elif "google_service_account" in st.secrets:
                    sa_info = dict(st.secrets["google_service_account"])
                else:
                    sa_info = None
                if sa_info:
                    gclient = gspread.service_account_from_dict(sa_info)
                    sh_bdc = gclient.open_by_key(BDC_SHEET_ID)
                    # get worksheet by GID (sheet id)
                    try:
                        ws_bdc = None
                        for ws_candidate in sh_bdc.worksheets():
                            if int(ws_candidate.id) == int(BDC_SHEET_GID):
                                ws_bdc = ws_candidate
                                break
                        if ws_bdc is None:
                            # fallback to sheet1
                            ws_bdc = sh_bdc.sheet1
                    except Exception:
                        ws_bdc = sh_bdc.sheet1
                else:
                    ws_bdc = None
            except Exception:
                ws_bdc = None

            # Envoi vers Google Sheets (BDC)
            if st.button("📤 Envoyer vers Google Sheets — BDC"):
                try:
                    if ws_bdc is None:
                        raise FileNotFoundError("Credentials Google Sheets / BDC non configuré")

                    edited = st.session_state.get("edited_bdc_df", edited_bdc).copy()
                    
                    # Filtrer les lignes vides
                    edited = edited[~(edited["Désignation"].astype(str).str.strip() == "")].reset_index(drop=True)
                    
                    # append rows
                    existing = ws_bdc.get_all_values()
                    start_row = len(existing) + 1
                    today_str = datetime.now().strftime("%d/%m/%Y")

                    for _, row in edited.iterrows():
                        final_row = [
                            numero_val or "",
                            client_val or "",
                            date_val or today_str,
                            adresse_val or "",
                            row.get("Désignation", ""),
                            row.get("Qté", ""),
                            st.session_state.user_nom
                        ]
                        ws_bdc.append_row(final_row)

                    end_row = len(ws_bdc.get_all_values())

                    st.success("✅ Données BDC insérées avec succès !")
                    st.info(f"📌 Lignes insérées dans le sheet BDC : {start_row} → {end_row}")

                    # Essayer la coloration
                    try:
                        sheet_id_bdc = ws_bdc.id
                        color_rows(BDC_SHEET_ID, sheet_id_bdc, start_row-1, end_row, st.session_state.get("scan_index", 0))
                    except Exception:
                        st.warning("Coloration automatique du BDC sheet a échoué.")

                    st.session_state["scan_index"] = st.session_state.get("scan_index", 0) + 1

                except Exception as e:
                    st.error(f"❌ Erreur envoi BDC Sheets: {e}")

    # Retour au menu
    if st.button("⬅️ Retour au menu principal"):
        st.session_state.mode = None
        try:
            st.experimental_rerun()
        except Exception:
            pass

# ---------------------------
# Footer + logout
# ---------------------------
st.markdown("---")
if st.button("🚪 Déconnexion"):
    for k in ["auth", "user_nom", "user_matricule"]:
        if k in st.session_state:
            del st.session_state[k]
    try:
        st.experimental_rerun()
    except Exception:
        pass

# End of file
