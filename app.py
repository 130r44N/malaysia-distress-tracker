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
st.markdown("**Nationwide • Adjustable • Automatic History & Comparison**")

# ================== ADMIN AUTHENTICATION ==================
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "change_me_in_secrets")

col1, col2 = st.columns([5, 1])
with col1:
    if st.session_state.admin_authenticated:
        st.success("✅ Logged in as Admin")
    else:
        password_input = st.text_input("🔑 Admin Password", type="password", key="pw_input")
        if password_input:
            if password_input == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("✅ Admin access granted")
                st.rerun()
            else:
                st.error("❌ Wrong password")

with col2:
    if st.session_state.admin_authenticated:
        if st.button("🚪 Logout"):
            st.session_state.admin_authenticated = False
            st.rerun()

# ================== FUEL PRICES + FUEL HISTORY ==================
FUEL_FILE = "fuel_prices.json"
FUEL_HISTORY_FILE = "fuel_history.csv"

if "fuel_prices" not in st.session_state:
    try:
        with open(FUEL_FILE, "r") as f:
            st.session_state.fuel_prices = json.load(f)
    except:
        st.session_state.fuel_prices = {"budi95": "RM1.99", "non_budi95": "RM3.87", "ron97": "RM5.15",
                                        "diesel_peninsular": "RM5.52", "diesel_east": "RM2.15",
                                        "last_updated": "26 Mar – 1 Apr 2026"}

if "fuel_history_df" not in st.session_state:
    try:
        st.session_state.fuel_history_df = pd.read_csv(FUEL_HISTORY_FILE)
    except:
        st.session_state.fuel_history_df = pd.DataFrame(columns=["date", "budi95", "non_budi95", "ron97", "diesel_peninsular", "diesel_east", "last_updated"])

# Fuel Display
st.subheader("⛽ Current Malaysia Fuel Prices")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("RON95 BUDI95", st.session_state.fuel_prices["budi95"])
    st.metric("RON95 Non-BUDI", st.session_state.fuel_prices["non_budi95"])
with c2:
    st.metric("RON97", st.session_state.fuel_prices["ron97"])
with c3:
    st.metric("Diesel Peninsular", st.session_state.fuel_prices["diesel_peninsular"])
    st.metric("Diesel East", st.session_state.fuel_prices["diesel_east"])
st.caption(f"Last updated: {st.session_state.fuel_prices['last_updated']}")

if st.session_state.admin_authenticated:
    st.subheader("✏️ Edit Fuel Prices")
    with st.form("fuel_form"):
        budi = st.text_input("BUDI95", st.session_state.fuel_prices["budi95"])
        nonbudi = st.text_input("Non-BUDI RON95", st.session_state.fuel_prices["non_budi95"])
        ron97 = st.text_input("RON97", st.session_state.fuel_prices["ron97"])
        d_pen = st.text_input("Diesel Peninsular", st.session_state.fuel_prices["diesel_peninsular"])
        d_east = st.text_input("Diesel East", st.session_state.fuel_prices["diesel_east"])
        updated = st.text_input("Last Updated", st.session_state.fuel_prices["last_updated"])
        
        if st.form_submit_button("Save Fuel Prices"):
            st.session_state.fuel_prices = {"budi95": budi, "non_budi95": nonbudi, "ron97": ron97,
                                            "diesel_peninsular": d_pen, "diesel_east": d_east, "last_updated": updated}
            with open(FUEL_FILE, "w") as f:
                json.dump(st.session_state.fuel_prices, f)
            
            new_row = pd.DataFrame([{"date": datetime.now().strftime("%d-%b-%Y %H:%M"), **st.session_state.fuel_prices}])
            st.session_state.fuel_history_df = pd.concat([st.session_state.fuel_history_df, new_row], ignore_index=True)
            st.session_state.fuel_history_df.to_csv(FUEL_HISTORY_FILE, index=False)
            st.success("Fuel prices saved!")
            st.rerun()

# ================== LISTINGS TRACKING ==================
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
selected_locations = st.sidebar.multiselect("Select locations", options=list(LOCATIONS.keys()), default=["Bintulu (Sarawak)", "Miri (Sarawak)"])
track_prop = st.sidebar.checkbox("Track Properties", value=True)
track_veh = st.sidebar.checkbox("Track Vehicles", value=True)
run_button = st.sidebar.button("🚀 Run Fresh Scan Now", type="primary")

CSV_FILE = "history.csv"
if "history_df" not in st.session_state:
    try:
        st.session_state.history_df = pd.read_csv(CSV_FILE)
    except:
        st.session_state.history_df = pd.DataFrame(columns=["date","location","category","total","distress_ads","risk_score"])

def scrape_mudah(slug, category):
    url = f"https://www.mudah.my/{slug}/{'properties-for-sale' if category=='Properties' else 'cars-for-sale'}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        total_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:result|listing)', r.text, re.I)
        total = int(total_match.group(1).replace(',','')) if total_match else 0
        distress = sum(1 for kw in KEYWORDS if kw in r.text.lower())
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
                data = scrape_mudah(slug, "Properties")
                risk = "High" if data["distress_ads"] > 5 else "Medium" if data["distress_ads"] > 2 else "Low"
                new_rows.append({"date": today, "location": loc, "category": "Properties", "total": data["total"], "distress_ads": data["distress_ads"], "risk_score": risk})
            if track_veh:
                data = scrape_mudah(slug, "Vehicles")
                risk = "High" if data["distress_ads"] > 5 else "Medium" if data["distress_ads"] > 2 else "Low"
                new_rows.append({"date": today, "location": loc, "category": "Vehicles", "total": data["total"], "distress_ads": data["distress_ads"], "risk_score": risk})
        
        if new_rows:
            st.session_state.history_df = pd.concat([st.session_state.history_df, pd.DataFrame(new_rows)], ignore_index=True)
            st.session_state.history_df.to_csv(CSV_FILE, index=False)
            st.success("Scan completed!")

# ================== TABS ==================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Today", "📈 Listings Trends", "📊 Listings History", "⛽ Fuel History"])

with tab1:
    st.header("Today's Scan Results")
    if not st.session_state.history_df.empty:
        today_str = datetime.now().strftime("%d-%b-%Y")
        today_df = st.session_state.history_df[st.session_state.history_df["date"] == today_str]
        for loc in selected_locations:
            st.subheader(loc)
            df_loc = today_df[today_df["location"] == loc]
            if not df_loc.empty:
                st.dataframe(df_loc, hide_index=True)

with tab2:
    st.header("Listings Trends (Separate by Type)")
    if not st.session_state.history_df.empty:
        # Properties Graph
        prop_df = st.session_state.history_df[st.session_state.history_df["category"] == "Properties"]
        if not prop_df.empty:
            st.subheader("Properties Trend")
            fig_p = px.line(prop_df, x="date", y="total", color="location", title="Properties - Total Listings")
            st.plotly_chart(fig_p, use_container_width=True)
        
        # Vehicles Graph
        veh_df = st.session_state.history_df[st.session_state.history_df["category"] == "Vehicles"]
        if not veh_df.empty:
            st.subheader("Vehicles Trend")
            fig_v = px.line(veh_df, x="date", y="total", color="location", title="Vehicles - Total Listings")
            st.plotly_chart(fig_v, use_container_width=True)

with tab3:
    st.header("Listings History Table")
    if not st.session_state.history_df.empty:
        st.dataframe(st.session_state.history_df.sort_values("date", ascending=False), hide_index=True)
    else:
        st.info("No scans yet.")

with tab4:
    st.header("Fuel Price History")
    if not st.session_state.fuel_history_df.empty:
        st.dataframe(st.session_state.fuel_history_df.sort_values("date", ascending=False), hide_index=True)
    else:
        st.info("No fuel price changes saved yet.")

st.caption("Phase 10 • Separate graphs for Properties & Vehicles • Current vs Previous comparison ready")
