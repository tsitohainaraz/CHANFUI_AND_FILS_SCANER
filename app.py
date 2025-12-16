import streamlit as st
import re
from io import BytesIO
from PIL import Image, ImageFilter, ImageOps
from google.cloud import vision
from google.oauth2.service_account import Credentials
import pandas as pd

# ============================================================
# CONFIGURATION STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Multi-Scanner de Documents",
    page_icon="🧾",
    layout="centered"
)

st.title("🧾 Multi-Scanner de Documents")
st.caption("Sélectionnez le type de document et importez l'image pour l'analyse")

# ============================================================
# SÉLECTION DU TYPE DE DOCUMENT
# ============================================================
document_type = st.radio(
    "**Sélectionnez le type de document à scanner :**",
    ["FACTURE EN COMPTE", "BDC LEADERPRICE", "BDC SUPERMAKI", "BDC ULYS"],
    horizontal=True
)

st.markdown("---")

# ============================================================
# FONCTIONS COMMUNES
# ============================================================
def preprocess_image(b: bytes, radius=1.2, percent=180) -> bytes:
    """Prétraitement d'image générique"""
    img = Image.open(BytesIO(b)).convert("RGB")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent))
    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def vision_ocr(b: bytes, creds: dict) -> str:
    """OCR avec Google Vision AI"""
    client = vision.ImageAnnotatorClient(
        credentials=Credentials.from_service_account_info(creds)
    )
    image = vision.Image(content=b)
    res = client.document_text_detection(image=image)
    return res.full_text_annotation.text or ""

def clean_text(text: str) -> str:
    """Nettoyage du texte OCR"""
    text = text.replace("\r", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    return text.strip()

# ============================================================
# FONCTIONS D'EXTRACTION SPÉCIFIQUES
# ============================================================

# ----- FACTURE EN COMPTE -----
def extract_facture(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    result = {
        "date": "",
        "facture_numero": "",
        "adresse_livraison": "",
        "doit": "",
        "articles": []
    }

    # Date
    m = re.search(r"le\s+(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    if m:
        result["date"] = m.group(1)

    # Numéro de facture
    m = re.search(r"FACTURE EN COMPTE\s+N[°o]?\s*(\d+)", text, re.IGNORECASE)
    if m:
        result["facture_numero"] = m.group(1)

    # DOIT
    m = re.search(r"DOIT\s*:\s*(S2M|ULYS|DLP)", text, re.IGNORECASE)
    if m:
        result["doit"] = m.group(1)

    # Adresse
    m = re.search(r"Adresse de livraison\s*:\s*(.+)", text, re.IGNORECASE)
    if m:
        result["adresse_livraison"] = m.group(1).strip()

    # Tableau des articles
    in_table = False
    designation_queue = []

    def clean_designation(s: str) -> str:
        return re.sub(r"\s{2,}", " ", s).strip()

    for line in lines:
        up = line.upper()

        if "DÉSIGNATION DES MARCHANDISES" in up:
            in_table = True
            continue

        if not in_table:
            continue

        if "ARRÊTÉE LA PRÉSENTE FACTURE" in up or "TOTAL HT" in up:
            break

        if (
            len(line) > 12
            and not any(x in up for x in ["NB", "BTLL", "PU", "MONTANT", "TOTAL"])
            and not re.fullmatch(r"\d+", line)
        ):
            designation_queue.append(clean_designation(line))
            continue

        qty_match = re.search(r"\b(6|12|24|48|60|72|120)\b", line)
        if qty_match and designation_queue:
            qty = int(qty_match.group(1))
            designation = designation_queue.pop(0)
            result["articles"].append({
                "Désignation": designation,
                "Quantité": qty
            })

    return result

# ----- BDC LEADERPRICE -----
def extract_leaderprice(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    result = {
        "client": "LEADER PRICE",
        "numero": "",
        "date": "",
        "articles": []
    }

    m = re.search(r"BCD\d+", text)
    if m:
        result["numero"] = m.group(0)

    m = re.search(r"Date\s*(\d{2}/\d{2}/\d{2,4})", text)
    if m:
        result["date"] = m.group(1)

    in_table = False
    designation_queue = []

    def clean_designation(s: str) -> str:
        s = re.sub(r"\b\d{4}\b", "", s)
        s = re.sub(r"\s{2,}", " ", s)
        return s.strip()

    for line in lines:
        up = line.upper()

        if up == "RÉF" or "DÉSIGNATION" in up:
            in_table = True
            continue

        if not in_table:
            continue

        if "TOTAL HT" in up:
            break

        if (
            not re.search(r"\d+\.\d{3}", line)
            and len(line) >= 15
            and not any(x in up for x in [
                "PIÈCES", "C/12", "PX", "REM",
                "MONTANT", "QTÉ", "DATE", "TOTAL"
            ])
        ):
            designation_queue.append(clean_designation(line))
            continue

        qty_match = re.search(r"(\d{2,4})\.(\d{3})", line)
        if qty_match and designation_queue:
            qty = int(qty_match.group(1))
            designation = designation_queue.pop(0)
            result["articles"].append({
                "Désignation": designation.title(),
                "Quantité": qty
            })

    return result

# ----- BDC SUPERMAKI -----
def normalize_designation(designation: str) -> str:
    d = designation.upper()
    d = re.sub(r"\s+", " ", d)

    if "COTE DE FIANAR" in d:
        if "ROUGE" in d:
            return "Côte de Fianar Rouge 75 cl"
        if "BLANC" in d:
            return "Côte de Fianar Blanc 75 cl"
        if "ROSE" in d or "ROSÉ" in d:
            return "Côte de Fianar Rosé 75 cl"
        if "GRIS" in d:
            return "Côte de Fianar Gris 75 cl"
        return "Côte de Fianar Rouge 75 cl"

    if "CONS" in d and "CHAN" in d:
        return "CONS 2000 CHANFOUI"

    if "MAROPARASY" in d:
        return "Maroparasy Rouge 75 cl"

    return designation.title()

def extract_bdc_supermaki(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    result = {
        "client": "SUPERMAKI",
        "numero": "",
        "date": "",
        "adresse_livraison": "",
        "articles": []
    }

    m = re.search(r"Bon de commande n[°o]\s*(\d{8})", text)
    if m:
        result["numero"] = m.group(1)

    m = re.search(r"Date\s+[ée]mission\s*(\d{2}/\d{2}/\d{4})", text)
    if m:
        result["date"] = m.group(1)

    for i, l in enumerate(lines):
        if "Adresse de livraison" in l and i + 1 < len(lines):
            result["adresse_livraison"] = lines[i + 1]
            break

    i = 0
    while i < len(lines):
        if re.fullmatch(r"\d{6}", lines[i]):
            if i + 5 < len(lines):
                ean = lines[i + 1]
                designation = lines[i + 2]
                pcb = lines[i + 3]
                nb_colis = lines[i + 4]
                quantite = lines[i + 5]

                if (
                    re.fullmatch(r"\d{13}\.?", ean) and
                    any(k in designation.upper() for k in ["COTE", "CONS", "MAROPARASY"]) and
                    pcb.isdigit() and
                    nb_colis.isdigit() and
                    quantite.isdigit()
                ):
                    result["articles"].append({
                        "Désignation": normalize_designation(designation),
                        "Quantité": int(quantite)
                    })
                    i += 6
                    continue
        i += 1

    return result

# ----- BDC ULYS -----
def extract_bdc_ulys(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    result = {
        "client": "ULYS",
        "numero": "",
        "date": "",
        "articles": []
    }

    m = re.search(r"N[°o]\s*(\d{8,})", text)
    if m:
        result["numero"] = m.group(1)

    m = re.search(r"Date de la Commande\s*:?[\s\-]*(\d{2}/\d{2}/\d{4})", text)
    if m:
        result["date"] = m.group(1)

    in_table = False
    current_designation = ""
    waiting_qty = False

    def is_valid_qty(s: str) -> bool:
        s = s.replace("D", "").replace("O", "0").replace("G", "0")
        return re.fullmatch(r"\d{1,3}", s) is not None

    def clean_designation(s: str) -> str:
        s = re.sub(r"\b\d{6,}\b", "", s)
        s = s.replace("PAQ", "").replace("/PC", "")
        s = re.sub(r"\s{2,}", " ", s)
        return s.strip()

    for line in lines:
        up = line.upper()

        if "DESCRIPTION DE L'ARTICLE" in up:
            in_table = True
            continue

        if not in_table:
            continue

        if "TOTAL DE LA COMMANDE" in up:
            break

        if re.match(r"\d{6}\s+(VINS|CONSIGNE|LIQUEUR)", up):
            continue

        if ("VIN " in up or "CONS." in up) and not re.match(r"\d{6,}", line):
            current_designation = clean_designation(line)
            waiting_qty = False
            continue

        if up in ["PAQ", "/PC"]:
            waiting_qty = True
            continue

        if current_designation and waiting_qty:
            clean = (
                line.replace("D", "")
                    .replace("O", "0")
                    .replace("G", "0")
            )
            if is_valid_qty(clean):
                result["articles"].append({
                    "Désignation": current_designation.title(),
                    "Quantité": int(clean)
                })
                waiting_qty = False
                continue

    return result

# ============================================================
# MAPPING DES FONCTIONS D'EXTRACTION
# ============================================================
EXTRACTION_FUNCTIONS = {
    "FACTURE EN COMPTE": extract_facture,
    "BDC LEADERPRICE": extract_leaderprice,
    "BDC SUPERMAKI": extract_bdc_supermaki,
    "BDC ULYS": extract_bdc_ulys
}

# ============================================================
# INTERFACE UTILISATEUR
# ============================================================
uploaded = st.file_uploader(
    f"📤 Importer l'image du document ({document_type})",
    type=["jpg", "jpeg", "png"]
)

if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Aperçu du document", use_column_width=True)

    if "gcp_vision" not in st.secrets:
        st.error("❌ Credentials Google Vision manquants dans st.secrets")
        st.stop()

    # Conversion de l'image en bytes
    buf = BytesIO()
    image.save(buf, format="JPEG")
    image_bytes = buf.getvalue()

    # Prétraitement spécifique selon le type de document
    with st.spinner("🔍 Traitement de l'image et analyse OCR..."):
        if document_type == "FACTURE EN COMPTE":
            img_processed = preprocess_image(image_bytes, radius=1.1, percent=160)
        elif document_type == "BDC LEADERPRICE":
            img_processed = preprocess_image(image_bytes, radius=1.2, percent=170)
        else:  # SUPERMAKI et ULYS
            img_processed = preprocess_image(image_bytes, radius=1.2, percent=180)
        
        # OCR
        creds = dict(st.secrets["gcp_vision"])
        raw_text = vision_ocr(img_processed, creds)
        raw_text = clean_text(raw_text)
        
        # Extraction
        extract_func = EXTRACTION_FUNCTIONS[document_type]
        result = extract_func(raw_text)

    # Affichage des résultats
    st.subheader("📋 Informations extraites")
    
    # Affichage différent selon le type de document
    if document_type == "FACTURE EN COMPTE":
        col1, col2 = st.columns(2)
        with col1:
            st.write("📅 **Date :**", result.get("date", "Non trouvé"))
            st.write("🧾 **Facture n° :**", result.get("facture_numero", "Non trouvé"))
        with col2:
            st.write("👤 **DOIT :**", result.get("doit", "Non trouvé"))
        st.write("📦 **Adresse de livraison :**", result.get("adresse_livraison", "Non trouvé"))
    
    elif document_type in ["BDC LEADERPRICE", "BDC SUPERMAKI", "BDC ULYS"]:
        col1, col2 = st.columns(2)
        with col1:
            st.write("🏢 **Client :**", result.get("client", "Non trouvé"))
            st.write("🔢 **Numéro :**", result.get("numero", "Non trouvé"))
        with col2:
            st.write("📅 **Date :**", result.get("date", "Non trouvé"))
        
        if document_type == "BDC SUPERMAKI" and result.get("adresse_livraison"):
            st.write("📍 **Adresse de livraison :**", result["adresse_livraison"])

    # Articles
    st.subheader("🛒 Articles détectés")
    if result.get("articles"):
        df = pd.DataFrame(result["articles"])
        st.dataframe(df, use_container_width=True)
        
        # Résumé
        total_qty = sum(item["Quantité"] for item in result["articles"])
        st.info(f"**Total des articles :** {len(result['articles'])} lignes, **Quantité totale :** {total_qty}")
    else:
        st.warning("⚠️ Aucun article détecté dans le document")

    # OCR brut (optionnel)
    with st.expander("🔎 Voir le texte OCR brut"):
        st.text_area("Texte OCR extrait", raw_text, height=300)

st.markdown("---")
st.caption("Multi-Scanner de Documents - Version combinée")
