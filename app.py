# ============================================================
# APP AI — MULTI SCAN (FACTURE / LEADER PRICE / ULYS / SUPERMAKI)
# Vision AI — Chan Foui & Fils
# ============================================================

import streamlit as st
import re
from io import BytesIO
from PIL import Image, ImageFilter, ImageOps
from google.cloud import vision
from google.oauth2.service_account import Credentials
import pandas as pd

# ============================================================
# CONFIG STREAMLIT (UNE SEULE FOIS)
# ============================================================
st.set_page_config(
    page_title="APP AI — Scan Documents",
    page_icon="🧾",
    layout="centered"
)

st.title("🧾 APP AI — Scan intelligent des documents")
st.caption("Facture • BDC Leader Price • BDC ULYS • BDC Supermaki")

# ============================================================
# OUTILS COMMUNS
# ============================================================
def preprocess_image(b: bytes) -> bytes:
    img = Image.open(BytesIO(b)).convert("RGB")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=170))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def vision_ocr(b: bytes, creds: dict) -> str:
    client = vision.ImageAnnotatorClient(
        credentials=Credentials.from_service_account_info(creds)
    )
    image = vision.Image(content=b)
    res = client.document_text_detection(image=image)
    return res.full_text_annotation.text or ""

def load_image(uploaded):
    image = Image.open(uploaded)
    st.image(image, use_container_width=True)
    buf = BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()

# ============================================================
# 1️⃣ FACTURE EN COMPTE — VERSION STABLE
# ============================================================
def run_facture(image_bytes, raw_text):
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    result = {
        "date": "",
        "facture_numero": "",
        "adresse_livraison": "",
        "doit": "",
        "articles": []
    }

    m = re.search(r"le\s+(\d{1,2}\s+\w+\s+\d{4})", raw_text, re.IGNORECASE)
    if m: result["date"] = m.group(1)

    m = re.search(r"FACTURE EN COMPTE\s+N[°o]?\s*(\d+)", raw_text, re.IGNORECASE)
    if m: result["facture_numero"] = m.group(1)

    m = re.search(r"DOIT\s*:\s*(S2M|ULYS|DLP)", raw_text, re.IGNORECASE)
    if m: result["doit"] = m.group(1)

    m = re.search(r"Adresse de livraison\s*:\s*(.+)", raw_text, re.IGNORECASE)
    if m: result["adresse_livraison"] = m.group(1)

    in_table = False
    queue = []

    for l in lines:
        up = l.upper()
        if "DÉSIGNATION DES MARCHANDISES" in up:
            in_table = True
            continue
        if not in_table:
            continue
        if "TOTAL HT" in up:
            break

        if len(l) > 12 and not re.fullmatch(r"\d+", l):
            queue.append(l)
            continue

        q = re.search(r"\b(6|12|24|48|60|72|120)\b", l)
        if q and queue:
            result["articles"].append({
                "Désignation": queue.pop(0),
                "Quantité": int(q.group(1))
            })

    return result

# ============================================================
# 2️⃣ BDC LEADER PRICE — VERSION FINALE
# ============================================================
def run_leader_price(image_bytes, raw_text):
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    result = {"client": "LEADER PRICE", "articles": []}
    queue = []
    in_table = False

    for l in lines:
        up = l.upper()
        if "DÉSIGNATION" in up:
            in_table = True
            continue
        if not in_table:
            continue
        if "TOTAL HT" in up:
            break

        if len(l) > 15 and not re.search(r"\d+\.\d{3}", l):
            queue.append(l)
            continue

        q = re.search(r"(\d{2,4})\.(\d{3})", l)
        if q and queue:
            result["articles"].append({
                "Désignation": queue.pop(0),
                "Quantité": int(q.group(1))
            })

    return result

# ============================================================
# 3️⃣ BDC ULYS — VERSION MÉTIER (STABLE)
# ============================================================
def run_ulys(image_bytes, raw_text):
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    result = {"client": "ULYS", "articles": []}

    current = ""
    waiting_qty = False

    for l in lines:
        up = l.upper()

        if ("VIN " in up or "CONS." in up) and not re.search(r"\d{6,}", l):
            current = l
            waiting_qty = False
            continue

        if up in ["PAQ", "/PC"]:
            waiting_qty = True
            continue

        if current and waiting_qty:
            c = l.replace("D", "").replace("O", "0")
            if re.fullmatch(r"\d{1,3}", c):
                result["articles"].append({
                    "Désignation": current,
                    "Quantité": int(c)
                })
                waiting_qty = False

    return result

# ============================================================
# 4️⃣ SUPERMAKI (BASE ACTUELLE)
# ============================================================
def run_supermaki(image_bytes, raw_text):
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    result = {"client": "SUPERMAKI", "articles": []}
    queue = []

    for l in lines:
        if len(l) > 15 and not re.search(r"\d{2,}", l):
            queue.append(l)
            continue
        q = re.search(r"\b\d{2,3}\b", l)
        if q and queue:
            result["articles"].append({
                "Désignation": queue.pop(0),
                "Quantité": int(q.group(0))
            })

    return result

# ============================================================
# INTERFACE — 4 BOUTONS
# ============================================================
CHOIX = st.radio(
    "📄 Choisir le type de document",
    ["FACTURE", "LEADER PRICE", "ULYS", "SUPERMAKI"]
)

uploaded = st.file_uploader("📤 Importer l’image", ["jpg", "jpeg", "png"])

if uploaded and "gcp_vision" in st.secrets:
    img_bytes = preprocess_image(load_image(uploaded))
    raw = vision_ocr(img_bytes, dict(st.secrets["gcp_vision"]))

    if CHOIX == "FACTURE":
        result = run_facture(img_bytes, raw)
    elif CHOIX == "LEADER PRICE":
        result = run_leader_price(img_bytes, raw)
    elif CHOIX == "ULYS":
        result = run_ulys(img_bytes, raw)
    else:
        result = run_supermaki(img_bytes, raw)

    st.subheader("🛒 Résultat")
    st.dataframe(pd.DataFrame(result["articles"]), use_container_width=True)

    with st.expander("🔎 OCR brut"):
        st.text_area("OCR", raw, height=300)
