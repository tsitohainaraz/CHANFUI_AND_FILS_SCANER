import streamlit as st
import pytesseract
from PIL import Image
import pandas as pd
import os
import time
from datetime import datetime

# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Chan Foui & Fils — Scanner Pro",
    page_icon="🧾",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ============================================================
# THEME
# ============================================================
PALETTE = {
    "primary": "#27414A",
    "primary_dark": "#1F2F35",
    "background": "#F5F5F3",
    "white": "#FFFFFF",
    "border": "#D1D5DB",
    "text": "#1A1A1A",
}

# ============================================================
# CSS — TEXTE BOUTONS BLANC + GRAS (CORRIGÉ)
# ============================================================
st.markdown(f"""
<style>
.stApp {{
    background: {PALETTE['background']};
    font-family: Inter, system-ui;
}}

.stButton > button,
.stButton > button * {{
    background: {PALETTE['primary']} !important;
    color: {PALETTE['white']} !important;
    font-weight: 800 !important;
    border-radius: 14px;
    border: none;
    padding: 0.9rem 1.6rem;
}}

.stButton > button:hover,
.stButton > button:hover * {{
    background: {PALETTE['primary_dark']} !important;
}}

.card {{
    background: {PALETTE['white']};
    padding: 2rem;
    border-radius: 18px;
    border: 1px solid {PALETTE['border']};
    margin-bottom: 1.5rem;
}}

.title {{
    background: {PALETTE['primary']};
    color: white;
    padding: 1.2rem;
    border-radius: 16px;
    font-size: 1.4rem;
    font-weight: 800;
    text-align: center;
}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="card" style="text-align:center">', unsafe_allow_html=True)
st.markdown("<h1>CHAN FOUI ET FILS</h1>", unsafe_allow_html=True)
st.markdown("<p>Scanner OCR Local • Version Autonome</p>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
if "doc_type" not in st.session_state:
    st.session_state.doc_type = None
if "ocr_text" not in st.session_state:
    st.session_state.ocr_text = ""

# ============================================================
# CHOIX TYPE DOCUMENT
# ============================================================
if not st.session_state.doc_type:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("## 📋 Sélectionnez le type de document")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if st.button("🧾 FACTURE"):
            st.session_state.doc_type = "FACTURE"

    with c2:
        if st.button("🏪 BDC LEADERPRICE"):
            st.session_state.doc_type = "BDC LEADERPRICE"

    with c3:
        if st.button("🛒 BDC S2M"):
            st.session_state.doc_type = "BDC S2M"

    with c4:
        if st.button("🏢 BDC ULYS"):
            st.session_state.doc_type = "BDC ULYS"

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ============================================================
# MODE ACTIF
# ============================================================
st.markdown(
    f'<div class="title">Mode actif : {st.session_state.doc_type}</div>',
    unsafe_allow_html=True
)

# ============================================================
# UPLOAD IMAGE
# ============================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "📤 Glissez-déposez le document (JPG / PNG)",
    type=["jpg", "jpeg", "png"]
)
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# OCR LOCAL
# ============================================================
if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Aperçu du document", use_column_width=True)

    if st.button("🔍 Lancer l’OCR"):
        with st.spinner("Analyse OCR en cours..."):
            time.sleep(0.5)
            text = pytesseract.image_to_string(image, lang="fra")
            st.session_state.ocr_text = text

        st.success("OCR terminé ✔")

# ============================================================
# RESULTATS OCR
# ============================================================
if st.session_state.ocr_text:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📄 Texte OCR extrait")
    st.text_area(
        "Résultat OCR",
        value=st.session_state.ocr_text,
        height=300
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# NAVIGATION
# ============================================================
c1, c2 = st.columns(2)

with c1:
    if st.button("⬅️ Changer de type"):
        st.session_state.doc_type = None
        st.session_state.ocr_text = ""
        st.rerun()

with c2:
    if st.button("🔄 Recommencer"):
        st.session_state.ocr_text = ""
        st.rerun()

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    f"<p style='text-align:center;font-size:0.85rem'>© {datetime.now().year} Chan Foui et Fils • Scanner Pro</p>",
    unsafe_allow_html=True
)
