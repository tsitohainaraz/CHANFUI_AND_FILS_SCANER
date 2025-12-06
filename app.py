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
    Logic:
     - Parcourt chaque ligne non vide
     - Cherche le dernier nombre dans la ligne (peut contenir '.' ou ',' comme séparateur)
     - Nettoie le nombre et convertit en int si possible
     - Le reste de la ligne devient la description
    """
    items = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for l in lines:
        # ignore lines that are clearly headers
        if re.search(r"(bon|commande|date|adresse|factur|client|total|montant)", l, flags=re.I):
            continue
        # find all numbers (with possible thousands separators)
        nums = re.findall(r"(\d{1,3}(?:[.,]\d{3})*|\d+)", l)
        if nums:
            last_num = nums[-1]
            # normalize number: remove spaces, replace comma by '' if it's thousand sep, else handle decimal
            n_clean = last_num.replace(" ", "").replace(",", "").replace(".", "")
            try:
                q = int(n_clean)
            except Exception:
                q = 0
            # remove the matched numeric substring from line (only the last occurrence)
            # escape punctuation for regex
            esc_last = re.escape(last_num)
            article = re.sub(rf"{esc_last}\s*$", "", l).strip()
            article = re.sub(r"\s{2,}", " ", article)
            if article == "":
                article = l
            items.append({"article": article, "quantite": q})
        else:
            # no number found: maybe a pure description row -> quantity 0
            items.append({"article": l, "quantite": 0})
    # Post-process: try to merge nonsense single-word lines etc. (simple heuristic)
    # Remove duplicates and keep meaningful ones
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
# ADD PIMPELINE
# ---------------------------
def extract_table_bdc_8cols(text: str):
    """
    Extraction robuste des 8 colonnes :
    Ref four | Code ean | Désignation | PCB | Nb colis | Qté | P.A fact | T.TVA
    Fonctionne même si OCR casse les lignes.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    items = []
    i = 0
    while i < len(lines):
        l = lines[i]

        # Chercher un Ref four = 6 à 9 chiffres
        if re.fullmatch(r"\d{6,12}", l):
            ref_four = l
            i += 1

            # Code EAN (souvent 9 à 14 chiffres)
            if i < len(lines) and re.fullmatch(r"\d{8,14}", lines[i]):
                code_ean = lines[i]
                i += 1
            else:
                code_ean = ""

            # Désignation (1 à plusieurs lignes jusqu'à chiffre PCB)
            designation_lines = []
            while i < len(lines) and not re.fullmatch(r"\d{1,3}", lines[i]):
                designation_lines.append(lines[i])
                i += 1
            designation = " ".join(designation_lines).strip()

            # PCB = petit entier (ex : 6, 12)
            pcb = lines[i] if i < len(lines) and re.fullmatch(r"\d{1,3}", lines[i]) else ""
            if pcb:
                i += 1

            # Nb colis (ex : 1.00 ou 2,00)
            nb_colis = ""
            if i < len(lines) and re.fullmatch(r"\d+[.,]\d+", lines[i]):
                nb_colis = lines[i]
                i += 1

            # Bloc Qté / Nb colis / PA fact (ex: "12,000 8 625,000")
            qte = ""
            pa_fact = ""
            if i < len(lines) and re.search(r"\d", lines[i]):
                bloc = lines[i].replace(",", ".")
                nums = re.findall(r"[\d\.]+", bloc)
                if len(nums) >= 3:
                    qte = nums[0]
                    nb_colis = nums[1] if not nb_colis else nb_colis  # si absent plus tôt
                    pa_fact = nums[2]
                i += 1

            # T.TVA (ex : 20.00)
            tva = ""
            if i < len(lines) and re.fullmatch(r"\d+[.,]\d+", lines[i]):
                tva = lines[i]
                i += 1

            items.append({
                "ref_four": ref_four,
                "code_ean": code_ean,
                "designation": designation,
                "pcb": pcb,
                "nb_colis": nb_colis,
                "qte": qte,
                "pa_fact": pa_fact,
                "tva": tva
            })

        else:
            i += 1
        
    return items
# ---------------------------
# BDC pipeline (amélioré)
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
    m2 = re.search(r"Date(?:\s+d['’]emission)?\s*[:\-]?\s*(\d{1,2}\/\d{1,2}\/\d{2,4})", text, flags=re.I)
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

def bdc_pipeline(image_bytes: bytes):
    cleaned = preprocess_image(image_bytes)
    raw = google_vision_ocr(cleaned)
    raw = clean_text(raw)

    numero = extract_bdc_number(raw)
    date = extract_bdc_date(raw)
    client = extract_bdc_client(raw)
    adresse_liv = extract_bdc_delivery_address(raw)
    items = extract_table_bdc_8cols(raw)

    normalized = []
    for it in items:
        normalized.append({
            "Ref four.": it["ref_four"],
            "Code ean": it["code_ean"],
            "Désignation": it["designation"],
            "PCB": it["pcb"],
            "Nb colis": it["nb_colis"],
            "Qté": it["qte"],
            "P.A fact.": it["pa_fact"],
            "T.TVA": it["tva"]
        })
    
    
        return {
            "raw": raw,
            "numero": numero,
            "client": client,
            "date": date,
            "adresse_livraison": adresse_liv,
            "articles": normalized
        }
# ---------------------------
# NEW: Table extraction from Vision (for BDC structured table with 8 fixed columns)
# ---------------------------
def bbox_center(bbox):
    xs = [v.x for v in bbox.vertices]
    ys = [v.y for v in bbox.vertices]
    # some vertices may be None in certain responses - filter
    xs = [x for x in xs if x is not None]
    ys = [y for y in ys if y is not None]
    return (sum(xs) / len(xs), sum(ys) / len(ys))

def cluster_positions(positions, tol=60):
    if not positions:
        return []
    pos = sorted(positions)
    clusters = [[pos[0]]]
    for p in pos[1:]:
        if abs(p - np.mean(clusters[-1])) <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    centers = [float(np.mean(c)) for c in clusters]
    return centers

def extract_table_from_image(image_bytes: bytes, expected_cols, x_tol=60, y_tol=18):
    """
    Returns a DataFrame with columns = expected_cols by extracting words + bboxes using
    Google Vision document_text_detection, grouping into lines, clustering X positions
    into columns and assembling cells.
    """
    client = get_vision_client()
    image = vision.Image(content=image_bytes)
    resp = client.document_text_detection(image=image)
    if resp.error and resp.error.message:
        raise Exception(f"Google Vision Error: {resp.error.message}")

    words = []
    # iterate all symbols/words to get bounding boxes and text
    for page in resp.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    text = ''.join([s.text for s in word.symbols])
                    # compute center
                    cx, cy = bbox_center(word.bounding_box)
                    ys = [v.y for v in word.bounding_box.vertices if v.y is not None]
                    miny = min(ys) if ys else cy
                    maxy = max(ys) if ys else cy
                    words.append({"text": text, "cx": cx, "cy": cy, "miny": miny, "maxy": maxy})

    if not words:
        return pd.DataFrame(columns=expected_cols)

    # group by lines using y_tol
    words_sorted = sorted(words, key=lambda w: w["cy"])
    lines = []
    current = [words_sorted[0]]
    for w in words_sorted[1:]:
        if abs(w["cy"] - np.mean([c["cy"] for c in current])) <= y_tol:
            current.append(w)
        else:
            lines.append(sorted(current, key=lambda q: q["cx"]))
            current = [w]
    lines.append(sorted(current, key=lambda q: q["cx"]))

    # build list of all x centers to detect columns
    all_x = [w["cx"] for w in words]
    col_centers = cluster_positions(all_x, tol=x_tol)

    # If cluster count differs from expected, try to adjust tolerance
    if len(col_centers) < len(expected_cols):
        col_centers = cluster_positions(all_x, tol=int(x_tol * 0.7))
    if len(col_centers) > len(expected_cols):
        # pick the most spread centers by merging nearest until match expected length
        while len(col_centers) > len(expected_cols):
            # merge the closest pair
            dists = [(i, j, abs(col_centers[i] - col_centers[j])) for i in range(len(col_centers)) for j in range(i+1, len(col_centers))]
            i,j,_ = min(dists, key=lambda x: x[2])
            merged = (col_centers[i] + col_centers[j]) / 2.0
            new = [c for k,c in enumerate(col_centers) if k not in (i,j)]
            new.append(merged)
            col_centers = sorted(new)

    # For each line, assign words to nearest column center
    table_rows = []
    for line in lines:
        cells = {i: [] for i in range(len(col_centers))}
        for w in line:
            dists = [abs(w["cx"] - c) for c in col_centers]
            idx = int(np.argmin(dists))
            cells[idx].append((w["cx"], w["text"]))
        # assemble cell texts ordered by column
        row = []
        for i in range(len(col_centers)):
            if cells[i]:
                frags = [t for _, t in sorted(cells[i], key=lambda x: x[0])]
                row.append(" ".join(frags))
            else:
                row.append("")
        table_rows.append(row)

    # Convert to DataFrame
    df_raw = pd.DataFrame(table_rows)

    # Try to detect header row: find row containing at least 3 expected header keywords
    header_idx = None
    for i in range(min(4, len(df_raw))):
        row_text = " ".join(df_raw.iloc[i].astype(str).values).lower()
        matches = sum(1 for k in expected_cols if k.lower().replace(".", "").replace(" ", "") in row_text.replace(".", "").replace(" ", ""))
        if matches >= 2:
            header_idx = i
            break

    if header_idx is not None:
        header = list(df_raw.iloc[header_idx])
        data = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
        # Map header positions to expected columns - try to align by fuzzy match
        mapped_cols = []
        for h in header:
            h_norm = str(h).strip().lower()
            best = None
            for ex in expected_cols:
                ex_norm = ex.lower().replace(".", "").replace(" ", "")
                if ex_norm in h_norm or h_norm in ex_norm:
                    best = ex
                    break
            mapped_cols.append(best or "")
        # If mapping yields empty, fallback to positional mapping
        final_cols = []
        for i, m in enumerate(mapped_cols):
            if m:
                final_cols.append(m)
            else:
                # use positional expected col if available
                final_cols.append(expected_cols[i] if i < len(expected_cols) else f"col_{i}")
        data.columns = final_cols
        # ensure all expected cols present and in order
        for ex in expected_cols:
            if ex not in data.columns:
                data[ex] = ""
        data = data[expected_cols]
    else:
        # No header found: map columns by position -> expected_cols
        ncols = df_raw.shape[1]
        names = []
        for i in range(ncols):
            if i < len(expected_cols):
                names.append(expected_cols[i])
            else:
                names.append(f"col_{i}")
        df_raw.columns = names
        # ensure all expected exist
        for ex in expected_cols:
            if ex not in df_raw.columns:
                df_raw[ex] = ""
        data = df_raw[expected_cols]

    # simple cleanup: strip whitespace and normalize number fields
    def normalize_num(v):
        s = str(v).strip()
        if s == "":
            return ""
        s2 = s.replace(" ", "").replace(",", "").replace(".", "")
        if s2.isdigit():
            return int(s2)
        return s

    # try to cast Qté, Nb colis, PCB, P.A fact., T.TVA if possible
    for col in ["Nb colis", "Qté", "PCB", "P.A fact.", "T.TVA"]:
        if col in data.columns:
            data[col] = data[col].apply(lambda x: normalize_num(x))

    # strip all text values
    data = data.applymap(lambda x: (str(x).strip() if not (isinstance(x, int)) else x))

    # remove rows that are fully empty
    data = data[~(data.apply(lambda r: all([str(c).strip() == "" for c in r]), axis=1))].reset_index(drop=True)

    return data

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
# BDC mode (Bon de commande) - UPDATED to extract 8-column table automatically
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
                # Keep the existing bdc pipeline for header metadata
                res_bdc = bdc_pipeline(img_bdc_bytes)
            except Exception as e:
                st.error(f"Erreur OCR (BDC): {e}")
                p.empty()
                st.stop()
            p.progress(100)
            p.empty()

            # Detection fields (improved) - keep exactly as you requested (modifiable)
            st.subheader("Informations détectées (modifiable)")
            col1, col2 = st.columns(2)
            numero_val = col1.text_input("🔢 Numéro BDC", value=res_bdc.get("numero", ""))
            client_val = col1.text_input("👤 Client / Facturation", value=res_bdc.get("client", ""))
            date_val = col2.text_input("📅 Date d'émission", value=res_bdc.get("date", datetime.now().strftime("%d/%m/%Y")))
            adresse_val = col2.text_input("📍 Adresse de livraison", value=res_bdc.get("adresse_livraison", ""))
            st.markdown("</div>", unsafe_allow_html=True)

            # Articles editor (dynamic) - REPLACED: now 8 columns as requested
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.subheader("Articles détectés (modifiable)")

            expected_cols = ["Ref four.", "Code ean", "Désignation", "PCB", "Nb colis", "Qté", "P.A fact.", "T.TVA"]

            # Try automatic extraction of the 8-column table
            with st.spinner("Extraction automatique du tableau..."):
                try:
                    df_bdc_table = extract_table_from_image(img_bdc_bytes, expected_cols, x_tol=60, y_tol=18)
                except Exception as e:
                    st.error(f"Erreur extraction tableau automatique: {e}")
                    df_bdc_table = pd.DataFrame(columns=expected_cols)

            # If extraction yielded empty, provide one blank row
            if df_bdc_table.empty:
                df_bdc_table = pd.DataFrame([{c: "" for c in expected_cols}])

            # Ensure column order exactly as expected
            df_bdc_table = df_bdc_table.reindex(columns=expected_cols, fill_value="")

            # Cast numeric columns for nicer editor
            for col in ["Nb colis", "Qté", "PCB", "P.A fact.", "T.TVA"]:
                if col in df_bdc_table.columns:
                    # empty strings -> keep as ""
                    df_bdc_table[col] = df_bdc_table[col].replace("", "")
                    # for integers, keep as numeric where possible
                    def safe_to_numeric(v):
                        try:
                            if v is None or str(v).strip() == "":
                                return ""
                            s = str(v).replace(" ", "").replace(",", "").replace(".", "")
                            if s.isdigit():
                                return int(s)
                            # try float
                            return float(str(v).replace(",", "."))
                        except Exception:
                            return str(v)
                    df_bdc_table[col] = df_bdc_table[col].apply(safe_to_numeric)

            # Use data_editor with explicit column config
            column_config = {
                "Ref four.": st.column_config.TextColumn("Ref four."),
                "Code ean": st.column_config.TextColumn("Code ean"),
                "Désignation": st.column_config.TextColumn("Désignation"),
                "PCB": st.column_config.NumberColumn("PCB", min_value=0),
                "Nb colis": st.column_config.NumberColumn("Nb colis", min_value=0),
                "Qté": st.column_config.NumberColumn("Qté", min_value=0),
                "P.A fact.": st.column_config.TextColumn("P.A fact."),
                "T.TVA": st.column_config.TextColumn("T.TVA")
            }

            edited_bdc = st.data_editor(
                df_bdc_table,
                num_rows="dynamic",
                column_config=column_config,
                use_container_width=True
            )

            # add new line button
            if st.button("➕ Ajouter une ligne BDC"):
                new_row = pd.DataFrame([{c: "" for c in expected_cols}])
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

            # Envoi vers Google Sheets (BDC) -> write expected_cols order
            if st.button("📤 Envoyer vers Google Sheets — BDC"):
                try:
                    if ws_bdc is None:
                        raise FileNotFoundError("Credentials Google Sheets / BDC non configuré")

                    edited = st.session_state.get("edited_bdc_df", edited_bdc).copy()
                    # normalize: ensure columns present
                    for c in expected_cols:
                        if c not in edited.columns:
                            edited[c] = ""
                    # filter empty rows (all empty)
                    def row_non_empty(r):
                        for c in expected_cols:
                            if str(r.get(c, "")).strip() != "":
                                return True
                        return False
                    edited = edited[edited.apply(row_non_empty, axis=1)].reset_index(drop=True)

                    # append rows one by one as list in exact order
                    existing = ws_bdc.get_all_values()
                    start_row = len(existing) + 1
                    today_str = datetime.now().strftime("%d/%m/%Y")

                    for _, row in edited.iterrows():
                        row_vals = [row.get(c, "") for c in expected_cols]
                        # optionally add metadata columns if you want (numero, client, date, adresse, user)
                        final_row = [
                            numero_val or "",
                            client_val or "",
                            date_val or today_str,
                            adresse_val or ""
                        ] + row_vals + [st.session_state.user_nom]
                        # append: match your sheet structure — here we append whole list
                        ws_bdc.append_row(final_row)

                    end_row = len(ws_bdc.get_all_values())

                    st.success("✅ Données BDC insérées avec succès !")
                    st.info(f"📌 Lignes insérées dans le sheet BDC : {start_row} → {end_row}")

                    # try color - use sheet id
                    try:
                        sheet_id_bdc = ws_bdc.id
                        # color only the rows we appended; note: we appended n rows, compute indices
                        color_rows(BDC_SHEET_ID, sheet_id_bdc, start_row-1, end_row, st.session_state.get("scan_index", 0))
                    except Exception:
                        st.warning("Coloration automatique du BDC sheet a échoué (permission / sheetId).")

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


