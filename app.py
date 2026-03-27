import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import plotly.express as px
import re
import json

st.set_page_config(page_title="Malaysia Distress Sales Tracker", layout="wide")

st.title("🛡️ Malaysia Distress Sales Tracker")
st.markdown("**Nationwide • Adjustable • Per-Location Graphs**")

# ================== ADMIN ==================
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "change_me_in_secrets")

col1, col2 = st.columns([5, 1])
with col1:
    if st.session_state.admin_authenticated:
        st.success("✅ Logged in as Admin")
    else:
        pw = st.text_input("🔑 Admin Password", type="password")
        if pw:
            if pw == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Wrong password")

with col2:
    if st.session_state.admin_authenticated and st.button("🚪 Logout"):
        st.session_state.admin_authenticated = False
        st.rerun()

# ================== FUEL (unchanged) ==================
FUEL_FILE = "fuel_prices.json"
if "fuel_prices" not in st.session_state:
    try:
        with open(FUEL_FILE, "r") as f:
            st.session_state.fuel_prices = json.load(f)
    except:
        st.session_state.fuel_prices = {"budi95": "RM1.99", "non_budi95": "RM3.87", "ron97": "RM5.15",
                                        "diesel_peninsular": "RM5.52", "diesel_east": "RM2.15",
                                        "last_updated": "26 Mar – 1 Apr 2026"}

st.subheader("⛽ Current Fuel Prices")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("BUDI95", st.session_state.fuel_prices["budi95"])
    st.metric("Non-BUDI RON95", st.session_state.fuel_prices["non_budi95"])
with c2:
    st.metric("RON97", st.session_state.fuel_prices["ron97"])
with c3:
    st.metric("Diesel Peninsular", st.session_state.fuel_prices["diesel_peninsular"])
    st.metric("Diesel East", st.session_state.fuel_prices["diesel_east"])

# Fuel Editor (Admin only)
if st.session_state.admin_authenticated:
    st.subheader("Edit Fuel Prices")
    with st.form("fuel_form"):
        budi = st.text_input("BUDI95", st.session_state.fuel_prices["budi95"])
        nonbudi = st.text_input("Non-BUDI RON95", st.session_state.fuel_prices["non_budi95"])
        ron97 = st.text_input("RON97", st.session_state.fuel_prices["ron97"])
        dpen = st.text_input("Diesel Peninsular", st.session_state.fuel_prices["diesel_peninsular"])
        deast = st.text_input("Diesel East", st.session_state.fuel_prices["diesel_east"])
        updated = st.text_input("Last Updated", st.session_state.fuel_prices["last_updated"])
        
        if st.form_submit_button("Save"):
            st.session_state.fuel_prices = {"budi95": budi, "non_budi95": nonbudi, "ron97": ron97,
                                            "diesel_peninsular": dpen, "diesel_east": deast, "last_updated": updated}
            with open(FUEL_FILE, "w") as f:
                json.dump(st.session_state.fuel_prices, f)
            st.success("Saved!")
            st.rerun()

# ================== LISTINGS ==================
KEYWORDS = ["urgent", "cepat jual", "terdesak", "jual murah", "harga rendah", 
            "motivated seller", "quick sale", "must sell", "owner needs cash", "distress"]

LOCATIONS = {
    "Bintulu (Sarawak)": "sarawak-bintulu",
    "Miri (Sarawak)": "sarawak-miri",
    "Kuching (Sarawak)": "sarawak-kuching",
    "Kota Kinabalu (Sabah)": "sabah-kota-kinabalu",
    "Kuala Lumpur": "kuala-lumpur",
    "Selangor": "selangor",
    "Penang": "penang",
    "Johor": "johor",
    "Malaysia (Nationwide)": "malaysia"
}

st.sidebar.header("Settings")
selected_locations = st.sidebar.multiselect("Select locations", list(LOCATIONS.keys()), default=["Bintulu (Sarawak)", "Miri (Sarawak)"])
track_prop = st.sidebar.checkbox("Properties", True)
track_veh = st.sidebar.checkbox("Vehicles", True)
run_button = st.sidebar.button("🚀 Run Fresh Scan Now", type="primary")

# History
CSV_FILE = "history.csv"
if "history_df" not in st.session_state:
    try:
        st.session_state.history_df = pd.read_csv(CSV_FILE)
    except:
        st.session_state.history_df = pd.DataFrame(columns=["date", "location", "category", "total", "distress_ads", "risk_score"])

def scrape_mudah(slug, cat):
    url = f"https://www.mudah.my/{slug}/{'properties-for-sale' if cat=='Properties' else 'cars-for-sale'}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        total_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:result|listing)', r.text, re.I)
        total = int(total_match.group(1).replace(',','')) if total_match else 0
        distress = sum(1 for k in KEYWORDS if k in r.text.lower())
        return {"total": total, "distress_ads": min(distress, 15)}
    except:
        return {"total": 0, "distress_ads": 0}

if run_button and selected_locations:
    with st.spinner("Scanning..."):
        today = datetime.now().strftime("%d-%b-%Y")
        new_rows = []
        for loc in selected_locations:
            slug = LOCATIONS[loc]
            if track_prop:
                d = scrape_mudah(slug, "Properties")
                risk = "High" if d["distress_ads"] > 5 else "Medium" if d["distress_ads"] > 2 else "Low"
                new_rows.append({"date": today, "location": loc, "category": "Properties", "total": d["total"], "distress_ads": d["distress_ads"], "risk_score": risk})
            if track_veh:
                d = scrape_mudah(slug, "Vehicles")
                risk = "High" if d["distress_ads"] > 5 else "Medium" if d["distress_ads"] > 2 else "Low"
                new_rows.append({"date": today, "location": loc, "category": "Vehicles", "total": d["total"], "distress_ads": d["distress_ads"], "risk_score": risk})
        if new_rows:
            st.session_state.history_df = pd.concat([st.session_state.history_df, pd.DataFrame(new_rows)], ignore_index=True)
            st.session_state.history_df.to_csv(CSV_FILE, index=False)
            st.success("Scan completed!")

# ================== TABS ==================
tab1, tab2, tab3, tab4 = st.tabs(["Today", "Trends per Location", "Listings History", "Fuel History"])

with tab1:
    st.header("Today's Results")
    today_str = datetime.now().strftime("%d-%b-%Y")
    today_df = st.session_state.history_df[st.session_state.history_df["date"] == today_str] if not st.session_state.history_df.empty else pd.DataFrame()
    for loc in selected_locations:
        st.subheader(loc)
        df_loc = today_df[today_df["location"] == loc]
        if not df_loc.empty:
            st.dataframe(df_loc, hide_index=True)

with tab2:
    st.header("📈 Trends per Location")
    if not st.session_state.history_df.empty:
        for loc in selected_locations:
            loc_df = st.session_state.history_df[st.session_state.history_df["location"] == loc]
            if not loc_df.empty:
                st.subheader(f"{loc}")
                fig = px.line(loc_df, x="date", y="total", color="category", 
                              title=f"{loc} - Properties vs Vehicles", markers=True)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run scans to see per-location trends.")

with tab3:
    st.header("Listings History")
    if not st.session_state.history_df.empty:
        st.dataframe(st.session_state.history_df.sort_values("date", ascending=False), hide_index=True)

with tab4:
    st.header("Fuel History")
    if "fuel_history_df" in st.session_state and not st.session_state.fuel_history_df.empty:
        st.dataframe(st.session_state.fuel_history_df.sort_values("date", ascending=False), hide_index=True)
    else:
        st.info("No fuel changes yet.")

st.caption("Phase 11 • Graphs now separated by Location • Each location has its own Properties vs Vehicles graph")
