# ==========================================
# CHAN FOUI & FILS — APPLICATION OCR PRO
# MODULE : FACTURE + BON DE COMMANDE
# DESIGN : PREMIUM (OR + BLEU PÉTROLE)
# ==========================================

import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import base64
from datetime import datetime
from google.cloud import vision
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==========================================
# GOOGLE SHEET CONFIGURATION
# ==========================================
SPREADSHEET_ID = "1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE"

# Feuille FACTURE
SHEET_ID_FACTURE = 72936741

# Feuille BON DE COMMANDE
SHEET_ID_BDC = 1487110894


# ==========================================
# LOAD GOOGLE CREDENTIALS
# ==========================================
@st.cache_resource
def load_credentials():
    return service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])


# ==========================================
# GOOGLE SHEETS SERVICE
# ==========================================
def get_sheets():
    creds = load_credentials()
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()


# ==========================================
# CSS PREMIUM OR + BLEU PÉTROLE
# ==========================================
st.markdown("""
<style>
body {
    background-color: #F6F7FB;
    font-family: 'Inter', sans-serif;
}
.block {
    background-color: white;
    padding: 18px 25px;
    border-radius: 12px;
    margin-bottom: 22px;
    border-left: 6px solid #004A59;
    box-shadow: 0px 3px 12px rgba(0,0,0,0.08);
}
.block-title {
    font-size: 19px;
    font-weight: 700;
    color: #004A59;
    margin-bottom: 6px;
}
.btn-main {
    background-color: #004A59;
    color: white !important;
    padding: 8px 18px;
    border-radius: 10px;
}
h1, h2 {
    color: #004A59;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# LOGIN
# ==========================================
def login_section():
    st.title("CHAN FOUI — OCR PRO")
    st.subheader("Connexion utilisateur")

    user = st.text_input("Nom d'utilisateur")
    pwd = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter", use_container_width=True):
        if user == "admin" and pwd == "admin":
            st.session_state["logged"] = True
            st.experimental_rerun()
        else:
            st.error("Identifiants incorrects.")


# ==========================================
# HELPER : GOOGLE VISION OCR
# ==========================================
def run_ocr(image_bytes):
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    if response.text_annotations:
        return response.text_annotations[0].description
    return ""
# ==========================================
# BLOC 2 — PREPROCESS, OCR HELPERS, EXTRACTION (FACTURE)
# ==========================================

from io import BytesIO
from PIL import Image, ImageFilter, ImageOps
import gspread

# ---------------------------
# Image preprocessing (optimisation pour OCR)
# ---------------------------
def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Resize, autocontrast, denoise, unsharp mask -> return JPEG bytes optimized for Vision OCR.
    """
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

# ---------------------------
# Vision client helper (uses service account loaded earlier via st.secrets)
# ---------------------------
@st.cache_resource
def get_vision_client():
    # We expect the service account JSON in st.secrets["gcp_service_account"]
    creds = load_credentials()
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

# ---------------------------
# Text cleaning helper
# ---------------------------
def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\n ", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    text = text.replace("’", "'")
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()

# ---------------------------
# Extraction helpers (Facture)
# ---------------------------
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

# ---------------------------
# Robust item extractor (used by both Facture & BDC)
# ---------------------------
def extract_items(text):
    """
    Retourne une liste de dicts: {"article": str, "quantite": int}
    """
    items = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for l in lines:
        # skip header-like lines
        if re.search(r"(bon|commande|date|adresse|factur|client|total|montant|désignation)", l, flags=re.I):
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
    # filter trivial rows
    clean_items = []
    for it in items:
        if len(it["article"]) < 2 and it["quantite"] == 0:
            continue
        clean_items.append(it)
    return clean_items

# ---------------------------
# Invoice pipeline (unchanged behavior)
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
# ==========================================
# BLOC 3 — PIPELINE BON DE COMMANDE (BDC) — EXTRACTION PREMIUM
# ==========================================

# NOTE:
# - Utilise preprocess_image(), google_vision_ocr(), clean_text(), extract_items() du Bloc 2.
# - Retourne un dict structuré prêt pour l'UI et l'export Sheets.

def extract_bdc_number(text: str) -> str:
    """
    Cherche les motifs courants du numéro de bon de commande.
    Exemples trouvés dans tes documents : "n° 25011956", "251033", "Bon de commande n° 25011956"
    """
    patterns = [
        r"\b[nN][°º]?\s*[:\-]?\s*([0-9]{5,9})\b",               # n° 25011956
        r"\bBon\s+de\s+commande\s*(?:N[°º]?|:)?\s*([0-9A-Za-z\-\/]+)\b",
        r"\bNum(?:éro|ero)?\s*(?:BDC|bon)?\s*[:\-]?\s*([0-9A-Za-z\-\/]{4,12})\b",
        r"\b([0-9]{5,9})\b"                                     # fallback any 5-9 digit block
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1).strip()
    return ""

def extract_bdc_date(text: str) -> str:
    """
    Recherche les dates au format DD/MM/YY(YY) ou variantes avec espaces.
    Retourne une date normalisée en DD/MM/YYYY si possible.
    """
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
    # cas "date émission A livrer le\n04/11/2025\n07/11/2025" -> prefer first dd/mm/yyyy found
    m2 = re.search(r"\b(\d{2}\/\d{2}\/\d{4})\b", text)
    if m2:
        return m2.group(1)
    return ""

def extract_bdc_client(text: str) -> str:
    """
    Tente d'extraire le bloc 'Adresse facturation' ou le nom client proche du header.
    """
    m = re.search(r"Adresse\s+facturation\s*[:\-]?\s*(.+?)(?:\n[A-Z]|$)", text, flags=re.I | re.S)
    if m:
        # récupère la première ligne utile
        val = m.group(1).strip().split("\n")[0].strip()
        return val
    # fallback: look for capitalized company-like lines after header
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, l in enumerate(lines[:12]):  # chercher dans les premières lignes
        if re.search(r"(CHAN|S2M|SCORE|FOURNISSEUR|FOURNISSEUR)", l, flags=re.I):
            # next non-empty line might be client
            if i+1 < len(lines):
                return lines[i+1]
            return l
    # last fallback: first long capitalized-ish line
    for l in lines[:10]:
        if len(l) > 3 and not re.search(r"(bon|commande|date|adresse|n°|n )", l, flags=re.I):
            return l
    return ""

def extract_bdc_delivery_address(text: str) -> str:
    """
    Cherche 'Adresse Evraison' ou 'Adresse livraison' (même si mal orthographié).
    Retourne un bloc de texte multi-lignes (jusqu'à la section suivante).
    """
    # support typo "Evraison" (vu dans l'exemple)
    start_pat = re.search(r"(Adresse\s+(?:E?vra|de\s+)?livraison)\s*[:\-]?\s*", text, flags=re.I)
    if start_pat:
        # position du match
        idx = start_pat.end()
        tail = text[idx:]
        # stop when encountering 'Adresse facturation', 'Adresse fournisseur', 'Commentaire', 'Ref four.' etc.
        stop_re = re.search(r"\n(?:Adresse\s+facturation|Adresse\s+fournisseur|Commentaire|Ref\s+four\.|Adresse fournisseur|Référence fournisseur)", tail, flags=re.I)
        if stop_re:
            block = tail[:stop_re.start()].strip()
        else:
            # take next 3 lines as address block as fallback
            block = "\n".join([ln for ln in tail.split("\n")[:4] if ln.strip()]).strip()
        return block
    # fallback: find lines containing LOT, ANTANANARIVO, MDG etc.
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    addr_lines = []
    for l in lines:
        if "LOT" in l.upper() or "ANTANANARIVO" in l.upper() or "MDG" in l.upper() or re.search(r"\d{3}", l):
            addr_lines.append(l)
    if addr_lines:
        return "\n".join(addr_lines[:4])
    return ""

def normalize_items_for_bdc(items_raw):
    """
    items_raw: list of dicts from extract_items() where keys may be 'article'/'quantite'
    Retourne list de dicts avec 'designation' et 'quantite' (int).
    """
    normalized = []
    for it in items_raw:
        article = it.get("article") or it.get("designation") or ""
        quant = it.get("quantite") or it.get("quantite") == 0 and 0 or it.get("quantite") or it.get("bouteilles") or 0
        try:
            quant_i = int(quant)
        except Exception:
            # attempt to clean numbers like "12,000" or "12.000"
            s = str(quant).replace(",", "").replace(".", "").strip()
            quant_i = int(s) if s.isdigit() else 0
        normalized.append({"designation": article.strip(), "quantite": quant_i})
    return normalized

def bdc_pipeline(image_bytes: bytes):
    """
    Pipeline complet BDC:
     - preprocess image
     - OCR via Google Vision
     - nettoyage texte
     - extraction numero / date / client / adresse livraison
     - extraction items (designation + quantite)
    Retour: dict prêt pour l'UI
    """
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)

    numero = extract_bdc_number(raw)
    date = extract_bdc_date(raw)
    client = extract_bdc_client(raw)
    adresse_liv = extract_bdc_delivery_address(raw)

    # Use robust item extractor for listing lines
    items_raw = extract_items(raw)
    items = normalize_items_for_bdc(items_raw)

    # If items seem empty, try a second pass: collect lines after 'Désignation' header
    if not items or all(len(it["designation"]) < 2 for it in items):
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        collect = False
        tmp_items = []
        for l in lines:
            if re.search(r"D[eé]signation", l, flags=re.I):
                collect = True
                continue
            if collect:
                if re.search(r"(Horaire|Montant|Valeur|Seul le prix)", l, flags=re.I):
                    break
                # if line looks like a qty only
                if re.match(r"^[\d\.\, ]+$", l):
                    if tmp_items:
                        tmp_items[-1]["quantite"] = int(re.sub(r"[^\d]", "", l) or 0)
                else:
                    tmp_items.append({"designation": l, "quantite": 0})
        if tmp_items:
            items = tmp_items

    return {
        "raw": raw,
        "numero": numero,
        "date": date,
        "client": client,
        "adresse_livraison": adresse_liv,
        "articles": items
    }
# ======================================================
# BLOC 4 — INTERFACE STREAMLIT (FACTURE + BDC)
# ======================================================

# Préparation accès Google Sheets
def get_gsheet_clients():
    if "gcp_sheet" in st.secrets:
        sa_info = dict(st.secrets["gcp_sheet"])
    elif "google_service_account" in st.secrets:
        sa_info = dict(st.secrets["google_service_account"])
    else:
        raise Exception("❌ Credentials Google Sheets introuvables.")

    client = gspread.service_account_from_dict(sa_info)
    sh = client.open_by_key("1FooEwQBwLjvyjAsvHu4eDes0o-eEm92fbEWv6maBNyE")

    ws_facture = sh.get_worksheet_by_id(72936741)       # Feuille FACTURE
    ws_bdc = sh.get_worksheet_by_id(1487110894)         # Feuille BDC

    return ws_facture, ws_bdc


ws_facture, ws_bdc = None, None
try:
    ws_facture, ws_bdc = get_gsheet_clients()
except Exception as e:
    st.error(f"Erreur Google Sheets : {e}")


# ------------------------------------------------------
# PAGE : Facture ou Bon de commande
# ------------------------------------------------------
st.markdown("## 📌 Choisissez un mode")
colA, colB = st.columns(2)
if colA.button("📄 Scanner une facture"):
    st.session_state.mode = "facture"
if colB.button("📝 Scanner un bon de commande"):
    st.session_state.mode = "bdc"

if "mode" not in st.session_state:
    st.stop()

# ======================================================
# ------------------------- MODE FACTURE ---------------
# ======================================================
if st.session_state.mode == "facture":

    st.markdown("### 📥 Importer une facture")
    up = st.file_uploader("Importer un fichier JPG / PNG", type=["jpg", "jpeg", "png"])

    if not up:
        st.stop()

    img = Image.open(up)
    st.image(img, caption="Aperçu", use_column_width=True)

    buf = BytesIO()
    img.save(buf, format="JPEG")
    bytes_img = buf.getvalue()

    st.info("⏳ Traitement OCR Google Vision…")
    res = invoice_pipeline(bytes_img)

    # Champs détectés
    st.markdown("### ✏️ Informations détectées (modifiable)")
    col1, col2 = st.columns(2)
    facture_num = col1.text_input("Numéro de facture", res["facture"])
    doit_client = col2.text_input("DOIT", res["doit"])
    mois_val = col2.text_input("Mois", res["mois"])
    adresse_val = col2.text_input("Adresse livraison", res["adresse"])
    bc_val = col1.text_input("Suivant bon de commande", res["bon_commande"])

    # Table articles
    st.markdown("### 📦 Articles")
    df = pd.DataFrame(res["articles"])
    if "bouteilles" not in df.columns:
        df["bouteilles"] = df["quantite"] if "quantite" in df else 0

    df["bouteilles"] = df["bouteilles"].astype(int)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "article": "Article",
            "bouteilles": "Quantité",
        },
        use_container_width=True
    )

    # Envoi Google Sheets
    if ws_facture and st.button("📤 Envoyer vers Google Sheets — FACTURE"):
        try:
            today = datetime.now().strftime("%d/%m/%Y")
            for _, row in edited.iterrows():
                ws_facture.append_row([
                    mois_val,
                    doit_client,
                    today,
                    bc_val,
                    adresse_val,
                    row["article"],
                    int(row["bouteilles"])
                ])
            st.success("Données facture envoyées ✔️")
        except Exception as e:
            st.error(f"Erreur Sheets : {e}")

    st.markdown("### Texte brut OCR")
    st.code(res["raw"])

    st.stop()


# ======================================================
# ------------------------- MODE BDC -------------------
# ======================================================
if st.session_state.mode == "bdc":

    st.markdown("### 📝 Importer un Bon de commande")
    up = st.file_uploader("Importer un fichier JPG / PNG", type=["jpg", "jpeg", "png"], key="bdc_up")

    if not up:
        st.stop()

    img = Image.open(up)
    st.image(img, caption="Aperçu BDC", use_column_width=True)

    buf = BytesIO()
    img.save(buf, format="JPEG")
    bytes_img = buf.getvalue()

    st.info("⏳ Traitement OCR Google Vision (BDC)…")
    res = bdc_pipeline(bytes_img)

    # Champs détectés
    st.markdown("### ✏️ Informations BDC détectées (modifiable)")
    col1, col2 = st.columns(2)
    num_bdc = col1.text_input("Numéro BDC", res["numero"])
    date_bdc = col1.text_input("Date", res["date"])
    client = col2.text_input("Client", res["client"])
    adresse_liv = col2.text_area("Adresse de livraison", res["adresse_livraison"])

    # Table articles BDC
    st.markdown("### 📦 Articles (BDC)")
    df = pd.DataFrame(res["articles"])
    df["quantite"] = df["quantite"].astype(int)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "designation": "Désignation",
            "quantite": "Quantité"
        },
        use_container_width=True
    )

    # Envoi Google Sheets — FEUILLE BDC
    if ws_bdc and st.button("📤 Envoyer vers Google Sheets — BDC"):
        try:
            for _, row in edited.iterrows():
                ws_bdc.append_row([
                    num_bdc,
                    client,
                    date_bdc,
                    adresse_liv,
                    row["designation"],
                    int(row["quantite"])
                ])
            st.success("Bon de commande envoyé ✔️")
        except Exception as e:
            st.error(f"Erreur Sheets : {e}")

    st.markdown("### Texte brut OCR")
    st.code(res["raw"])
