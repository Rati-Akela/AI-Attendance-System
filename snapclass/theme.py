"""Look and feel: the original SNAP CLASS palette (blurple / pink / lavender)."""

import streamlit as st

PRIMARY = "#5865F2"
ACCENT = "#EB459E"
LAVENDER = "#E0E3FF"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Climate+Crisis:YEAR@1979&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300..800&display=swap');

#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 2rem !important; max-width: 1150px; }}

/* Target text elements only - a blanket rule would also hit <span> icon glyphs
   (Material Symbols) and turn the sidebar icons into words. */
p, label, li, a, input, textarea, button, th, td, h2, h3, h4,
[data-testid="stMetricLabel"] {{ font-family: 'Outfit', sans-serif; }}
h1 {{ font-family: 'Climate Crisis', 'Outfit', sans-serif !important;
      font-size: 2.6rem !important; line-height: 1.1 !important; color: {PRIMARY}; }}
h2, h3 {{ font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; }}

div.stButton > button, div.stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {{
    border-radius: 1.5rem; padding: .45rem 1.4rem; font-weight: 600;
    transition: transform .2s ease-in-out;
}}
div.stButton > button:hover, div.stDownloadButton > button:hover {{ transform: scale(1.04); }}

div[data-testid="stMetric"] {{
    background: {LAVENDER}; border-radius: 1.2rem; padding: 1rem 1.2rem;
}}
div[data-testid="stMetricValue"] {{ color: {PRIMARY}; font-weight: 800; }}
.snap-hero {{ color: #4b4f66; font-size: 1.15rem; margin: -0.4rem 0 1.4rem; }}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
