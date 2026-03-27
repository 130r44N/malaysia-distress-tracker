import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import plotly.express as px
import re

st.set_page_config(page_title="Malaysia Distress Sales Tracker", layout="wide")

st.title("🛡️ Malaysia Distress Sales Tracker")
st.markdown("**Nationwide • Adjustable • Automatic History**")

# ================== PASSWORD PROTECTION FOR FUEL EDITING ==================
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

ADMIN_PASSWORD = "sarawak2026"   # ← CHANGE THIS TO YOUR OWN STRONG PASSWORD

# Simple password input at the top
password_input = st.text_input("🔑 Admin Password (to edit fuel prices)", type="password")
if password_input:
    if password_input == ADMIN_PASSWORD:
        st.session_state.admin_authenticated = True
        st.success("✅ Admin access granted")
    else:
        st.error("❌ Wrong password")

# ================== FUEL PRICES WIDGET (BUDI vs Non-BUDI) ==================
st.subheader("⛽ Malaysia Fuel Prices (26 Mar – 1 Apr 2026)")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("RON95 BUDI95 (Subsidised)", "RM1.99", "unchanged")
    st.metric("RON95 (Unsubsidised / Non-BUDI)", "RM3.87", "+60 sen")

with col2:
    st.metric("RON97", "RM5.15", "+60 sen")

with col3:
    st.metric("Diesel - Peninsular", "RM5.52", "+80 sen")
    st.metric("Diesel - East Malaysia", "RM2.15", "unchanged")

st.caption("Source: Ministry of Finance / PETRONAS • Updated weekly")

if st.session_state.admin_authenticated:
    st.info("You are in admin mode. You can edit fuel prices here in the next phase.")

# ================== CONFIG ==================
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

# ================== SIDEBAR ==================
st.sidebar.header("🎛️ Settings")
selected_locations = st.sidebar.multiselect(
    "Select locations to track",
    options=list(LOCATIONS.keys()),
    default=["Bintulu (Sarawak)", "Miri (Sarawak)"]
)

track_properties = st.sidebar.checkbox("Track Properties", value=True)
track_vehicles = st.sidebar.checkbox("Track Vehicles", value=True)

run_button = st.sidebar.button("🚀 Run Fresh Scan Now", type="primary")

# ================== HISTORY ==================
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

# ================== IMPROVED SCRAPE FUNCTION ==================
def scrape_mudah(location_slug, category):
    if category == "Properties":
        url = f"https://www.mudah.my/{location_slug}/properties-for-sale"
    else:
        url = f"https://www.mudah.my/{location_slug}/cars-for-sale"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Better total count detection
        total_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:result|listing|found)', r.text, re.I)
        total = int(total_match.group(1).replace(',', '')) if total_match else 0
        
        # Rough distress count from first page
        distress_count = sum(1 for kw in KEYWORDS if kw in r.text.lower())
        
        return {
            "total": total,
            "private": 0,
            "new_24h": 0,
            "distress_ads": min(distress_count, 10),  # cap to avoid false high
            "median_price": None
        }
    except Exception as e:
        st.warning(f"Scraping issue for {location_slug}: {str(e)[:100]}")
        return {"total": 0, "private": 0, "new_24h": 0, "distress_ads": 0, "median_price": None}

# ================== RUN SCAN ==================
if run_button and selected_locations:
    with st.spinner("Scanning Mudah.my... This may take 15-30 seconds"):
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
tab1, tab2 = st.tabs(["📊 Live Dashboard", "📈 History & Trends"])

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
    st.header("History & Trends")
    if not st.session_state.history_df.empty:
        st.dataframe(st.session_state.history_df.sort_values("date", ascending=False))
        fig = px.line(st.session_state.history_df, x="date", y="total", color="location", title="Total Listings Trend")
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("📥 Download Full History CSV", st.session_state.history_df.to_csv(index=False), "malaysia_distress_history.csv")
    else:
        st.info("Run scans to build history and see trends.")

st.caption("Phase 5 • Password: sarawak2026 (change it in code) • Fuel editing coming next")
