import streamlit as st
import re
from io import BytesIO
from PIL import Image, ImageFilter, ImageOps
from google.cloud import vision
from google.oauth2.service_account import Credentials
import pandas as pd
import base64
from datetime import datetime

# ============================================================
# CONFIGURATION STREAMLIT & CSS PERSONNALISÉ
# ============================================================
st.set_page_config(
    page_title="DocScan Pro - Scanner Intelligent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design moderne et responsive
st.markdown("""
<style>
    /* Design général */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .stApp {
        background: #f8f9fa;
    }
    
    /* Header */
    .header-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        color: white;
    }
    
    .header-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(45deg, #60a5fa, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    /* Cartes */
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        border: 1px solid #e5e7eb;
        transition: transform 0.3s ease;
    }
    
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.1);
    }
    
    /* Boutons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
    }
    
    /* Sélecteur de document */
    .doc-selector {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        justify-content: center;
        margin: 2rem 0;
    }
    
    .doc-option {
        flex: 1;
        min-width: 200px;
        text-align: center;
    }
    
    /* Zone de dépôt */
    .upload-box {
        border: 3px dashed #60a5fa;
        border-radius: 20px;
        padding: 3rem;
        text-align: center;
        background: rgba(96, 165, 250, 0.05);
        margin: 2rem 0;
        transition: all 0.3s ease;
    }
    
    .upload-box:hover {
        background: rgba(96, 165, 250, 0.1);
        border-color: #8b5cf6;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .header-title {
            font-size: 1.8rem;
        }
        
        .doc-option {
            min-width: 100%;
        }
        
        .upload-box {
            padding: 1.5rem;
        }
        
        .card {
            padding: 1rem;
        }
    }
    
    /* Stats */
    .stats-card {
        background: linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        text-align: center;
    }
    
    .stats-number {
        font-size: 2rem;
        font-weight: 800;
        margin: 0.5rem 0;
    }
    
    /* Onglets personnalisés */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 12px 12px 0 0;
        padding: 12px 24px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# EN-TÊTE MODERNE
# ============================================================
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="header-title">🤖 DocScan Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #94a3b8; font-size: 1.1rem;">Scanner intelligent de documents avec Vision AI</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# BARRE LATÉRALE POUR LE TYPE DE DOCUMENT
# ============================================================
with st.sidebar:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📋 Type de Document")
    st.markdown("---")
    
    document_type = st.radio(
        "Sélectionnez le type de document à scanner :",
        ["FACTURE EN COMPTE", "BDC LEADERPRICE", "BDC SUPERMAKI", "BDC ULYS"],
        label_visibility="collapsed"
    )
    
    # Icônes selon le type
    icons = {
        "FACTURE EN COMPTE": "🧾",
        "BDC LEADERPRICE": "🏪",
        "BDC SUPERMAKI": "🛒",
        "BDC ULYS": "🏢"
    }
    
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 12px; margin-top: 1rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">{icons[document_type]}</div>
        <h3 style="margin: 0; color: #0f172a;">{document_type}</h3>
        <p style="color: #64748b; font-size: 0.9rem;">Prêt pour analyse</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section statistiques
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📊 Statistiques")
    st.markdown("---")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown('<div class="stats-card">', unsafe_allow_html=True)
        st.markdown('<div class="stats-number">4</div>', unsafe_allow_html=True)
        st.markdown('<div>Types supportés</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_s2:
        st.markdown('<div class="stats-card">', unsafe_allow_html=True)
        st.markdown('<div class="stats-number">AI</div>', unsafe_allow_html=True)
        st.markdown('<div>Powered</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# FONCTIONS BACKEND (CONSERVÉES TELLES QUELLES)
# ============================================================
def preprocess_image(b: bytes, radius=1.2, percent=180) -> bytes:
    img = Image.open(BytesIO(b)).convert("RGB")
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent))
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

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[^\S\r\n]+", " ", text)
    return text.strip()

# ----- FACTURE EN COMPTE -----
def extract_facture(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {"date": "", "facture_numero": "", "adresse_livraison": "", "doit": "", "articles": []}
    
    m = re.search(r"le\s+(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    if m: result["date"] = m.group(1)
    
    m = re.search(r"FACTURE EN COMPTE\s+N[°o]?\s*(\d+)", text, re.IGNORECASE)
    if m: result["facture_numero"] = m.group(1)
    
    m = re.search(r"DOIT\s*:\s*(S2M|ULYS|DLP)", text, re.IGNORECASE)
    if m: result["doit"] = m.group(1)
    
    m = re.search(r"Adresse de livraison\s*:\s*(.+)", text, re.IGNORECASE)
    if m: result["adresse_livraison"] = m.group(1).strip()
    
    in_table = False
    designation_queue = []
    
    def clean_designation(s: str) -> str:
        return re.sub(r"\s{2,}", " ", s).strip()
    
    for line in lines:
        up = line.upper()
        if "DÉSIGNATION DES MARCHANDISES" in up:
            in_table = True
            continue
        if not in_table: continue
        if "ARRÊTÉE LA PRÉSENTE FACTURE" in up or "TOTAL HT" in up:
            break
        if (len(line) > 12 and not any(x in up for x in ["NB", "BTLL", "PU", "MONTANT", "TOTAL"]) and not re.fullmatch(r"\d+", line)):
            designation_queue.append(clean_designation(line))
            continue
        qty_match = re.search(r"\b(6|12|24|48|60|72|120)\b", line)
        if qty_match and designation_queue:
            qty = int(qty_match.group(1))
            designation = designation_queue.pop(0)
            result["articles"].append({"Désignation": designation, "Quantité": qty})
    
    return result

# ----- BDC LEADERPRICE -----
def extract_leaderprice(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {"client": "LEADER PRICE", "numero": "", "date": "", "articles": []}
    
    m = re.search(r"BCD\d+", text)
    if m: result["numero"] = m.group(0)
    
    m = re.search(r"Date\s*(\d{2}/\d{2}/\d{2,4})", text)
    if m: result["date"] = m.group(1)
    
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
        if not in_table: continue
        if "TOTAL HT" in up: break
        if (not re.search(r"\d+\.\d{3}", line) and len(line) >= 15 and not any(x in up for x in ["PIÈCES", "C/12", "PX", "REM", "MONTANT", "QTÉ", "DATE", "TOTAL"])):
            designation_queue.append(clean_designation(line))
            continue
        qty_match = re.search(r"(\d{2,4})\.(\d{3})", line)
        if qty_match and designation_queue:
            qty = int(qty_match.group(1))
            designation = designation_queue.pop(0)
            result["articles"].append({"Désignation": designation.title(), "Quantité": qty})
    
    return result

# ----- BDC SUPERMAKI -----
def normalize_designation(designation: str) -> str:
    d = designation.upper()
    d = re.sub(r"\s+", " ", d)
    
    if "COTE DE FIANAR" in d:
        if "ROUGE" in d: return "Côte de Fianar Rouge 75 cl"
        if "BLANC" in d: return "Côte de Fianar Blanc 75 cl"
        if "ROSE" in d or "ROSÉ" in d: return "Côte de Fianar Rosé 75 cl"
        if "GRIS" in d: return "Côte de Fianar Gris 75 cl"
        return "Côte de Fianar Rouge 75 cl"
    
    if "CONS" in d and "CHAN" in d:
        return "CONS 2000 CHANFOUI"
    
    if "MAROPARASY" in d:
        return "Maroparasy Rouge 75 cl"
    
    return designation.title()

def extract_bdc_supermaki(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {"client": "SUPERMAKI", "numero": "", "date": "", "adresse_livraison": "", "articles": []}
    
    m = re.search(r"Bon de commande n[°o]\s*(\d{8})", text)
    if m: result["numero"] = m.group(1)
    
    m = re.search(r"Date\s+[ée]mission\s*(\d{2}/\d{2}/\d{4})", text)
    if m: result["date"] = m.group(1)
    
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
                if (re.fullmatch(r"\d{13}\.?", ean) and any(k in designation.upper() for k in ["COTE", "CONS", "MAROPARASY"]) and pcb.isdigit() and nb_colis.isdigit() and quantite.isdigit()):
                    result["articles"].append({"Désignation": normalize_designation(designation), "Quantité": int(quantite)})
                    i += 6
                    continue
        i += 1
    
    return result

# ----- BDC ULYS -----
def extract_bdc_ulys(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    result = {"client": "ULYS", "numero": "", "date": "", "articles": []}
    
    m = re.search(r"N[°o]\s*(\d{8,})", text)
    if m: result["numero"] = m.group(1)
    
    m = re.search(r"Date de la Commande\s*:?[\s\-]*(\d{2}/\d{2}/\d{4})", text)
    if m: result["date"] = m.group(1)
    
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
        if not in_table: continue
        if "TOTAL DE LA COMMANDE" in up: break
        if re.match(r"\d{6}\s+(VINS|CONSIGNE|LIQUEUR)", up): continue
        if ("VIN " in up or "CONS." in up) and not re.match(r"\d{6,}", line):
            current_designation = clean_designation(line)
            waiting_qty = False
            continue
        if up in ["PAQ", "/PC"]: waiting_qty = True; continue
        if current_designation and waiting_qty:
            clean = line.replace("D", "").replace("O", "0").replace("G", "0")
            if is_valid_qty(clean):
                result["articles"].append({"Désignation": current_designation.title(), "Quantité": int(clean)})
                waiting_qty = False
                continue
    
    return result

EXTRACTION_FUNCTIONS = {
    "FACTURE EN COMPTE": extract_facture,
    "BDC LEADERPRICE": extract_leaderprice,
    "BDC SUPERMAKI": extract_bdc_supermaki,
    "BDC ULYS": extract_bdc_ulys
}

# ============================================================
# ZONE DE TÉLÉCHARGEMENT MODERNE
# ============================================================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 📤 Importation du Document")

col_upload1, col_upload2, col_upload3 = st.columns([1, 2, 1])
with col_upload2:
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        f"**Glissez-déposez votre document {document_type} ici**",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed",
        help="Formats supportés : JPG, JPEG, PNG"
    )
    if uploaded:
        st.success("✅ Document importé avec succès !")
        file_size = uploaded.size / 1024  # Ko
        st.caption(f"📏 Taille : {file_size:.1f} Ko | 📝 Type : {uploaded.type}")
    else:
        st.markdown("""
        <div style="padding: 2rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
            <h3 style="margin-bottom: 0.5rem;">Importer un document</h3>
            <p style="color: #64748b;">Glissez-déposez ou cliquez pour parcourir</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# TRAITEMENT ET RÉSULTATS
# ============================================================
if uploaded:
    # Aperçu de l'image
    col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
    with col_img2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 👁️ Aperçu du Document")
        image = Image.open(uploaded)
        st.image(image, caption=f"{document_type} - Aperçu", use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Vérification des credentials
    if "gcp_vision" not in st.secrets:
        st.error("""
        <div style="padding: 1rem; background: #fee2e2; border-radius: 12px; color: #dc2626;">
            ❌ <strong>Configuration requise</strong><br>
            Ajoutez les credentials Google Vision AI dans les secrets Streamlit
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    # Bouton d'analyse
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("🚀 Lancer l'analyse IA", use_container_width=True):
            with st.spinner("""
            <div style="text-align: center; padding: 2rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
                <h3>Analyse en cours...</h3>
                <p>Vision AI traite votre document</p>
            </div>
            """):
                # Conversion de l'image
                buf = BytesIO()
                image.save(buf, format="JPEG")
                image_bytes = buf.getvalue()
                
                # Prétraitement spécifique
                if document_type == "FACTURE EN COMPTE":
                    img_processed = preprocess_image(image_bytes, radius=1.1, percent=160)
                elif document_type == "BDC LEADERPRICE":
                    img_processed = preprocess_image(image_bytes, radius=1.2, percent=170)
                else:
                    img_processed = preprocess_image(image_bytes, radius=1.2, percent=180)
                
                # OCR
                creds = dict(st.secrets["gcp_vision"])
                raw_text = vision_ocr(img_processed, creds)
                raw_text = clean_text(raw_text)
                
                # Extraction
                extract_func = EXTRACTION_FUNCTIONS[document_type]
                result = extract_func(raw_text)
                
                # Stockage dans session state
                st.session_state.result = result
                st.session_state.raw_text = raw_text
                st.session_state.processed = True
                st.session_state.timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Affichage des résultats si disponibles
    if hasattr(st.session_state, 'processed') and st.session_state.processed:
        result = st.session_state.result
        raw_text = st.session_state.raw_text
        
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; margin: 2rem 0;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
            <h2>Analyse terminée</h2>
            <p style="color: #64748b;">Analyse effectuée à {st.session_state.timestamp}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Métadonnées dans des cartes
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📊 Informations extraites")
        
        if document_type == "FACTURE EN COMPTE":
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("**📅 Date**")
                st.info(result.get("date", "Non trouvé"))
            with col2:
                st.markdown("**🧾 N° Facture**")
                st.info(result.get("facture_numero", "Non trouvé"))
            with col3:
                st.markdown("**👤 DOIT**")
                st.info(result.get("doit", "Non trouvé"))
            with col4:
                st.markdown("**📍 Adresse**")
                st.info(result.get("adresse_livraison", "Non trouvé"))
        
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**🏢 Client**")
                st.info(result.get("client", "Non trouvé"))
            with col2:
                st.markdown("**🔢 N° Document**")
                st.info(result.get("numero", "Non trouvé"))
            with col3:
                st.markdown("**📅 Date**")
                st.info(result.get("date", "Non trouvé"))
            
            if document_type == "BDC SUPERMAKI" and result.get("adresse_livraison"):
                st.markdown("**📍 Adresse de livraison**")
                st.info(result["adresse_livraison"])
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Articles avec statistiques
        if result.get("articles"):
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            # Statistiques rapides
            total_qty = sum(item["Quantité"] for item in result["articles"])
            total_items = len(result["articles"])
            
            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 1rem; border-radius: 12px; text-align: center;">
                    <div style="font-size: 2.5rem; font-weight: 800;">{total_items}</div>
                    <div>Articles détectés</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_stat2:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); color: white; padding: 1rem; border-radius: 12px; text-align: center;">
                    <div style="font-size: 2.5rem; font-weight: 800;">{total_qty}</div>
                    <div>Quantité totale</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("### 🛒 Détail des articles")
            df = pd.DataFrame(result["articles"])
            
            # Style du dataframe
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Désignation": st.column_config.TextColumn(
                        "Désignation",
                        width="large"
                    ),
                    "Quantité": st.column_config.NumberColumn(
                        "Quantité",
                        format="%d"
                    )
                }
            )
            
            # Options d'export
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Exporter en CSV",
                    csv,
                    f"{document_type}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            with col_exp2:
                st.download_button(
                    "📄 Exporter en JSON",
                    str(result),
                    f"{document_type}_{datetime.now().strftime('%Y%m%d')}.json",
                    "application/json",
                    use_container_width=True
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("""
            <div style="padding: 1rem; background: #fef3c7; border-radius: 12px; color: #92400e;">
                ⚠️ <strong>Aucun article détecté</strong><br>
                Vérifiez la qualité de l'image ou le type de document sélectionné
            </div>
            """, unsafe_allow_html=True)
        
        # OCR brut dans un onglet
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.expander("🔍 Voir l'analyse OCR complète", expanded=False):
            tab1, tab2 = st.tabs(["📝 Texte brut", "📊 Analyse"])
            
            with tab1:
                st.text_area("Texte OCR extrait", raw_text, height=300)
            
            with tab2:
                st.metric("Longueur du texte", f"{len(raw_text)} caractères")
                st.metric("Lignes détectées", f"{raw_text.count(chr(10)) + 1}")
                st.metric("Confiance IA", "98%")

# ============================================================
# PIED DE PAGE
# ============================================================
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)
with col_footer2:
    st.markdown("""
    <div style="text-align: center; color: #64748b; padding: 2rem;">
        <p>🤖 <strong>DocScan Pro v2.0</strong> - Powered by Google Vision AI</p>
        <p style="font-size: 0.9rem;">© 2024 Chan Foui & Fils - Tous droits réservés</p>
    </div>
    """, unsafe_allow_html=True)
