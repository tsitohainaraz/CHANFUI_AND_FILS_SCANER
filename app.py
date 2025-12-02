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
# Petrol #0F3A45 -> (15,58,69) /255
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

def extract_items(text):
    items = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    pattern = re.compile(r"(.+?(?:75\s*cls?|75\s*cl|75cl|75))\s+\d+\s+\d+\s+(\d+)", flags=re.I)
    for l in lines:
        m = pattern.search(l)
        if m:
            name = m.group(1).strip()
            nb_btls = int(m.group(2))
            name = re.sub(r"\s{2,}", " ", name)
            items.append({"article": name, "bouteilles": nb_btls})
    if not items:
        for l in lines:
            if "75" in l or "cls" in l.lower():
                nums = re.findall(r"(\d{1,4})", l)
                if nums:
                    nb_btls = int(nums[-1])
                    name = re.sub(r"\d+", "", l).strip()
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
        "articles": extract_items(raw)
    }

# ---------------------------
# BDC pipeline (séparé pour modifications futures)
# ---------------------------
def bdc_pipeline(image_bytes: bytes):
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)

    # Champs placeholders — tu pourras ajouter des extracteurs spécifiques
    numero = ""   # ex: extract_bdc_number(raw)
    client = ""   # ex: extract_bdc_client(raw)
    date = ""     # ex: extract_bdc_date(raw)

    return {
        "raw": raw,
        "numero": numero,
        "client": client,
        "date": date,
        "articles": extract_items(raw)
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
    # color is dict floats; if theme -> white text, if white -> black text
    if color == SHEET_COLOR_THEME:
        return TEXT_COLOR_WHITE
    return TEXT_COLOR_BLACK

def color_rows(spreadsheet_id, sheet_id, start, end, scan_index):
    """
    Coloration PAR FACTURE (par opération d’envoi).
    - Toutes les lignes envoyées en une seule fois = même couleur
    - Alternance : blanc → bleu pétrole → blanc → bleu pétrole → ...
    - start / end : index 0-based (end exclus)
    """

    service = get_sheets_service()

    # --- Choix de couleur basé sur l'index du scan ---
    if scan_index % 2 == 0:
        bg = SHEET_COLOR_DEFAULT      # Blanc
        text_color = TEXT_COLOR_BLACK
    else:
        bg = SHEET_COLOR_THEME        # Bleu pétrole
        text_color = TEXT_COLOR_WHITE

    # --- Construire la requête unique pour colorer tout le bloc ---
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

    # --- Exécuter la coloration dans Google Sheets ---
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

            # --- SUCCESS premium petrol ---
            st.markdown(
                f"""
                <div style="
                    background-color: #0F3A45;
                    padding: 12px 16px;
                    border-radius: 8px;
                    color: white;
                    font-weight: 600;
                    text-align: c
