# CSS personnalisé - DESIGN ULTRA LISIBLE
st.markdown(f"""
<style>
    /* Design général - FOND CLAIR POUR MAXIMUM DE LISIBILITÉ */
    .main {{
        background: {PALETTE['background']};
    }}
    
    .stApp {{
        background: {PALETTE['background']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
    }}
    
    /* Header élégant avec titre en majuscules noires */
    .header-container {{
        background: {PALETTE['card_bg']};
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(39, 65, 74, 0.08);
        text-align: center;
        border: 1px solid {PALETTE['border']};
    }}
    
    .logo-title-wrapper {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.2rem;
        margin-bottom: 0.5rem;
    }}
    
    .logo-img {{
        height: 100px;
        width: auto;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        border-radius: 12px;
        padding: 8px;
        background: {PALETTE['card_bg']};
    }}
    
    .brand-title {{
        color: {PALETTE['text_dark']} !important;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: 1px;
        text-transform: uppercase;
        line-height: 1.2;
    }}
    
    .brand-sub {{
        color: {PALETTE['text_medium']} !important;
        font-size: 1.1rem;
        margin-top: 0.2rem;
        font-weight: 400;
        opacity: 0.9;
    }}
    
    /* Sous-titre document */
    .document-title {{
        background: {PALETTE['primary_dark']};
        color: {PALETTE['card_bg']} !important;
        padding: 1.2rem 2rem;
        border-radius: 16px;
        font-weight: 700;
        font-size: 1.4rem;
        text-align: center;
        margin: 1.5rem 0 2rem 0;
        box-shadow: 0 4px 12px rgba(39, 65, 74, 0.15);
        border: none;
    }}
    
    /* Cartes avec fond blanc pour lisibilité optimale */
    .card {{
        background: {PALETTE['card_bg']};
        padding: 2rem;
        border-radius: 18px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        margin-bottom: 1.8rem;
        border: 1px solid {PALETTE['border']};
        transition: all 0.2s ease;
    }}
    
    .card:hover {{
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }}
    
    .card h4 {{
        color: {PALETTE['text_dark']} !important;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        border-bottom: 2px solid {PALETTE['accent']};
        padding-bottom: 0.8rem;
    }}
    
    /* Boutons avec bon contraste */
    .stButton > button {{
        background: {PALETTE['primary_dark']};
        color: {PALETTE['card_bg']} !important;
        font-weight: 600;
        border: 1px solid {PALETTE['primary_dark']};
        padding: 0.9rem 1.8rem;
        border-radius: 12px;
        transition: all 0.2s ease;
        width: 100%;
        font-size: 1rem;
    }}
    
    .stButton > button:hover {{
        background: {PALETTE['primary_light']};
        border-color: {PALETTE['primary_light']};
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(39, 65, 74, 0.2);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
    }}
    
    /* Zone de dépôt */
    .upload-box {{
        border: 2px dashed {PALETTE['accent']};
        border-radius: 18px;
        padding: 3rem;
        text-align: center;
        background: {PALETTE['card_bg']};
        margin: 1.5rem 0;
        transition: all 0.3s ease;
    }}
    
    .upload-box:hover {{
        background: {PALETTE['hover']};
        border-color: {PALETTE['primary_dark']};
    }}
    
    /* Barre de progression */
    .progress-container {{
        background: {PALETTE['primary_dark']};
        color: {PALETTE['card_bg']} !important;
        padding: 2.5rem;
        border-radius: 18px;
        text-align: center;
        margin: 2rem 0;
        box-shadow: 0 4px 20px rgba(39, 65, 74, 0.15);
    }}
    
    /* Sélecteur de document - TEXTE BLANC */
    .doc-selector {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.2rem;
        margin: 2rem 0;
    }}
    
    .doc-option {{
        background: {PALETTE['primary_dark']};      /* Fond bleu foncé */
        color: {PALETTE['card_bg']} !important;     /* Texte blanc */
        padding: 1.8rem 1.2rem;
        border-radius: 16px;
        border: 1px solid {PALETTE['primary_dark']};
        transition: all 0.2s ease;
        cursor: pointer;
        text-align: center;
        box-shadow: 0 3px 10px rgba(39, 65, 74, 0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        min-height: 130px;
    }}
    
    .doc-option:hover {{
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(39, 65, 74, 0.2);
        border-color: {PALETTE['accent']};
        background: {PALETTE['primary_light']};     /* Fond bleu plus foncé au hover */
        color: {PALETTE['card_bg']} !important;     /* Texte blanc */
    }}
    
    .doc-option.selected {{
        background: {PALETTE['accent']};            /* Fond bleu accent */
        color: {PALETTE['card_bg']} !important;     /* Texte blanc */
        border-color: {PALETTE['accent']};
        box-shadow: 0 6px 20px rgba(44, 95, 115, 0.3);
    }}
    
    /* Texte dans les boutons de document */
    .doc-option .stButton > button div {{
        color: {PALETTE['card_bg']} !important;
    }}
    
    /* Image preview permanent */
    .image-preview-container {{
        background: {PALETTE['card_bg']};
        border-radius: 18px;
        padding: 1.8rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        margin-bottom: 2rem;
        border: 1px solid {PALETTE['border']};
    }}
    
    /* Alertes avec bon contraste */
    .info-box {{
        background: #E8F4F8;
        border-left: 4px solid {PALETTE['accent']};
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: {PALETTE['text_dark']} !important;
    }}
    
    .success-box {{
        background: #E8F5E9;
        border-left: 4px solid {PALETTE['success']};
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: {PALETTE['text_dark']} !important;
    }}
    
    .warning-box {{
        background: #FFF3E0;
        border-left: 4px solid {PALETTE['warning']};
        padding: 1.2rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Champs de formulaire */
    .stTextInput > div > div > input {{
        border: 1px solid {PALETTE['border']};
        border-radius: 10px;
        padding: 0.75rem 1rem;
        font-size: 1rem;
        color: {PALETTE['text_dark']} !important;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: {PALETTE['accent']};
        box-shadow: 0 0 0 2px rgba(44, 95, 115, 0.1);
    }}
    
    /* Labels toujours noirs pour lisibilité */
    label {{
        color: {PALETTE['text_dark']} !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
    }}
    
    /* Textes dans l'application */
    p, span, div {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    .stMarkdown p, .stMarkdown li {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Data Editor */
    .stDataFrame {{
        border: 1px solid {PALETTE['border']};
        border-radius: 12px;
    }}
    
    /* Boutons secondaires (Changer de type, Recommencer) */
    .stButton > button[data-testid="baseButton-secondary"] {{
        background: {PALETTE['accent']} !important;
        color: {PALETTE['card_bg']} !important;
        border: 1px solid {PALETTE['accent']} !important;
    }}
    
    .stButton > button[data-testid="baseButton-secondary"]:hover {{
        background: {PALETTE['primary_light']} !important;
        border-color: {PALETTE['primary_light']} !important;
        color: {PALETTE['card_bg']} !important;
    }}
    
    /* Responsive Design */
    @media (max-width: 768px) {{
        .header-container {{
            padding: 1.5rem;
            margin: 1rem 0.5rem;
        }}
        
        .brand-title {{
            font-size: 2rem;
        }}
        
        .logo-img {{
            height: 80px;
        }}
        
        .brand-sub {{
            font-size: 1rem;
        }}
        
        .document-title {{
            font-size: 1.2rem;
            padding: 1rem 1.5rem;
            margin: 1rem 0.5rem 1.5rem 0.5rem;
        }}
        
        .doc-option {{
            min-height: 110px;
            padding: 1.5rem 1rem;
        }}
        
        .card {{
            padding: 1.5rem;
            margin: 0.5rem;
            border-radius: 16px;
        }}
        
        .upload-box {{
            padding: 2rem;
            margin: 1rem;
        }}
        
        .stButton > button {{
            padding: 0.8rem 1.5rem;
            font-size: 0.95rem;
        }}
        
        .image-preview-container {{
            margin: 1rem 0.5rem;
            padding: 1.5rem;
        }}
    }}
    
    @media (max-width: 480px) {{
        .brand-title {{
            font-size: 1.6rem;
        }}
        
        .logo-img {{
            height: 70px;
        }}
        
        .doc-selector {{
            grid-template-columns: 1fr;
        }}
        
        .doc-option {{
            min-height: 100px;
        }}
        
        .brand-sub {{
            font-size: 0.9rem;
        }}
        
        .card {{
            padding: 1.2rem;
        }}
    }}
    
    /* Amélioration de la visibilité des icônes dans les boutons */
    .stButton > button div {{
        color: {PALETTE['card_bg']} !important;
        font-weight: 600;
    }}
    
    /* Styles spécifiques pour les éléments Streamlit */
    .st-bb {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    .css-1d391kg p {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Contraste amélioré pour toutes les sections */
    section.main > div {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Meilleur contraste pour les textes dans les boutons */
    .stButton > button span {{
        color: {PALETTE['card_bg']} !important;
        font-weight: 600;
    }}
    
    /* Style pour les textes d'erreur/succès */
    .stAlert {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    .st-emotion-cache-1q7spjk p {{
        color: {PALETTE['text_dark']} !important;
    }}
    
    /* Spécifique pour garantir que les textes dans les boutons de sélection sont blancs */
    button[data-testid="stButton"] div p,
    button[data-testid="stButton"] div {{
        color: {PALETTE['card_bg']} !important;
    }}
    
    /* Style pour les boutons de navigation */
    div[data-testid="column"] button {{
        color: {PALETTE['card_bg']} !important;
    }}
    
    /* S'assurer que tous les textes dans les boutons sont blancs */
    .stButton button, 
    .stButton button span,
    .stButton button div,
    .stButton button p {{
        color: {PALETTE['card_bg']} !important;
    }}
</style>
""", unsafe_allow_html=True)
