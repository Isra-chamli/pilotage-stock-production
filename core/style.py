import streamlit as st

def appliquer_style():
    st.markdown("""
        <style>
        /* Fond bleu marine UNIQUEMENT sur la sidebar */
        [data-testid="stSidebar"] {
            background-color: #1B2B4B;
        }

        /* Texte blanc dans la sidebar */
        [data-testid="stSidebar"] * {
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)