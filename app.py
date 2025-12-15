import streamlit as st
import re
from io import BytesIO
from PIL import Image, ImageFilter, ImageOps
from google.cloud import vision
from google.oauth2.service_account import Credentials
import pandas as pd

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="CHAN FOUI – Scan Intelligent", page_icon="🧾")
st.title("🧾 Scan Intelligent — Chan Foui & Fils")

CHOIX = st.radio(
    "📄 Type de document",
    ["FACTURE", "BDC ULYS", "BDC LEADER PRICE", "BDC SUPERMAKI"],
    horizontal=True
)

# ============================================================
# OCR
# ============================================================
def preprocess_image(b):
    img = Image.open(BytesIO(b)).convert("RGB")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=180))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def vision_ocr(b, creds):
    client = vision.ImageAnnotatorClient(
        credentials=Credentials.from_service_account_info(creds)
    )
    image = vision.Image(content=b)
    res = client.document_text_detection(image=image)
    return res.full_text_annotation.text or ""

# ============================================================
# FACTURE
# ============================================================
def parse_facture(text):
    return {
        "type": "FACTURE",
        "client": "",
        "numero": re.search(r"FACTURE.*?(\d+)", text, re.I).group(1),
        "date": re.search(r"(\d{1,2}\s+\w+\s+\d{4})", text).group(1),
        "magasin": "",
        "fournisseur": "",
        "articles": extract_articles_generic(text)
    }

# ============================================================
# BDC ULYS
# ============================================================
def parse_ulys(text):
    return {
        "type": "BDC ULYS",
        "client": "ULYS",
        "numero": re.search(r"N[°o]\s*(\d{8,})", text).group(1),
        "date": re.search(r"Date.*?(\d{2}/\d{2}/\d{4})", text).group(1),
        "magasin": "Super U Analakely",
        "fournisseur": "Chan Foui Fils",
        "articles": extract_articles_generic(text)
    }

# ============================================================
# BDC LEADER PRICE
# ============================================================
def parse_leaderprice(text):
    return {
        "type": "BDC LEADER PRICE",
        "client": "LEADER PRICE",
        "numero": re.search(r"BCD\d+", text).group(0),
        "date": re.search(r"(\d{2}/\d{2}/\d{4})", text).group(1),
        "magasin": "",
        "fournisseur": "Chan Foui Fils",
        "articles": extract_articles_generic(text)
    }

# ============================================================
# BDC SUPERMAKI
# ============================================================
def parse_supermaki(text):
    return {
        "type": "BDC SUPERMAKI",
        "client": "SUPERM AKI",
        "numero": re.search(r"\d{6,}", text).group(0),
        "date": re.search(r"(\d{2}/\d{2}/\d{4})", text).group(1),
        "magasin": "",
        "fournisseur": "Chan Foui Fils",
        "articles": extract_articles_generic(text)
    }

# ============================================================
# ARTICLES (LOGIQUE COMMUNE)
# ============================================================
def extract_articles_generic(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    articles = []
    current = None

    for l in lines:
        if re.search(r"VIN|CONS\.", l, re.I):
            current = l
        elif current and re.fullmatch(r"\d{1,3}", l):
            articles.append({
                "designation": current.title(),
                "quantite": int(l)
            })
            current = None

    return articles

# ============================================================
# UI
# ============================================================
uploaded = st.file_uploader("📤 Importer le document", ["jpg", "jpeg", "png"])

if uploaded and "gcp_vision" in st.secrets:
    img = Image.open(uploaded)
    st.image(img, use_container_width=True)

    buf = BytesIO()
    img.save(buf, format="JPEG")

    raw = vision_ocr(preprocess_image(buf.getvalue()), dict(st.secrets["gcp_vision"]))

    if CHOIX == "FACTURE":
        result = parse_facture(raw)
    elif CHOIX == "BDC ULYS":
        result = parse_ulys(raw)
    elif CHOIX == "BDC LEADER PRICE":
        result = parse_leaderprice(raw)
    else:
        result = parse_supermaki(raw)

    # AFFICHAGE UNIFIÉ
    st.subheader("📋 Informations document")
    for k in ["type", "client", "numero", "date", "magasin", "fournisseur"]:
        if result[k]:
            st.write(f"**{k.capitalize()} :** {result[k]}")

    st.subheader("🛒 Articles")
    st.dataframe(pd.DataFrame(result["articles"]), use_container_width=True)

    with st.expander("🔎 OCR brut"):
        st.text_area("OCR", raw, height=300)
