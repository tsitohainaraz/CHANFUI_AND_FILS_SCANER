# app_updated.py
# Chan Foui et Fils — OCR Facture PRO (UI premium, centered header)
# Updated by assistant: center header, improve typography, keep backend unchanged

import streamlit as st
import numpy as np
import re
import time
import os
import json
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
# Colors & sheet row colors (keep for Sheets color_rows)
# ---------------------------
PALETTE = {
    "petrol":"#0F3A45",
    "gold":"#D4AF37",
    "ivory":"#FAF5EA",
    "muted":"#7a8a8f",
    "card":"#ffffff",
    "soft":"#f6f2ec"
}

COLORS = [
    {"red": 0.07, "green": 0.06, "blue": 0.06},
    {"red": 0.83, "green": 0.72, "blue": 0.45},
    {"red": 0.88, "green": 0.84, "blue": 0.78},
]

# ---------------------------
# Styles (premium, animations, centered header)
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

    /* header - centered */
    .topbar-wrapper {{ display:flex; justify-content:center; }}
    .topbar {{
        display:flex;
        align-items:center;
        gap:18px;
        padding:12px 18px;
        border-radius:12px;
        background: linear-gradient(90deg, rgba(15,58,69,0.03), rgba(212,175,55,0.02));
        box-shadow: 0 6px 22px rgba(15,58,69,0.06);
        margin-bottom:16px;
        max-width:920px;
        width:100%;
    }}
    .brand-left {{ display:flex; align-items:center; gap:14px; justify-content:center; width:100%; }}
    .brand-title {{
        font-family: Georgia, serif;
        font-size:28px;
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

    /* card */
    .card {{
        border-radius:14px;
        background: var(--card);
        padding:16px;
        box-shadow: 0 8px 30px rgba(15,58,69,0.04);
        border: 1px solid rgba(15,58,69,0.04);
        transition: transform .18s ease, box-shadow .18s ease;
        max-width:920px;
        margin:auto;
    }}
    .card:hover {{ transform: translateY(-6px); box-shadow: 0 14px 40px rgba(15,58,69,0.06); }}

    /* buttons */
    .stButton>button {{
        background: linear-gradient(180deg, var(--gold), #b58f2d);
        color: #081214;
        font-weight:700;
        border-radius:10px;
        padding:8px 12px;
        box-shadow: 0 6px 18px rgba(212,175,55,0.18);
    }}

    .muted-small {{ color: var(--muted); font-size:13px; text-align:center; }}
    .logo-round {{ border-radius:10px; display:block; margin:auto; }}
    .highlight {{ color: var(--petrol); font-weight:700; }}

    @keyframes shimmer {{
      0% {{ background-position: -200% 0; }}
      100% {{ background-position: 200% 0; }}
    }}
    .shimmer {{
      background: linear-gradient(90deg, rgba(212,175,55,0.06), rgba(15,58,69,0.03), rgba(212,175,55,0.06));
      background-size: 200% 100%;
      animation: shimmer 4s linear infinite;
      border-radius: 8px;
      padding:6px;
    }}

    /* small screens */
    @media (max-width: 640px) {{
        .brand-title {{ font-size:20px; }}
        .topbar {{ padding:10px; gap:10px; }}
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

def color_rows(spreadsheet_id, sheet_id, start, end, color):
    service = get_sheets_service()
    body = {
        "requests":[
            {
                "repeatCell":{
                    "range":{
                        "sheetId":sheet_id,
                        "startRowIndex":start,
                        "endRowIndex":end
                    },
                    "cell":{"userEnteredFormat":{"backgroundColor":color}},
                    "fields":"userEnteredFormat.backgroundColor"
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

# ---------------------------
# Session init
# ---------------------------
if "scan_index" not in st.session_state:
    try:
        st.session_state.scan_index = int(st.secrets.get("SCAN_STATE", {}).get("scan_index", 0))
    except Exception:
        st.session_state.scan_index = 0

# ---------------------------
# Header rendering (logo + centered title)
# ---------------------------
def render_header():
    st.markdown("<div class='topbar-wrapper'>", unsafe_allow_html=True)
    if os.path.exists(LOGO_FILENAME):
        try:
            logo = Image.open(LOGO_FILENAME).convert("RGBA")
            # show logo + title centered
            logo_html = f"<div style='text-align:center;width:120px'><img src='data:image/png;base64,{st.image(logo, use_column_width=False)}' class='logo-round' style='width:84px;height:auto;display:block;margin:auto'/></div>"
            # Note: st.image() already renders the image; we'll render layout using columns instead
            cols = st.columns([1,6,1])
            with cols[0]:
                st.write("")
            with cols[1]:
                # show centered stack: logo above title
                if os.path.exists(LOGO_FILENAME):
                    st.image(logo, width=96)
                st.markdown(f"<div class='topbar'><div class='brand-left'><div><h2 class='brand-title'>{BRAND_TITLE}</h2><div class='brand-sub'>{BRAND_SUB}</div></div></div></div>", unsafe_allow_html=True)
            with cols[2]:
                st.write("")
        except Exception:
            st.markdown(f"<div class='topbar'><div class='brand-left'><div><h2 class='brand-title'>{BRAND_TITLE}</h2><div class='brand-sub'>{BRAND_SUB}</div></div></div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='topbar'><div class='brand-left'><div><h2 class='brand-title'>{BRAND_TITLE}</h2><div class='brand-sub'>{BRAND_SUB}</div></div></div></div>", unsafe_allow_html=True)
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
            st.success(f"Connexion OK — Bienvenue {st.session_state.user_nom}")
            try:
                st.experimental_rerun()
            except Exception:
                pass
        else:
            st.error("Accès refusé — Nom ou matricule invalide")
    st.markdown("</div>", unsafe_allow_html=True)

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    login_block()
    st.stop()

# ---------------------------
# Main UI - Upload and OCR
# ---------------------------
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center'>📥 Importer une facture</h3>", unsafe_allow_html=True)
st.markdown("<div class='muted-small'>Formats acceptés: jpg, jpeg, png — qualité recommandée: photo nette</div>", unsafe_allow_html=True)
uploaded = st.file_uploader("", type=["jpg","jpeg","png"], key="uploader")
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
    st.image(img, caption="Aperçu", use_container_width=True)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    st.info("Traitement OCR Google Vision...")
    p = st.progress(8)
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
    if "article" not in df_articles.columns:
        df_articles["article"] = ""
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
# ENVOI -> Google Sheets
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

            start_row = len(ws.get_all_values()) + 1
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

            color = COLORS[st.session_state.get("scan_index", 0) % len(COLORS)]
            if spreadsheet_id and sheet_id is not None:
                color_rows(spreadsheet_id, sheet_id, start_row-1, end_row, color)

            st.session_state["scan_index"] = st.session_state.get("scan_index", 0) + 1

            st.success("✅ Donn\u00e9es ins\u00e9r\u00e9es avec succ\u00e8s !")
            st.info(f"📌 Lignes ins\u00e9r\u00e9es dans le sheet : {start_row} → {end_row}")
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

# ---------------------------
# Aperçu du Google Sheet
# ---------------------------
if ws:
    if st.button("👀 Aperçu du Google Sheet"):
        try:
            records = ws.get_all_records()
            df_sheet = pd.DataFrame(records)
            if df_sheet.shape[0] > 200:
                st.warning("⚠ Le sheet contient plus de 200 lignes — affichage des 200 premières lignes.")
                st.dataframe(df_sheet.head(200), use_container_width=True)
            else:
                st.dataframe(df_sheet, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur lors du chargement du sheet : {e}")

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

