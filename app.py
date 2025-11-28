# app.py
# Chan Foui et Fils — OCR Facture PRO
# Option C — UI premium + animations (fond clair, accents or & bleu pétrole)
# Requirements: streamlit, pillow, numpy, google-cloud-vision, gspread, google-api-python-client, google-auth, pandas

import streamlit as st
import re
import time
import os
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
    initial_sidebar_state="collapsed",
)

# ---------------------------
# Vars / Auth
# ---------------------------
LOGO_FILENAME = "CF_LOGOS.png"
BRAND_TITLE = "Chan Foui et Fils"
BRAND_SUB = "Google Vision — Edition Premium"

AUTHORIZED_USERS = {
    "DIRECTION": "CFF10",
    "COMERCIALE": "CFF11",
    "STOCK": "CFF12",
    "AUTRES": "CFF13"
}

# Colors palette
PALETTE = {
    "petrol": "#0F3A45",   # for UI / sheet alternate color
    "gold": "#D4AF37",
    "ivory": "#FAF5EA",
    "muted": "#7a8a8f",
    "card": "#ffffff",
    "soft": "#f6f2ec"
}

# Sheets alternating colors (Option 1): White <-> Petrol
SHEET_COLORS = [
    {"red": 1.0, "green": 1.0, "blue": 1.0},  # white
    {"red": 15/255, "green": 58/255, "blue": 69/255}  # petrol from hex #0F3A45
]

# ---------------------------
# Lightweight styling (centered header, premium)
# ---------------------------
st.markdown(
    f"""
    <style>
    :root{{ --petrol: {PALETTE['petrol']}; --gold: {PALETTE['gold']}; --ivory: {PALETTE['ivory']}; --muted: {PALETTE['muted']}; --card: {PALETTE['card']}; --soft: {PALETTE['soft']}; }}
    html, body, [data-testid='stAppViewContainer'] {{
        background: linear-gradient(180deg, var(--ivory), #fffdf9);
        color: var(--petrol);
        font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }}
    .topbar-wrapper {{ display:flex; justify-content:center; margin-bottom:12px; }}
    .topbar {{
        display:flex; align-items:center; gap:18px; padding:12px 20px; border-radius:14px;
        background: linear-gradient(90deg, rgba(15,58,69,0.03), rgba(212,175,55,0.02));
        box-shadow: 0 6px 22px rgba(15,58,69,0.05); max-width:980px; width:100%;
    }}
    .brand-title {{ font-family: Georgia, serif; font-size:28px; color:var(--petrol); margin:0; font-weight:700; text-align:center; }}
    .brand-sub {{ color:var(--muted); margin:0; font-size:13px; text-align:center; }}
    .card {{ border-radius:14px; background:var(--card); padding:16px; box-shadow:0 8px 30px rgba(15,58,69,0.04); border:1px solid rgba(15,58,69,0.04); max-width:920px; margin:auto 0 16px; }}
    .stButton>button {{ background: linear-gradient(180deg, var(--gold), #b58f2d); color:#081214; font-weight:700; border-radius:10px; padding:8px 12px; box-shadow:0 6px 18px rgba(212,175,55,0.18); }}
    .muted-small {{ color:var(--muted); font-size:13px; text-align:center; }}
    .logo-round {{ border-radius:10px; display:block; margin:auto; }}
    @media (max-width:640px) {{ .brand-title{{ font-size:20px }} .topbar{{ padding:10px; gap:10px }} }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# Helpers: Vision, preprocess, extraction (kept minimal & fast)
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

# cache the vision client resource to avoid re-creating repeatedly
@st.cache_resource
def get_vision_client_from_secrets():
    if "gcp_vision" in st.secrets:
        info = dict(st.secrets["gcp_vision"])
    elif "google_service_account" in st.secrets:
        info = dict(st.secrets["google_service_account"])
    else:
        raise RuntimeError("Credentials Google Vision introuvables dans st.secrets (ajoute [gcp_vision])")
    creds = SA_Credentials.from_service_account_info(info)
    return vision.ImageAnnotatorClient(credentials=creds)

def google_vision_ocr(img_bytes: bytes) -> str:
    client = get_vision_client_from_secrets()
    image = vision.Image(content=img_bytes)
    response = client.text_detection(image=image)
    if response.error and response.error.message:
        raise Exception(f"Google Vision Error: {response.error.message}")
    if response.text_annotations:
        return response.text_annotations[0].description or ""
    return ""

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\n ", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = text.replace("’", "'")
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

# Extraction helpers (kept as in working backend)
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
    return m.group(1) if m else ""

def extract_delivery_address(text):
    p = r"Adresse de livraison\s*[:\-]\s*(.+)"
    m = re.search(p, text, flags=re.I)
    if m:
        return m.group(1).strip().rstrip(".")
    p2 = r"Adresse(?:\s+de\s+livraison)?\s*[:\-]?\s*\n?\s*(.+)"
    m2 = re.search(p2, text, flags=re.I)
    return m2.group(1).strip().split("\n")[0] if m2 else ""

def extract_doit(text):
    p = r"\bDOIT\s*[:\-]?\s*([A-Z0-9]{2,6})"
    m = re.search(p, text, flags=re.I)
    if m:
        return m.group(1).strip()
    for c in ["S2M", "ULYS", "DLP"]:
        if c in text:
            return c
    return ""

def extract_month(text):
    months = {
        "janvier":"Janvier","février":"Février","fevrier":"Février","mars":"Mars","avril":"Avril",
        "mai":"Mai","juin":"Juin","juillet":"Juillet","août":"Août","aout":"Août",
        "septembre":"Septembre","octobre":"Octobre","novembre":"Novembre","décembre":"Décembre","decembre":"Décembre"
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
    return (m2.group(1).strip().split()[0]) if m2 else ""

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
    # progress handled in UI wrapper, keep this function focused
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
# Google Sheets helpers
# ---------------------------
def _get_sheet_id():
    if "settings" in st.secrets and "sheet_id" in st.secrets["settings"]:
        return st.secrets["settings"]["sheet_id"]
    if "SHEET_ID" in st.secrets:
        return st.secrets["SHEET_ID"]
    raise KeyError("Mettez 'sheet_id' dans st.secrets['settings'] ou 'SHEET_ID' dans st.secrets")

def get_worksheet():
    # returns gspread worksheet or raises
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

@st.cache_resource
def get_sheets_service_from_secrets():
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise FileNotFoundError("Credentials Google Sheets introuvables dans st.secrets")
    creds = SA_Credentials.from_service_account_info(sa_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds)

def color_rows(spreadsheet_id, sheet_id, start, end, color):
    service = get_sheets_service_from_secrets()
    body = {
        "requests":[
            {
                "repeatCell":{
                    "range":{
                        "sheetId": sheet_id,
                        "startRowIndex": start,
                        "endRowIndex": end
                    },
                    "cell": {"userEnteredFormat": {"backgroundColor": color}},
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

# ---------------------------
# Session & scan index (two-state toggler)
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
    # centered layout via columns
    cols = st.columns([1, 6, 1])
    with cols[1]:
        st.markdown("<div class='topbar'>", unsafe_allow_html=True)
        if os.path.exists(LOGO_FILENAME):
            try:
                logo = Image.open(LOGO_FILENAME).convert("RGBA")
                st.image(logo, width=92, use_column_width=False)
            except Exception:
                pass
        st.markdown(f"<div style='margin-left:8px'><h2 class='brand-title'>{BRAND_TITLE}</h2><div class='brand-sub'>{BRAND_SUB}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

render_header()

# ---------------------------
# Simple auth UI
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
# Upload + OCR UI (with progress)
# ---------------------------
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center'>📥 Importer une facture</h3>", unsafe_allow_html=True)
st.markdown("<div class='muted-small'>Formats acceptés: jpg, jpeg, png — photo nette recommandée</div>", unsafe_allow_html=True)
uploaded = st.file_uploader("", type=["jpg","jpeg","png"], key="uploader")
st.markdown("</div>", unsafe_allow_html=True)

img = None
if uploaded:
    try:
        img = Image.open(uploaded)
    except Exception as e:
        st.error("Image non lisible : " + str(e))

if "edited_articles_df" not in st.session_state:
    st.session_state["edited_articles_df"] = None

if img:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.image(img, caption="Aperçu", use_column_width=True)
    buf = BytesIO(); img.save(buf, format="JPEG"); img_bytes = buf.getvalue()

    # progress bar restore: show meaningful steps
    p = st.progress(5)
    try:
        p.progress(15)
        # small debounce to make UX visible
        time.sleep(0.06)
        p.progress(35)
        res = invoice_pipeline(img_bytes)
        p.progress(80)
        time.sleep(0.05)
        p.progress(100)
    except Exception as e:
        p.empty()
        st.error(f"Erreur OCR: {e}")
        st.stop()
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

    # Articles editor
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    detected_articles = res.get("articles", []) or [{"article": "", "bouteilles": 0}]
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
        try: st.experimental_rerun()
        except Exception: pass

    st.session_state["edited_articles_df"] = edited_df.copy()
    st.subheader("Texte brut (résultat OCR)")
    st.code(res["raw"])
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Prepare worksheet (non-blocking)
# ---------------------------
try:
    ws = get_worksheet()
    sheet_gid = ws.id
    spreadsheet_id = _get_sheet_id()
except Exception:
    ws = None
    sheet_gid = None
    spreadsheet_id = None

# ---------------------------
# Send to Google Sheets (no preview button)
# ---------------------------
if img and st.session_state.get("edited_articles_df") is not None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    if ws is None:
        st.info("Google Sheets non configuré ou credentials manquants — vérifie .streamlit/secrets.toml")
        st.markdown("<div class='muted-small'>Astuce: mets [gcp_sheet] et [gcp_vision] et [settings] avec sheet_id dans .streamlit/secrets.toml</div>", unsafe_allow_html=True)
    if ws and st.button("📤 Envoyer vers Google Sheets"):
        try:
            edited = st.session_state["edited_articles_df"].copy()
            # drop empty lines
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

            # alternate only between two states (white <-> petrol)
            idx = st.session_state.get("scan_index", 0) % 2
            color = SHEET_COLORS[idx]
            if spreadsheet_id and sheet_gid is not None:
                color_rows(spreadsheet_id, sheet_gid, start_row-1, end_row, color)

            # flip state (0->1->0->1)
            st.session_state["scan_index"] = (st.session_state.get("scan_index", 0) + 1) % 2

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

# ---------------------------
# Footer + logout
# ---------------------------
st.markdown("---")
if st.button("🚪 Déconnexion"):
    for k in ["auth", "user_nom", "user_matricule"]:
        if k in st.session_state:
            del st.session_state[k]
    try: st.experimental_rerun()
    except Exception: pass
