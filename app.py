# app.py
# Chan Foui et Fils — OCR Facture PRO
# Option C — UI premium (fond clair, accents or & bleu pétrole)
# Requirements: streamlit, pillow, numpy, google-cloud-vision, gspread, google-api-python-client, google-auth, pandas

import streamlit as st
import numpy as np
import re
import os
import base64
from io import BytesIO
from datetime import datetime
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
LOGO_FILENAME = "CF_LOGOS.png"
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
# BDC sheet id
# ---------------------------
BDC_SHEET_ID = "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"

# ---------------------------
# Colors & theme
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
# Styles
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
    /* topbar / logo / card / buttons / inputs ... */  
    .topbar-wrapper {{ display:flex; justify-content:center; align-items:center; margin-bottom:18px; }}
    .topbar {{ display:flex; align-items:center; gap:18px; padding:12px 22px; border-radius:14px; background: linear-gradient(90deg, rgba(15,58,69,0.03), rgba(212,175,55,0.03)); box-shadow: 0 8px 30px rgba(15,58,69,0.04); }}
    .brand-title {{ font-family: Georgia, serif; font-size:30px; color: var(--petrol); margin:0; font-weight:700; text-align:center; }}
    .brand-sub {{ color: var(--muted); margin:0; font-size:13px; text-align:center; }}
    .logo-box {{ display:flex; align-items:center; justify-content:center; }}
    .card {{ border-radius:14px; background: var(--card); padding:18px; box-shadow: 0 10px 30px rgba(15,58,69,0.04); border: 1px solid rgba(15,58,69,0.03); transition: transform .12s ease, box-shadow .12s ease; margin-bottom:14px; }}
    .card:hover {{ transform: translateY(-4px); box-shadow: 0 18px 50px rgba(15,58,69,0.06); }}
    .stButton>button {{ background: linear-gradient(180deg, var(--gold), #b58f2d); color: #081214; font-weight:700; border-radius:10px; padding:8px 12px; box-shadow: 0 6px 18px rgba(212,175,55,0.12); }}
    .stTextInput>div>input, .stTextArea>div>textarea {{ border-radius:8px; padding:8px 10px; border:1px solid rgba(15,58,69,0.06); }}
    .muted-small {{ color: var(--muted); font-size:13px; }}
    .logo-round img {{ border-radius:8px; }}
    .highlight {{ color: var(--petrol); font-weight:700; }}
    @media (max-width: 640px) {{ .brand-title {{ font-size:20px; }} .topbar {{ padding:10px 12px; gap:10px; }} }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Helpers - OCR / preprocessing
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
    else:
        raise RuntimeError("Credentials Google Vision introuvables dans st.secrets [gcp_vision]")
    creds = SA_Credentials.from_service_account_info(sa_info)
    return vision.ImageAnnotatorClient(credentials=creds)

def google_vision_ocr(img_bytes: bytes) -> str:
    client = get_vision_client()
    image = vision.Image(content=img_bytes)
    response = client.text_detection(image=image)
    if response.error and response.error.message:
        raise Exception(f"Google Vision Error: {response.error.message}")
    return response.text_annotations[0].description if response.text_annotations else ""

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n").replace("\n ", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = text.replace("’", "'")
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

# ---------------------------
# Extraction helpers
# ---------------------------
def extract_invoice_number(text):
    patterns = [r"FACTURE\s+EN\s+COMPTE.*?N[°o]?\s*([0-9]{3,})", r"FACTURE.*?N[°o]\s*([0-9]{3,})", r"N°\s*([0-9]{3,})"]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m: return m.group(1).strip()
    return ""

def extract_delivery_address(text):
    m = re.search(r"Adresse de livraison\s*[:\-]?\s*(.+)", text, flags=re.I)
    if m: return m.group(1).strip().rstrip(".")
    return ""

def extract_doit(text):
    m = re.search(r"\bDOIT\s*[:\-]?\s*([A-Z0-9]{2,6})", text, flags=re.I)
    if m: return m.group(1).strip()
    for c in ["S2M", "ULYS", "DLP"]:
        if c in text: return c
    return ""

def extract_month(text):
    months = {"janvier":"Janvier","février":"Février","fevrier":"Février","mars":"Mars","avril":"Avril",
              "mai":"Mai","juin":"Juin","juillet":"Juillet","août":"Août","aout":"Août",
              "septembre":"Septembre","octobre":"Octobre",
              "novembre":"Novembre","décembre":"Décembre","decembre":"Décembre"}
    for mname in months:
        if re.search(r"\b" + re.escape(mname) + r"\b", text, flags=re.I): return months[mname]
    return ""

def extract_bon_commande(text):
    m = re.search(r"Suivant votre bon de commande\s*[:\-]?\s*([0-9A-Za-z\-\/]+)", text, flags=re.I)
    if m: return m.group(1).strip()
    return ""

def extract_items(text):
    items = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for l in lines:
        if re.search(r"(bon|commande|date|adresse|factur|client|total|montant)", l, flags=re.I): continue
        nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*|\d+)", l)
        if nums:
            last_num = nums[-1]
            n_clean = last_num.replace(" ", "").replace(",", "").replace(".", "")
            try: q = int(n_clean)
            except: q = 0
            esc_last = re.escape(last_num)
            article = re.sub(rf"{esc_last}\s*$", "", l).strip()
            if article == "": article = l
            items.append({"article": article, "quantite": q})
        else:
            items.append({"article": l, "quantite": 0})
    return [it for it in items if len(it["article"]) > 1 or it["quantite"] > 0]

# ---------------------------
# Pipelines
# ---------------------------
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

def bdc_pipeline(ocr_text):
    lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
    data = {"date_emission": "", "numero_bdc": "", "adresse_livraison": "", "adresse_facturation": "", "items": []}

    # Date et numéro BDC
    for l in lines:
        if "/" in l and len(l) <= 10: data["date_emission"] = l
        if l.isdigit() and len(l) >= 5: data["numero_bdc"] = l

    # Adresses
    start=False; adr_liv=[]
    for l in lines:
        if "Adresse livraison" in l: start=True; continue
        if start:
            if "Adresse facturation" in l: break
            adr_liv.append(l)
    data["adresse_livraison"] = "\n".join(adr_liv)

    start=False; adr_fac=[]
    for l in lines:
        if "Adresse facturation" in l: start=True; continue
        if start:
            if "Adresse fournisseur" in l: break
            adr_fac.append(l)
    data["adresse_facturation"] = "\n".join(adr_fac)

    # Items
    start=False
    for l in lines:
        if "Désignation" in l: start=True; continue
        if start:
            if "Horaire" in l or "Montant" in l: break
            if l.replace(",", "").replace(".", "").isdigit():
                if data["items"]: data["items"][-1]["quantite"] = int(l.replace(",", "").replace(".", ""))
            else:
                data["items"].append({"article": l, "quantite": 0})
    return data

# ---------------------------
# Sheets helpers
# ---------------------------
def _get_sheet_id():
    if "settings" in st.secrets and "sheet_id" in st.secrets["settings"]: return st.secrets["settings"]["sheet_id"]
    if "SHEET_ID" in st.secrets: return st.secrets["SHEET_ID"]
    raise KeyError("Mettez 'sheet_id' dans st.secrets['settings'] ou 'SHEET_ID'")

def get_worksheet():
    if "gcp_sheet" in st.secrets: sa_info=dict(st.secrets["gcp_sheet"])
    else: raise FileNotFoundError("Credentials Google Sheets introuvables")
    client = gspread.service_account_from_dict(sa_info)
    sheet_id = _get_sheet_id()
    sh = client.open_by_key(sheet_id)
    return sh.sheet1

def get_sheets_service():
    if "gcp_sheet" in st.secrets: sa_info=dict(st.secrets["gcp_sheet"])
    creds = SA_Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds)

def color_rows(spreadsheet_id, sheet_id, start, end, scan_index):
    service = get_sheets_service()
    if scan_index %2 == 0: bg, text_color = SHEET_COLOR_DEFAULT, TEXT_COLOR_BLACK
    else: bg, text_color = SHEET_COLOR_THEME, TEXT_COLOR_WHITE
    body = {"requests":[{"repeatCell":{"range":{"sheetId":sheet_id,"startRowIndex":start,"endRowIndex":end},"cell":{"userEnteredFormat":{"backgroundColor":bg,"textFormat":{"foregroundColor":text_color}}},"fields":"userEnteredFormat(backgroundColor,textFormat)"}}]}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

# ---------------------------
# Session init
# ---------------------------
if "scan_index" not in st.session_state: st.session_state.scan_index = int(st.secrets.get("SCAN_STATE", {}).get("scan_index",0))

# ---------------------------
# Header
# ---------------------------
def _img_to_base64(img: Image.Image) -> str:
    buf = BytesIO(); img.save(buf, format="PNG"); return base64.b64encode(buf.getvalue()).decode("utf-8")

def render_header():
    st.markdown("<div class='topbar-wrapper'>", unsafe_allow_html=True)
    if os.path.exists(LOGO_FILENAME):
        try:
            logo = Image.open(LOGO_FILENAME).convert("RGBA")
            b64 = _img_to_base64(logo)
            st.markdown(
                "<div class='topbar'>"
                f"<div class='logo-box'><img src='data:image/png;base64,{b64}' width='84'/></div>"
                f"<div style='display:flex;flex-direction:column;justify-content:center;'>"
                f"<h1 class='brand-title'>{BRAND_TITLE}</h1><div class='brand-sub'>{BRAND_SUB}</div>"
                "</div></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            return
        except: pass
    st.markdown(
        "<div class='topbar'><div style='text-align:center;width:100%;'><h1 class='brand-title'>{BRAND_TITLE}</h1><div class='brand-sub'>{BRAND_SUB}</div></div></div>",
        unsafe_allow_html=True)
render_header()
