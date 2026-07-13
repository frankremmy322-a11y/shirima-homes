import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from datetime import timedelta, datetime
import base64
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
from prophet import Prophet
import logging

# Mipangilio ya Prophet kuzuia meseji zisizo na lazima
logging.getLogger('prophet').setLevel(logging.WARNING)

# =====================================================================
# 1. PAKIA DATA MOJA KWA MOJA KUTOKA GOOGLE SHEETS (GLOBAL LOADING)
# =====================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    mauzo_global = conn.read(worksheet="mauzo")
    stoo_global = conn.read(worksheet="stoo")
    orders_global = conn.read(worksheet="orders")
except Exception as e:
    st.error(f"Hitilafu ya Mtandao kwenye Sheets: {e}")
    mauzo_global = pd.DataFrame()
    stoo_global = pd.DataFrame()
    orders_global = pd.DataFrame()

# Kopi za data kutumika kwenye app nzima bila kusoma faili upya
df = mauzo_global.copy()
df_stoo = stoo_global.copy()
df_orders = orders_global.copy()

# =====================================================================
# 2. FUNCTIONS / MKATABA WA KAZI ZA DASHBOARD
# =====================================================================

def piga_utabiri_wa_faida(df_data, siku_za_mbele):
    try:
        df_p = df_data[['Date', 'Profit']].copy()
        df_p.columns = ['ds', 'y']
        df_p['ds'] = pd.to_datetime(df_p['ds'])
        m = Prophet(daily_seasonality=True).fit(df_p)
        future = m.make_future_dataframe(periods=siku_za_mbele)
        forecast = m.predict(future)
        return forecast
    except Exception as e:
        return None

def piga_utabiri_wa_mauzo(df_data, siku_za_mbele):
    try:
        df_prophet = df_data[['Date', 'Total']].copy()
        df_prophet.columns = ['ds', 'y']
        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])
        m = Prophet(changepoint_prior_scale=0.05, daily_seasonality=False)
        m.fit(df_prophet)
        future = m.make_future_dataframe(periods=siku_za_mbele)
        forecast = m.predict(future)
        return forecast
    except Exception as e:
        st.error(f"Error kwenye Prophet: {e}")
        return None

def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except:
        return ""

def password_entered():
    if st.session_state["password"] == "shirima2026":
        st.session_state["password_correct"] = True
        del st.session_state["password"]
    else:
        st.session_state["password_correct"] = False

def save_inventory():
    # Inasaga inventory ya sasa na kuisukuma Google Sheets
    data = []
    for bidhaa, kiasi in st.session_state.inventory_awal.items():
        bei = st.session_state.get('prices', {}).get(bidhaa, 0)
        data.append({"Category": bidhaa, "Total_Stock": kiasi, "Buying_Price": bei})
    new_df = pd.DataFrame(data)
    conn.update(worksheet="stoo", data=new_df)

def load_inventory():
    return stoo_global.copy() if not stoo_global.empty else pd.DataFrame(columns=['Category', 'Total_Stock', 'Buying_Price'])
   
def style_status(val):
    if val == 'Pending':
        return 'color:#ff4b4b;font-weight:bold;'
    elif val == 'Completed':
        return 'color:#00ff00;font-weight:bold;'
    elif val == 'Canceled':
        return 'color:#00f2ff;font-weight:bold;'
    return

def calculate_inventory_value():
    try:
        # Tunatumia data zilizopakiwa juu badala ya pd.read_csv
        df_s = stoo_global.copy()
        df_m = mauzo_global.copy()
         
        df_s['Category'] = df_s['Category'].str.strip().str.lower()
        df_m['Category'] = df_m['Category'].str.strip().str.lower()
        
        mauzo_sum = df_m.groupby('Category')['Qty'].sum().reset_index()
        mauzo_sum.columns = ['Category', 'Zilizouzwa']

        df_final = pd.merge(df_s, mauzo_sum, on='Category', how='left').fillna(0)
        df_final['Zilizobaki'] = df_final['Total_Stock'] - df_final['Zilizouzwa']
        df_final['Actual_Value'] = df_final['Zilizobaki'] * df_final['Buying_Price']
      
        return df_final['Actual_Value'].sum(), df_final['Zilizobaki'].sum()
    except Exception as e:
        print(f"Error kwenye Thamani: {e}")
    return 0, 0

pesa_stoo, vitu_stoo = calculate_inventory_value()
  
def check_password():
    if "welcomed" not in st.session_state:
        st.session_state["welcomed"] = False
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    .stApp { background-color: #0e1117; }
    div[data-baseweb="input"]{
        border:2px solid #00f2ff !important;
        border-radius:10px;
        box-shadow:none !important;
    }
    .jarvis-title{
        color:#00f2ff;
        font-family:'Courier New',Courier,monospace;
        text-shadow:0 0 5px #00f2ff,0 0 10px #00f2ff;
        font-size:40px;
        font-weight:bold;
        letter-spacing: 5px;
        text-transform: uppercase;
    }
    .kali-container{
        display:block;
        margin-left:auto;
        margin-right:auto;
        width:300px !important;
        opacity:0.9;
        filter:invert(1) brightness(1.2) drop-shadow(0 0 15px #00f2ff);
        text-align:center;
    }
    </style>
    """, unsafe_allow_html=True)

    if "password_correct" not in st.session_state:
        st.info("System Locked: Waiting for Authorization From Frank Shirima")
        st.text_input("ENTER ACCESS CODE", type="password", on_change=password_entered, key="password")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="kali-container"><img src="data:image/png;base64,{}"></div>'.format(image_to_base64("kali.png")), unsafe_allow_html=True)
            st.markdown('<p class="jarvis-title" style="font-size:20px; text-align:center;">CYBERGATES LABS</p>', unsafe_allow_html=True)
        return False

    elif not st.session_state['password_correct']:
        st.markdown('<p style="color:#ff0000; font-family:\'Orbitron\',sans-serif; text-align:center; text-shadow:0 0 15px #ff0000; font-size:18px; font-weight:bold; letter-spacing:5px;">ACCESS DENIED</p>', unsafe_allow_html=True)
        st.text_input("ENTER ACCESS CODE", type="password", on_change=password_entered, key="password")
        st.error("Authentication Failed: Security Breach Protocol Initialized")
        return False
    else:
        if st.session_state["password_correct"] and not st.session_state["welcomed"]:
            st.balloons()
            st.toast("Access Granted. Welcome Back, Mr Shirima.")
            st.session_state["welcomed"] = True
        return True

# =====================================================================
# 3. UKURASA MKUU WA DASHBOARD (MIFUMO YOTE INAPORUN)
# =====================================================================
if check_password():
    st.set_page_config(page_title="KWA SHIRIMA AI", layout="wide")
    st.title("📊 Prophet Dashboard - KWA SHIRIMA Store")

    # Mfumo wa Session State wa stoo ya ndani ya app
    if 'inventory_awal' not in st.session_state:
        st.session_state.inventory_awal = {
            'Mapazia': 1000, 'Saa za Ukutani': 950, 'Mazulia': 900, 'Taa za Kupamba': 850, 'Vases': 920
        }

    df_stock = pd.DataFrame(list(st.session_state.inventory_awal.items()), columns=['Category', 'Total_Stock'])
    mauzo_kwa_bidhaa = df.groupby('Category')['Qty'].sum().reset_index()
    df_hali_ya_stoo = pd.merge(df_stock, mauzo_kwa_bidhaa, on='Category', how='left').fillna(0)
    df_hali_ya_stoo['iliyobaki'] = df_hali_ya_stoo['Total_Stock'] - df_hali_ya_stoo['Qty']
      
    df['Date'] = pd.to_datetime(df['Date'])
    daily_sales = df.groupby('Date')['Total'].sum().reset_index()
    
    # Logic ya tarehe
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    leo_halisi = datetime.now().date()

    pamoja = st.selectbox("Linganisha Mauzo ya:", ["Siku (Leo vs Jana)", "Wiki (Hii vs Iliyopita)", "Mwezi (Huu vs Uliopita)"])

    if pamoja == "Siku (Leo vs Jana)":
        k1_start, k1_end = leo_halisi, leo_halisi
        k2_start, k2_end = leo_halisi - timedelta(days=1), leo_halisi - timedelta(days=1)
        label1, label2 = "Leo", "Jana"
    elif pamoja == "Wiki (Hii vs Iliyopita)":
        k1_start, k1_end = leo_halisi - timedelta(days=6), leo_halisi
        k2_start, k2_end = k1_start - timedelta(days=7), k1_start - timedelta(days=1)
        label1, label2 = "Wiki Hii", "Wiki Iliyopita"
    else:
        k1_start = leo_halisi.replace(day=1)
        k1_end = leo_halisi
        punda = k1_start - timedelta(days=1) 
        k2_start = punda.replace(day=1)
        k2_end = punda
        label1, label2 = "Mwezi Huu", "Mwezi Uliopita"

    m1 = df[(df['Date'] >= k1_start) & (df['Date'] <= k1_end)]['Total'].sum()
    m2 = df[(df['Date'] >= k2_start) & (df['Date'] <= k2_end)]['Total'].sum()
    diff = m1 - m2

    with st.sidebar:
        st.header("⚙️ Mipangilio ya AI")
        siku_za_mbele = st.slider("Chagua Siku za Kutabiri Mauzo:", 7, 90, 30)

    st.sidebar.divider()
 
    # Kutengeneza dictionary ya bei kutoka kwenye data ya Google Sheets
    bei_kununua_dict = dict(zip(df_stoo['Category'], df_stoo['Buying_Price']))

    st.sidebar.header("📝 Ingiza Mauzo")
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = list(bei_kununua_dict.keys())[0] if bei_kununua_dict else ""
 
    new_category = st.sidebar.selectbox("Aina ya Bidhaa", options=list(bei_kununua_dict.keys()), key="cat_selector")

    with st.sidebar.form("sales_form", clear_on_submit=True):
        current_price = bei_kununua_dict.get(new_category, 0)
        st.markdown(f"💰 **Bei ya Stoo kwa {new_category}:**")
        st.code(f"TSh {current_price:,.0f}") 
    
        new_date = st.date_input("Tarehe", datetime.now())
        new_qty = st.number_input("Idadi (Qty)", min_value=1, step=1)
        new_total = st.number_input("Jumla ya Pesa uliyopokea (TZS)", min_value=0, step=5000)
        submitted = st.form_submit_button("Hifadhi Mauzo")
    
    if submitted:
        profit_made = new_total - (current_price * new_qty)
        unit_price = int(new_total / new_qty) if new_qty > 0 else 0
        
        new_row = pd.DataFrame([[
            new_date.strftime("%Y-%m-%d"), new_category, new_qty, unit_price, new_total, profit_made
        ]], columns=['Date', 'Category', 'Qty', 'Price', 'Total', 'Profit'])
        
        # Sukuma mauzo mapya kwenda Google Sheets
        df_mauzo_updated = pd.concat([mauzo_global, new_row], ignore_index=True)
        conn.update(worksheet="mauzo", data=df_mauzo_updated)
        st.success(f"Imesave Google Sheets! Faida: {profit_made:,.0f}")
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("💼 Duka Portfolio")
    st.sidebar.write("Thamani ya stoo (Total)")
    st.sidebar.subheader(f"{pesa_stoo:,.0f} TZS")
    st.sidebar.write("Idadi ya bidhaa (Total)")
    st.sidebar.subheader(f"{vitu_stoo:,.0f} Pcs")

    mwezi_huu_data = df[df['Date'] >= (leo_halisi - timedelta(days=30))]
    wastani_kwa_siku = mwezi_huu_data.groupby('Date')['Total'].sum().mean() if not mwezi_huu_data.empty else 0

    st.sidebar.divider()
    st.sidebar.metric(label="Wastani wa Mauzo/Siku", value=f"{wastani_kwa_siku:,.0f} TZS")

    st.sidebar.divider()
    st.sidebar.subheader("🎯 Target Control")
    lengo_la_mwezi = st.sidebar.number_input("Weka Lengo la Mwezi (TZS)", value=900000, step=100000)
    asilimia_ya_lengo = (m1 / lengo_la_mwezi) * 100 if lengo_la_mwezi > 0 else 0
    bar_color = "#ff0000" if asilimia_ya_lengo < 50 else "#ffaa00" if asilimia_ya_lengo < 80 else "#00ff00"
    
    st.sidebar.markdown(f"""
        <div style="width: 100%; background-color: #262730; border-radius: 20px; border: 1px solid #444;">
            <div style="width: {min(asilimia_ya_lengo, 100.0)}%; background: linear-gradient(90deg, {bar_color}, #ffffff); height: 20px; border-radius: 20px; box-shadow: 0 0 15px {bar_color};"></div>
        </div>
        <p style="text-align: center; font-family: 'Orbitron', sans-serif; color: {bar_color}; font-size: 18px; margin-top: 5px;">
            {asilimia_ya_lengo:.1f}% LOADED
        </p>
    """, unsafe_allow_html=True)

    bado_kiasi = lengo_la_mwezi - m1
    if bado_kiasi > 0:
        st.sidebar.warning(f"⚠️ Bado **{bado_kiasi:,.0f} TZS** kufikia lengo!")
    else:
        st.sidebar.success(f"🔥 SYSTEM OPTIMIZED: Umevuka lengo kwa **{abs(bado_kiasi):,.0f} TZS**!")
    
    # --- Low Stock Alerts ---
    st.sidebar.divider()
    st.sidebar.subheader("🚀 Low Stock Alerts")

    df_stoo_clean = df_stoo.copy()
    df_mauzo_clean = df.copy()
    df_stoo_clean['Category'] = df_stoo_clean['Category'].astype(str).str.strip()
    df_mauzo_clean['Category'] = df_mauzo_clean['Category'].astype(str).str.strip()

    mauzo_sum_alert = df_mauzo_clean.groupby('Category')['Qty'].sum().reset_index()
    current_hali = pd.merge(df_stoo_clean, mauzo_sum_alert, on='Category', how='left').fillna(0)
    current_hali['iliyobaki'] = current_hali['Total_Stock'] - current_hali['Qty']

    LOW_STOCK_LIMIT = 10
    low_stock_items = current_hali[current_hali['iliyobaki'] <= LOW_STOCK_LIMIT]

    if not low_stock_items.empty:
        for _, row in low_stock_items.iterrows():
            baki = int(row['iliyobaki'])
            bidhaa = row['Category']
            if baki <= 0:
                st.sidebar.error(f"⚠️ **{bidhaa}** IMEKWISHA!: {baki}")
            else:
                st.sidebar.error(f"⚠️ **{bidhaa}** imebaki: {baki}")
    else:
        st.sidebar.success("✅ Bidhaa zote zipo za kutosha!") 

    # --- Ongeza Mzigo Mpya ---
    st.sidebar.divider()
    st.sidebar.subheader("📦 Ongeza Mzigo Mpya")
    list_ya_bidhaa = df_stoo['Category'].unique().tolist()

    with st.sidebar.form("stock_form"):
        bidhaa_mpya = st.selectbox("Chagua Bidhaa", list_ya_bidhaa)
        kiasi_kipya = st.number_input("Idadi", min_value=1)
        submit_stock = st.form_submit_button("Hifadhi mzigo")
    
    if submit_stock:
        mask = df_stoo['Category'] == bidhaa_mpya
        if mask.any():
            idadi_ya_sasa = int(pd.to_numeric(df_stoo.loc[mask, 'Total_Stock']).iloc[0])
            idadi_mpya = idadi_ya_sasa + int(kiasi_kipya)
            df_stoo.loc[mask, 'Total_Stock'] = idadi_mpya
            
            # Update kule Google Sheets
            conn.update(worksheet="stoo", data=df_stoo)
            
            if 'inventory_awal' in st.session_state:
                st.session_state.inventory_awal[bidhaa_mpya] = idadi_mpya
            st.success(f"✅ Imefanikiwa Google Sheets! {bidhaa_mpya} sasa zipo {idadi_mpya}")
            st.rerun()

    # --- Ongeza Bidhaa Mpya Kabisa ---
    st.sidebar.divider()
    st.sidebar.subheader("🆕 Ongeza Bidhaa Mpya Kabisa")

    with st.sidebar.form("new_item_form", clear_on_submit=True):
        jina_la_bidhaa = st.text_input("Andika jina la bidhaa")
        idadi_ya_mwanzo = st.number_input("Idadi ya mwanzo", min_value=1)
        bei_ya_kununulia = st.number_input("Bei ya kununulia (moja)", min_value=1)
        submit_new = st.form_submit_button("Sajili Sasa")

    if submit_new and jina_la_bidhaa:
        new_row_item = {'Category': jina_la_bidhaa, 'Total_Stock': int(idadi_ya_mwanzo), 'Buying_Price': float(bei_ya_kununulia)}
        df_stoo_updated = pd.concat([df_stoo, pd.DataFrame([new_row_item])], ignore_index=True)
        
        # Sukuma kwenye Sheets
        conn.update(worksheet="stoo", data=df_stoo_updated)
        
        if 'inventory_awal' in st.session_state:
            st.session_state.inventory_awal[jina_la_bidhaa] = int(idadi_ya_mwanzo)
        st.toast(f"✅ {jina_la_bidhaa} imesajiliwa Sheets!")
        st.rerun()

    # --- Main Dashboard Visuals ---
    st.subheader(f"Uchambuzi wa Mauzo: {pamoja}")
    col_a, col_b = st.columns(2)
    col_a.metric(label=label1, value=f"{m1:,.0f} TZS", delta=f"{diff:,.0f} TZS")
    col_b.metric(label=label2, value=f"{m2:,.0f} TZS")

    m1_profit = df[(df['Date'] >= k1_start) & (df['Date'] <= k1_end)]['Profit'].sum()
    m2_profit = df[(df['Date'] >= k2_start) & (df['Date'] <= k2_end)]['Profit'].sum()
    growth_pct = ((m1_profit - m2_profit) / m2_profit) * 100 if m2_profit > 0 else 0

    st.write("___")
    st.subheader(f"Uchambuzi wa Faida: {pamoja}")
    p_col1, p_col2 = st.columns(2)
    p_col1.metric(label=f"Faida ({label1})", value=f"{m1_profit:,.0f} TZS", delta=f"{growth_pct:,.1f}% vs {label2}")
    p_col2.metric(label=f"Faida ({label2})", value=f"{m2_profit:,.0f} TZS")
       
    st.write("___")
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("Mwenendo wa Mauzo ya Nyuma")
        df_graph = df.copy()
        daily_sales_graph = df_graph.groupby('Date')['Total'].sum().reset_index().sort_values('Date')
        st.line_chart(data=daily_sales_graph, x='Date', y='Total', use_container_width=True)

    with col_g2:
        st.markdown(f"#### 🔮 Utabiri wa Mauzo")
        forecast = piga_utabiri_wa_mauzo(df, siku_za_mbele)
        if forecast is not None:
            future_only = forecast.tail(siku_za_mbele)
            st.line_chart(future_only.set_index('ds')['yhat'])
            mauzo_yatarajiwa = forecast['yhat'].iloc[-1]
            st.metric(label=f"Mauzo ya Siku ya {siku_za_mbele}", value=f"{mauzo_yatarajiwa:,.0f} TZS")
         
    st.divider()
    st.write("### 📜 Historia ya Mauzo: Kwa Shirima Store")

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        t_anza = st.date_input("Kuanzia tarehe:", df['Date'].min() if not df.empty else leo_halisi, key="start_hist")
    with col_h2:
        t_isha = st.date_input("Mpaka tarehe:", df['Date'].max() if not df.empty else leo_halisi, key="end_hist")

    mask_hist = (df['Date'] >= t_anza) & (df['Date'] <= t_isha)
    df_filtered_hist = df.loc[mask_hist].copy()

    if not df_filtered_hist.empty:
        df_filtered_hist['Total (Tsh)'] = df_filtered_hist['Total'].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_filtered_hist[['Date', 'Category', 'Qty', 'Price', 'Total']], use_container_width=True, hide_index=True)
        st.success(f"💰 Jumla ya Mapato Kipindi Hiki: **Tsh {df_filtered_hist['Total'].sum():,.0f}**")
    else:
        st.warning("Hakuna mauzo yaliyopatikana katika kipindi ulichochagua.")
    
    # Top Products Analysis
    st.divider()
    st.subheader("🔍 Wateja wanapenda nini zaidi? (Product Analysis)")
    top_5_data = df.groupby('Category')['Qty'].sum().sort_values(ascending=False).head(5)
    names = list(top_5_data.index)
    vals = list(top_5_data.values)

    c1, c2, c3, c4, c5 = st.columns(5)
    if len(names) > 0: c1.metric(names[0], f"{int(vals[0])} Pcs")
    if len(names) > 1: c2.metric(names[1], f"{int(vals[1])} Pcs")
    if len(names) > 2: c3.metric(names[2], f"{int(vals[2])} Pcs")
    if len(names) > 3: c4.metric(names[3], f"{int(vals[3])} Pcs")
    if len(names) > 4: c5.metric(names[4], f"{int(vals[4])} Pcs")

    if not top_5_data.empty:
        labels = top_5_data.index
        sizes = top_5_data.values
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']
        col_pie1, col_pie2, col_pie3 = st.columns([1, 2, 1])
    
        with col_pie2:
            fig, ax1 = plt.subplots(figsize=(5, 5))
            wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, pctdistance=0.75, textprops={'color': "black", 'fontsize': 10, 'fontweight': 'bold'})
            centre_circle = plt.Circle((0,0), 0.70, fc='black')
            fig.gca().add_artist(centre_circle)

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_weight('bold')
            
            ax1.text(0, 0, f"{int(sizes.sum())}\nPcs", ha='center', va='center', fontsize=14, color='white', fontweight='bold')
            ax1.axis('equal')
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)

    st.divider()
    st.subheader("📊 Mauzo ya Bidhaa Zote")
    st.bar_chart(df.groupby('Category')['Qty'].sum().sort_values(ascending=False))
  
    # --- Mchanganuo wa Stoo Table ---
    st.markdown("### 📋 Mchanganuo wa Stoo (Inventory)")
    try:
        mauzo_sum_table = df.groupby('Category')['Qty'].sum().reset_index()
        mauzo_sum_table.columns = ['Category', 'Zilizouzwa']
    except:
        mauzo_sum_table = pd.DataFrame(columns=['Category', 'Zilizouzwa'])

    df_final_table = pd.merge(df_stoo, mauzo_sum_table, on='Category', how='left').fillna(0)
    df_final_table['Zilizobaki'] = (df_final_table['Total_Stock'] - df_final_table['Zilizouzwa']).astype(int)
    df_final_table['Total_Stock'] = df_final_table['Total_Stock'].astype(int)
    df_final_table['Zilizouzwa'] = df_final_table['Zilizouzwa'].astype(int)

    df_display = df_final_table[['Category', 'Total_Stock', 'Zilizouzwa', 'Zilizobaki']]
    df_display.columns = ['Aina ya Bidhaa', 'Mzigo Ulioingia', 'Zilizouzwa', 'Zilizobaki']

    def highlight_low_stock(row):
        return ['background-color: #ff4b4b; color: white' if row['Zilizobaki'] < 10 else ''] * len(row)

    st.dataframe(df_display.style.apply(highlight_low_stock, axis=1), use_container_width=True)

    # --- Orders System ---
    st.divider()
    st.subheader("Orders Table")
    bidhaa_zilizopo = list(df_stoo['Category'].unique())
   
    with st.expander("Bonyeza hapa kusajili Oda Mpya"):
        with st.form("new_order_form", clear_on_submit=True):
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                mteja_mpya = st.text_input("Jina la Mteja")
                simu_mpya = st.text_input("Namba Mpya")
                chaguo = st.selectbox("Chagua Bidhaa", bidhaa_zilizopo)
                bidhaa_mpya_text = st.text_input("Kama Bidhaa ni Mpya, andika hapa:")
                location_mpya = st.text_input("Mteja anatokea wapi:")
            with col_o2:
                qty_mpya = st.number_input("Idadi (Qty)", min_value=1, step=1)
                advanced_mpya = st.number_input("Advanced (TZS)", min_value=0, step=5000)
                hali_mpya = st.selectbox("Hali ya Oda", ["Pending", "Completed", "Canceled"])
                bidhaa_final = bidhaa_mpya_text.strip() if bidhaa_mpya_text.strip() != "" else chaguo

            if st.form_submit_button("Hifadhi Oda"):
                if mteja_mpya and simu_mpya and bidhaa_final:
                    mpya = {
                        'Tarehe': datetime.now().strftime("%Y-%m-%d"), 'Mteja': mteja_mpya, 'Simu': str(simu_mpya),
                        'Bidhaa': bidhaa_final, 'Qty': qty_mpya, 'Advanced': advanced_mpya, 'Status': hali_mpya, 'Location': location_mpya
                    }
                    df_orders_updated = pd.concat([df_orders, pd.DataFrame([mpya])], ignore_index=True)
                    
                    # Update Sheets
                    conn.update(worksheet="orders", data=df_orders_updated)
                    st.success(f"Oda ya {mteja_mpya} imepokelewa Google Sheets!")
                    st.rerun()
                else:
                    st.error("Tafadhali jaza Jina, Simu, na Bidhaa!")

    # Chapa Orders zilizochujwa
    if not df_orders.empty:
        df_orders['Tarehe'] = pd.to_datetime(df_orders['Tarehe'], errors='coerce').dt.date
        st.write("Chuja Oda Kwa Tarehe")
        col_ord1, col_ord2 = st.columns(2)
        with col_ord1:
            start_date = st.date_input("Kuanzia:", df_orders['Tarehe'].min() if not df_orders['Tarehe'].isnull().all() else leo_halisi)
        with col_ord2:
            end_date = st.date_input("Mpaka:", df_orders['Tarehe'].max() if not df_orders['Tarehe'].isnull().all() else leo_halisi)
        
        status_options = df_orders['Status'].unique().tolist()
        status_filter = st.multiselect("Chagua Hali:", options=status_options, default=status_options)
        
        mask_ord = (df_orders['Tarehe'] >= start_date) & (df_orders['Tarehe'] <= end_date) & (df_orders['Status'].isin(status_filter))
        df_filtered_ord = df_orders[mask_ord]
   
        if not df_filtered_ord.empty:
            st.metric(label=f"Jumla ya Advance", value=f"{df_filtered_ord['Advanced'].sum():,.0f} TZS")
            st.dataframe(df_filtered_ord.style.applymap(style_status, subset=['Status']), use_container_width=True)
        else:
            st.info("Hakuna Oda ya Kipindi hiki")

        # Update and Delete Orders Section
        target_customer = st.selectbox("Chagua mteja wa kumfanyia marekebisho:", df_orders['Mteja'].unique())
        col_u1, col_u2, col_u3 = st.columns(3)

        with col_u1:
            new_status = st.selectbox("Badilisha Hali (Status):", ["Pending", "Completed", "Canceled"])
            ongeza_hela = st.number_input("Ongeza Pesa Ya Advance (TZS):", min_value=0, step=5000)

            if st.button("Update Status"):
                idx = df_orders[df_orders['Mteja'] == target_customer].index
                if not idx.empty:
                    df_orders.at[idx[0], 'Advanced'] = df_orders.at[idx[0], 'Advanced'] + ongeza_hela
                    df_orders.at[idx[0], 'Status'] = new_status
                    
                    # Push direct Google Sheets
                    conn.update(worksheet="orders", data=df_orders)
                    st.success(f"Oda ya {target_customer} sasa ni {new_status}")
                    st.rerun()

        with col_u2:
            if st.button("Futa Oda Hii"):
                df_orders = df_orders[df_orders['Mteja'] != target_customer]
                conn.update(worksheet="orders", data=df_orders)
                st.warning(f"Oda ya {target_customer} imefutwa Sheets!")
                st.rerun()

        with col_u3:
            st.write("**Maelekezo ya Order:**")
            info = df_orders[df_orders['Mteja'] == target_customer].iloc[0]
            st.write(f"Tarehe: {info['Tarehe']}")
            st.write(f"Bidhaa: {info['Bidhaa']}")
            st.write(f"Idadi: {info['Qty']} Pcs")
            st.write(f"Simu: {info['Simu']}")
            st.write(f"Advanced: {info['Advanced']} TZS")
            st.write(f"Location: {info['Location']}")
            
            if info['Status'] == "Pending": st.error(f"Hali: {info['Status']}")
            elif info['Status'] == "Completed": st.success(f"Hali: {info['Status']}")
            else: st.info(f"Hali: {info['Status']}")
    else:
        st.info("Hakuna oda za kufanyiwa marekebisho kwa sasa")

    # Prophet Profit Analysis
    st.divider()
    st.subheader("🔮 Frank AI: Profit Analysis")
    siku_adjust = st.slider("Adjust Siku:", 7, 90, 30, key="fs_slider")

    with st.spinner("Frank AI is analysing profit..."):
        matokeo = piga_utabiri_wa_faida(df, siku_adjust)
        if matokeo is not None:
            col_prof1, col_prof2 = st.columns([2, 1])
            with col_prof1:
                st.line_chart(matokeo.set_index('ds')['yhat'])
            with col_prof2:
                faida_ijayo = matokeo['yhat'].iloc[-1]
                st.metric(label=f"Faida ya Siku {siku_adjust}", value=f"{faida_ijayo:,.0f} TZS")
        else:
            st.error("AI imeshindwa kusoma data ya faida.")
    
    st.write(f"**Jumla ya Faida Mpaka Sasa:** TSh {df['Profit'].sum():,.0f}") 
       
    # --- Ripoti Area ---
    st.divider()
    st.write("### 📊 Ripoti na Uchambuzi wa Biashara (Mauzo & Stoo)")

    if not df.empty:
        aina_ya_ripoti = st.selectbox("Chagua Kipindi cha Ripoti:", ["Ripoti ya Siku (Leo)", "Ripoti ya Wiki Hii", "Ripoti ya Mwezi Huu", "Ripoti ya Mwaka Huu"], key="ripoti_kipindi_real_box")
        df_rep = df.copy()
        df_rep['Date'] = pd.to_datetime(df_rep['Date']).dt.date
    
        if aina_ya_ripoti == "Ripoti ya Siku (Leo)":
            df_rep = df_rep[df_rep['Date'] == leo_halisi]
            f_name = f"ripoti_ya_siku_{leo_halisi}.pdf"
        elif aina_ya_ripoti == "Ripoti ya Wiki Hii":
            mwanzo_wa_wiki = leo_halisi - pd.Timedelta(days=6)
            df_rep = df_rep[(df_rep['Date'] >= mwanzo_wa_wiki) & (df_rep['Date'] <= leo_halisi)]
            f_name = f"ripoti_ya_wiki_{leo_halisi}.pdf"
        elif aina_ya_ripoti == "Ripoti ya Mwezi Huu":
            df_rep = df_rep[pd.to_datetime(df_rep['Date']).dt.month == leo_halisi.month]
            f_name = f"ripoti_ya_mwezi_{leo_halisi.month}_{leo_halisi.year}.pdf"
        else:
            df_rep = df_rep[pd.to_datetime(df_rep['Date']).dt.year == leo_halisi.year]
            f_name = f"ripoti_ya_mwaka_{leo_halisi.year}.pdf"

        if not df_rep.empty:
            jumla_mauzo = df_rep['Total'].sum()
            jumla_profit = df_rep['Profit'].sum()
            bidhaa_zilizouzwa = df_rep['Qty'].sum()
            
            top_bidhaa_df = df_rep.groupby('Category')['Qty'].sum().reset_index()
            top_bidhaa_df['Asilimia'] = (top_bidhaa_df['Qty'] / bidhaa_zilizouzwa) * 100
            top_bidhaa_safi = top_bidhaa_df.sort_values(by='Qty', ascending=False).iloc[0]
            
            top_jina = top_bidhaa_safi['Category']
            top_asilimia = top_bidhaa_safi['Asilimia']
            vitu_vya_stoo = df_stoo['Total_Stock'].sum()

            c_rep1, c_rep2, c_rep3 = st.columns(3)
            with c_rep1:
                st.metric(label="💰 Jumla ya Mauzo", value=f"{jumla_mauzo:,.0f} TZS")
                st.metric(label="📦 Jumla ya Vitu Vilivyouzwa", value=f"{bidhaa_zilizouzwa:,} Pcs")
            with c_rep2:
                st.metric(label="📈 Faida Halisi (Profit)", value=f"{jumla_profit:,.0f} TZS")
                st.metric(label="🏬 Vitu Vilivyobaki Stoo", value=f"{vitu_vya_stoo:,} Pcs")
            with c_rep3:
                st.metric(label="🥇 Bidhaa Inayoongoza", value=f"{top_jina}")
                st.metric(label="📊 Asilimia ya Soko", value=f"{top_asilimia:.1f}%")

            # PDF Generator
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(26, 54, 93)
            pdf.cell(200, 10, txt="KWA SHIRIMA STORE - DODOMA", ln=True, align="C")
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(200, 8, txt=f"Ripoti: {aina_ya_ripoti}", ln=True, align="C")
            pdf.ln(10)
            
            # Print Table 1
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(26, 54, 93)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(90, 8, txt="Kipengele", border=1, ln=False, fill=True)
            pdf.cell(100, 8, txt="Kiasi", border=1, ln=True, fill=True)
            
            pdf.set_text_color(0, 0, 0)
            data_muhtasari = [
                ("Jumla ya Mauzo", f"{jumla_mauzo:,.0f} TZS"),
                ("Faida Halisi", f"{jumla_profit:,.0f} TZS"),
                ("Vitu Vilivyouzwa", f"{bidhaa_zilizouzwa:,} Pcs"),
                ("Inayoongoza", f"{top_jina} ({top_asilimia:.1f}%)")
            ]
            for k, v in data_muhtasari:
                pdf.cell(90, 8, txt=k, border=1, ln=False)
                pdf.cell(100, 8, txt=v, border=1, ln=True)

            pdf_output = pdf.output(dest='S')
            pdf_data = bytes(pdf_output) if not isinstance(pdf_output, str) else pdf_output
            
            st.download_button(
                label=f"📥 Pakua {aina_ya_ripoti} (PDF)",
                data=pdf_data,
                file_name=f_name,
                mime='application/pdf',
                key='download_fpdf_report_btn'
            )
        else:
            st.warning("Hakuna mauzo katika kipindi hiki cha ripoti.")