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
st.markdown("**Nationwide • Adjustable Locations • Automatic History**")

# ================== ADMIN AUTHENTICATION ==================
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "change_me_in_secrets")

# Login / Logout Area
if st.session_state.admin_authenticated:
    col1, col2 = st.columns([5, 1])
    with col1:
        st.success("✅ Logged in as Admin")
    with col2:
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.admin_authenticated = False
            st.rerun()
else:
    password_input = st.text_input("🔑 Admin Password (to edit fuel prices)", type="password", key="pw_input")
    if password_input:
        if password_input == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.success("✅ Admin access granted")
            st.rerun()
        else:
            st.error("❌ Wrong password")

# ================== FUEL PRICES + HISTORY ==================
FUEL_FILE = "fuel_prices.json"
FUEL_HISTORY_FILE = "fuel_history.csv"

if "fuel_prices" not in st.session_state:
    try:
        with open(FUEL_FILE, "r") as f:
            st.session_state.fuel_prices = json.load(f)
    except:
        st.session_state.fuel_prices = {
            "budi95": "RM1.99", "non_budi95": "RM3.87", "ron97": "RM5.15",
            "diesel_peninsular": "RM5.52", "diesel_east": "RM2.15",
            "last_updated": "26 Mar – 1 Apr 2026"
        }

if "fuel_history_df" not in st.session_state:
    try:
        st.session_state.fuel_history_df = pd.read_csv(FUEL_HISTORY_FILE)
    except:
        st.session_state.fuel_history_df = pd.DataFrame(columns=["date", "budi95", "non_budi95", "ron97", 
                                                                 "diesel_peninsular", "diesel_east", "last_updated"])

# Current Fuel Display
st.subheader("⛽ Current Malaysia Fuel Prices")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("RON95 BUDI95 (Subsidised)", st.session_state.fuel_prices["budi95"])
    st.metric("RON95 (Unsubsidised / Non-BUDI)", st.session_state.fuel_prices["non_budi95"])
with col2:
    st.metric("RON97", st.session_state.fuel_prices["ron97"])
with col3:
    st.metric("Diesel - Peninsular", st.session_state.fuel_prices["diesel_peninsular"])
    st.metric("Diesel - East Malaysia", st.session_state.fuel_prices["diesel_east"])
st.caption(f"Last updated: {st.session_state.fuel_prices['last_updated']}")

# Fuel Editor
if st.session_state.admin_authenticated:
    st.subheader("✏️ Edit Fuel Prices (Admin Only)")
    with st.form("fuel_form"):
        budi95 = st.text_input("RON95 BUDI95 (Subsidised)", st.session_state.fuel_prices["budi95"])
        non_budi95 = st.text_input("RON95 (Unsubsidised / Non-BUDI)", st.session_state.fuel_prices["non_budi95"])
        ron97 = st.text_input("RON97", st.session_state.fuel_prices["ron97"])
        diesel_pen = st.text_input("Diesel - Peninsular", st.session_state.fuel_prices["diesel_peninsular"])
        diesel_east = st.text_input("Diesel - East Malaysia", st.session_state.fuel_prices["diesel_east"])
        last_updated = st.text_input("Last Updated", st.session_state.fuel_prices["last_updated"])
        
        submitted = st.form_submit_button("💾 Save Fuel Prices")
        if submitted:
            st.session_state.fuel_prices = {
                "budi95": budi95, "non_budi95": non_budi95, "ron97": ron97,
                "diesel_peninsular": diesel_pen, "diesel_east": diesel_east,
                "last_updated": last_updated
            }
            with open(FUEL_FILE, "w") as f:
                json.dump(st.session_state.fuel_prices, f)
            
            # Save to fuel history
            new_row = pd.DataFrame([{
                "date": datetime.now().strftime("%d-%b-%Y %H:%M"),
                "budi95": budi95,
                "non_budi95": non_budi95,
                "ron97": ron97,
                "diesel_peninsular": diesel_pen,
                "diesel_east": diesel_east,
                "last_updated": last_updated
            }])
            st.session_state.fuel_history_df = pd.concat([st.session_state.fuel_history_df, new_row], ignore_index=True)
            st.session_state.fuel_history_df.to_csv(FUEL_HISTORY_FILE, index=False)
            
            st.success("✅ Fuel prices updated and saved to history!")
            st.rerun()

# ================== LISTINGS CONFIG & SCAN ==================
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

st.sidebar.header("🎛️ Monitoring Settings")
selected_locations = st.sidebar.multiselect(
    "Select locations to track",
    options=list(LOCATIONS.keys()),
    default=["Bintulu (Sarawak)", "Miri (Sarawak)"]
)

track_properties = st.sidebar.checkbox("Track Properties", value=True)
track_vehicles = st.sidebar.checkbox("Track Vehicles", value=True)

run_button = st.sidebar.button("🚀 Run Fresh Scan Now", type="primary")

# Listings History
CSV_FILE = "history.csv"
if "history_df" not in st.session_state:
    try:
        st.session_state.history_df = pd.read_csv(CSV_FILE)
    except:
        st.session_state.history_df = pd.DataFrame(columns=[
            "date", "location", "category", "total", "private", "new_24h", 
            "distress_ads", "median_price", "risk_score"
        ])

def save_history():
    st.session_state.history_df.to_csv(CSV_FILE, index=False)

def scrape_mudah(location_slug, category):
    if category == "Properties":
        url = f"https://www.mudah.my/{location_slug}/properties-for-sale"
    else:
        url = f"https://www.mudah.my/{location_slug}/cars-for-sale"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        total_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:result|listing|found|ads)', r.text, re.I)
        total = int(total_match.group(1).replace(',', '')) if total_match else 0
        distress_count = sum(1 for kw in KEYWORDS if kw in r.text.lower())
        return {
            "total": total,
            "private": 0,
            "new_24h": 0,
            "distress_ads": min(distress_count, 15),
            "median_price": None
        }
    except:
        return {"total": 0, "private": 0, "new_24h": 0, "distress_ads": 0, "median_price": None}

if run_button and selected_locations:
    with st.spinner("Scanning Mudah.my..."):
        today = datetime.now().strftime("%d-%b-%Y")
        new_rows = []
        for loc_display in selected_locations:
            slug = LOCATIONS[loc_display]
            if track_properties:
                data = scrape_mudah(slug, "Properties")
                risk = "High" if data["distress_ads"] > 5 else "Medium" if data["distress_ads"] > 2 else "Low"
                new_rows.append({"date": today, "location": loc_display, "category": "Properties", **data, "risk_score": risk})
            if track_vehicles:
                data = scrape_mudah(slug, "Vehicles")
                risk = "High" if data["distress_ads"] > 5 else "Medium" if data["distress_ads"] > 2 else "Low"
                new_rows.append({"date": today, "location": loc_display, "category": "Vehicles", **data, "risk_score": risk})
        
        if new_rows:
            st.session_state.history_df = pd.concat([st.session_state.history_df, pd.DataFrame(new_rows)], ignore_index=True)
            save_history()
            st.success(f"✅ Scan completed for {len(selected_locations)} location(s)")

# ================== TABS ==================
tab1, tab2, tab3 = st.tabs(["📊 Live Dashboard", "📈 Listings History", "⛽ Fuel History"])

with tab1:
    st.header("Today's Results")
    if not st.session_state.history_df.empty:
        today_str = datetime.now().strftime("%d-%b-%Y")
        today_df = st.session_state.history_df[st.session_state.history_df["date"] == today_str]
        for loc in selected_locations:
            st.subheader(f"📍 {loc}")
            loc_df = today_df[today_df["location"] == loc]
            if not loc_df.empty:
                st.dataframe(loc_df.style.apply(
                    lambda x: ["background: #ffcccc" if v == "High" else "background: #fff3cc" if v == "Medium" else "" for v in x], 
                    axis=1), hide_index=True)

with tab2:
    st.header("Listings History & Trends")
    if not st.session_state.history_df.empty:
        st.dataframe(st.session_state.history_df.sort_values("date", ascending=False))
        fig = px.line(st.session_state.history_df, x="date", y="total", color="location", title="Total Listings Trend")
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("📥 Download Listings History", st.session_state.history_df.to_csv(index=False), "listings_history.csv")
    else:
        st.info("Run scans to build listings history.")

with tab3:
    st.header("⛽ Fuel Price History")
    if not st.session_state.fuel_history_df.empty:
        st.dataframe(st.session_state.fuel_history_df.sort_values("date", ascending=False))
        st.download_button("📥 Download Fuel History", st.session_state.fuel_history_df.to_csv(index=False), "fuel_history.csv")
    else:
        st.info("Save fuel prices a few times to build fuel history.")

st.caption("Phase 9 • Logout fixed • Fuel history included")
