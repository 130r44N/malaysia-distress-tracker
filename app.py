import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Malaysia Distress Sales Tracker", layout="wide")

st.title("🛡️ Malaysia Distress Sales Tracker")
st.markdown("**Nationwide Adjustable Tracker • Properties & Vehicles • Fuel Prices**")

# ================== FUEL PRICES WIDGET (BUDI vs Non-BUDI) ==================
st.subheader("⛽ Current Malaysia Fuel Prices (26 Mar – 1 Apr 2026)")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("RON95 BUDI95 (Subsidised)", "RM1.99", "unchanged")
    st.metric("RON95 (Unsubsidised / Non-BUDI)", "RM3.87", "+60 sen")

with col2:
    st.metric("RON97", "RM5.15", "+60 sen")

with col3:
    st.metric("Diesel - Peninsular Malaysia", "RM5.52", "+80 sen")
    st.metric("Diesel - East Malaysia", "RM2.15", "unchanged")

st.caption("Source: Ministry of Finance / PETRONAS • Updated weekly")

# Placeholder for future features
st.info("📍 Location selector and scanning features will be added in the next phase.")

st.caption("Repository: malaysia-distress-tracker • Built step by step")
