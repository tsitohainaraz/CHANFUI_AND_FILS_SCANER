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
# AUTH
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
# Colors & sheet row colors
# ---------------------------
PALETTE = {
    "petrol": "#0F3A45",
    "gold": "#D4AF37",
    "ivory": "#FAF5EA",
    "muted": "#7a8a8f",
    "card": "#ffffff",
    "soft": "#f6f2ec"
}

SHEET_COLOR_THEME = {"red": 15/255.0, "green": 58/255.0, "blue": 69/255.0}
SHEET_COLOR_DEFAULT = {"red": 1.0, "green": 1.0, "blue": 1.0}
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
    .logo-box {{
        display:flex;
        align-items:center;
        justify-content:center;
    }}
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
    .stButton>button {{
        background: linear-gradient(180deg, var(--gold), #b58f2d);
        color: #081214;
        font-weight:700;
        border-radius:10px;
        padding:8px 12px;
        box-shadow: 0 6px 18px rgba(212,175,55,0.12);
    }}
    .stTextInput>div>input, .stTextArea>div>textarea {{
        border-radius:8px;
        padding:8px 10px;
        border:1px solid rgba(15,58,69,0.06);
    }}
    .muted-small {{ color: var(--muted); font-size:13px; }}
    .logo-round img {{ border-radius:8px; }}
    .highlight {{ color: var(--petrol); font-weight:700; }}
    @media (max-width: 640px) {{
        .brand-title {{ font-size:20px; }}
        .topbar {{ padding:10px 12px; gap:10px; }}
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Helpers: preprocess / OCR / extraction
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
        raise RuntimeError("Credentials Google Vision introuvables")
    creds = SA_Credentials.from_service_account_info(sa_info)
    client = vision.ImageAnnotatorClient(credentials=creds)
    return client

def google_vision_ocr(img_bytes: bytes) -> str:
    client = get_vision_client()
    image = vision.Image(content=img_bytes)
    response = client.text_detection(image=image)
    if response.error and response.error.message:
        raise Exception(f"Google Vision Error: {response.error.message}")
    return response.text_annotations[0].description if response.text_annotations else ""

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\n ", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = text.replace("’", "'")
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

def extract_items(text):
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
            except:
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

# ---------------------------
# BDC pipeline (optimisé)
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
    return m2.group(1) if m2 else ""

def extract_bdc_date(text: str) -> str:
    m = re.search(r"(\d{1,2}\s*[\/\-]\s*\d{1,2}\s*[\/\-]\s*\d{2,4})", text)
    if m:
        parts = re.split(r"[\/\-]", re.sub(r"\s+", "", m.group(1)))
        if len(parts) == 3:
            day = parts[0].zfill(2)
            mon = parts[1].zfill(2)
            year = "20" + parts[2] if len(parts[2]) == 2 else parts[2]
            return f"{day}/{mon}/{year}"
    return ""

def extract_bdc_client(text: str) -> str:
    m = re.search(r"Adresse\s*(?:facturation|facture)\s*[:\-]?\s*(.+)", text, flags=re.I)
    if m:
        return m.group(1).split("\n")[0].strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for l in lines[:6]:
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
        "articles": extract_items(raw)
    }

# ---------------------------
# Google Sheets helpers
# ---------------------------
def _get_sheet_id():
    if "settings" in st.secrets and "sheet_id" in st.secrets["settings"]:
        return st.secrets["settings"]["sheet_id"]
    if "SHEET_ID" in st.secrets:
        return st.secrets["SHEET_ID"]
    raise KeyError("Mettez 'sheet_id' dans st.secrets")

def get_worksheet():
    sa_info = dict(st.secrets.get("gcp_sheet") or st.secrets.get("google_service_account") or {})
    client = gspread.service_account_from_dict(sa_info)
    sh = client.open_by_key(_get_sheet_id())
    return sh.sheet1

def get_sheets_service():
    sa_info = dict(st.secrets.get("gcp_sheet") or st.secrets.get("google_service_account") or {})
    creds = SA_Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    service = build("sheets", "v4", credentials=creds)
    return service

def _sheet_text_color_for_bg(color):
    return TEXT_COLOR_WHITE if color == SHEET_COLOR_THEME else TEXT_COLOR_BLACK

def color_rows(spreadsheet_id, sheet_id, start, end, scan_index):
    service = get_sheets_service()
    bg = SHEET_COLOR_DEFAULT if scan_index % 2 == 0 else SHEET_COLOR_THEME
    text_color = _sheet_text_color_for_bg(bg)
    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": start, "endRowIndex": end},
                    "cell": {"userEnteredFormat": {"backgroundColor": bg, "textFormat": {"foregroundColor": text_color}}},
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

# ---------------------------
# Session init
# ---------------------------
if "scan_index" not in st.session_state:
    st.session_state.scan_index = int(st.secrets.get("SCAN_STATE", {}).get("scan_index", 0) or 0)

def _img_to_base64(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def render_header():
    st.markdown("<div class='topbar-wrapper'>", unsafe_allow_html=True)
    if os.path.exists(LOGO_FILENAME):
        logo = Image.open(LOGO_FILENAME).convert("RGBA")
        b64 = _img_to_base64(logo)
        st.markdown(
            "<div class='topbar'>"
            f"<div class='logo-box'><img src='data:image/png;base64,{b64}' width='84'/></div>"
            f"<div style='display:flex;flex-direction:column;justify-content:center;'>"
            f"<h1 class='brand-title'>{BRAND_TITLE}</h1>"
            f"<div class='brand-sub'>{BRAND_SUB}</div>"
            f"</div></div>", unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

render_header()

# ---------------------------
# Login UI
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
            st.success(f"Bienvenue {st.session_state.user_nom}")
            st.experimental_rerun()
        else:
            st.error("Nom ou matricule invalide")
    st.markdown("</div>", unsafe_allow_html=True)

if "auth" not in st.session_state:
    st.session_state.auth = False
if not st.session_state.auth:
    login_block()
    st.stop()

# ---------------------------
# Mode selection (Facture / BDC)
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
# FACTURE mode (inchangé)
# ---------------------------
# ... (le code facture reste exactement comme dans ton ancien code) ...

# ---------------------------
# BDC mode (optimisé)
# ---------------------------
if st.session_state.mode == "bdc":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center'>📝 Importer un Bon de commande</h3>", unsafe_allow_html=True)
    st.markdown("<div class='muted-small'>Formats acceptés: jpg, jpeg, png — photo nette</div>", unsafe_allow_html=True)
    uploaded_bdc = st.file_uploader("", type=["jpg","jpeg","png"], key="bdc_upload")
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_bdc is not None:
        bdc_data = bdc_pipeline(uploaded_bdc.read())
        st.success("✅ Extraction terminée")

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<h4>Numéro BDC: <span class='highlight'>{bdc_data['numero']}</span></h4>", unsafe_allow_html=True)
        st.markdown(f"<h4>Client: <span class='highlight'>{bdc_data['client']}</span></h4>", unsafe_allow_html=True)
        st.markdown(f"<h4>Date: <span class='highlight'>{bdc_data['date']}</span></h4>", unsafe_allow_html=True)
        st.markdown(f"<h4>Adresse Livraison: <span class='highlight'>{bdc_data['adresse_livraison']}</span></h4>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if bdc_data["articles"]:
            df_items = pd.DataFrame(bdc_data["articles"])
            edited_df = st.data_editor(df_items, num_rows="dynamic")
        else:
            edited_df = st.data_editor(pd.DataFrame(columns=["article","quantite"]), num_rows="dynamic")

        if st.button("📤 Envoyer vers Google Sheets"):
            ws = get_worksheet()
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            for idx, row in edited_df.iterrows():
                ws.append_row([
                    now,
                    bdc_data["numero"],
                    bdc_data["client"],
                    bdc_data["date"],
                    bdc_data["adresse_livraison"],
                    row["article"],
                    row["quantite"]
                ])
            st.success("✅ BDC envoyé avec succès à Google Sheets !")
