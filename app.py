import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import base64
from fpdf import FPDF
from datetime import datetime as dt, timedelta
from prophet import Prophet
from streamlit_gsheets import GSheetsConnection
import logging
import io
import plotly.graph_objects as go






# Hii inazuia Prophet isijaze terminal yako na meseji nyingi za kodi zisizo na lazima
logging.getLogger('prophet').setLevel(logging.WARNING)



@st.cache_data(ttl=600)  # Data itahifadhiwa kwa dakika 10
def load_data():

    
    # Hapa ndipo unapoweka code yako ya kusoma Google Sheets
    # mfano: return pd.read_csv(...)
    pass

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    mauzo_global = conn.read(worksheet="mauzo", ttl=0)
    stoo_global = conn.read(worksheet="stoo", ttl=0)
    orders_global = conn.read(worksheet="orders", ttl=0)
    orders_global['Tarehe'] = orders_global['Tarehe'].astype(str)
    orders_global['Tarehe'] = orders_global['Tarehe'].str.replace('00:00:00', '').str.replace(' 00:0', '')
except Exception as e:
    st.error(f"Hitilafu ya Mtandao: {e}")
    # Kutengeneza DataFrame tupu ili app isife kabisa chini
    import pandas as pd
    mauzo_global = pd.DataFrame()
    stoo_global = pd.DataFrame()
    orders_global = pd.DataFrame()

df = mauzo_global.copy()
df_stoo = stoo_global.copy()
df_orders = orders_global.copy()

def piga_utabiri_wa_faida(df, siku_za_mbele):
    try:
        # 1. Hakikisha df si tupu na ina columns zinazohitajika
        if df is None or df.empty or 'Date' not in df.columns or 'Profit' not in df.columns:
            st.info("ℹ️ Hakuna data ya faida inayopatikana kwa ajili ya utabiri.")
            return None

        # 2. Prophet inataka column ziitwe 'ds' na 'y'
        df_p = df[['Date', 'Profit']].copy()
        df_p.columns = ['ds', 'y']

        # 3. Hakikisha tarehe zipo kwenye format sahihi na faida ni namba
        df_p['ds'] = pd.to_datetime(df_p['ds'], errors='coerce')
        df_p['y'] = pd.to_numeric(df_p['y'], errors='coerce')

        # 4. Safiisha mistari yote yenye NaN (data iliyokosekana au yenye makosa)
        df_p_clean = df_p.dropna(subset=['ds', 'y'])

        # 5. Prophet inahitaji angalau mistari 2 halali kufanya kazi
        if len(df_p_clean) < 2:
            st.info("ℹ️ Data ya faida haitoshi kufanya utabiri kwa sasa. Inahitaji angalau rekodi 2.")
            return None

        # 6. Anzisha model na kuwasha msimu wa wiki na mwaka
        from prophet import Prophet
        m = Prophet(
            changepoint_prior_scale=0.05, 
            daily_seasonality=False,   # Hatuhitaji mabadiliko ya saa kwa saa
            weekly_seasonality=True,   # Inakamata tabia za siku za wiki (mf. wikendi)
            yearly_seasonality=True    # Inakamata mbadiliko ya miezi ya mwaka
        )
        
        # 7. ONGEZA SIKUKUU ZA TANZANIA (Holidays) 🇹🇿
        # Prophet itajua kiotomatiki siku kama Krismasi, Eid, Saba Saba, n.k.
        try:
            m.add_country_holidays(country_name='TZ')
        except Exception as holiday_error:
            # Kama kuna shida ya maktaba ya holidays, code itaendelea bila kufeli
            st.warning(f"⚠️ Imeshindwa kupakia sikukuu za TZ, utabiri utaendelea kawaida: {holiday_error}")
        
        # 8. Funza model kwa kutumia data iliyosafishwa
        m.fit(df_p_clean)

        # 9. Tengeneza tarehe za mbeleni na piga utabiri
        future = m.make_future_dataframe(periods=siku_za_mbele)
        forecast = m.predict(future)

        return forecast

    except Exception as e:
        # Ulinzi kama kuna hitilafu nyingine yoyote isiyotegemewa
        st.error(f"Error kwenye Prophet ya Faida: {e}")
        return None

def piga_utabiri_wa_mauzo(df, siku_za_mbele):
    try:
        # 1. Hakikisha df si tupu na ina columns zinazohitajika
        if df is None or df.empty or 'Date' not in df.columns or 'Total' not in df.columns:
            st.info("ℹ️ Hakuna data ya mauzo inayopatikana kwa ajili ya utabiri.")
            return None
            
        # Prophet inataka column ziitwe 'ds' na 'y'
        df_prophet = df[['Date', 'Total']].copy()
        df_prophet.columns = ['ds', 'y']

        # Hakikisha tarehe zipo kwenye format sahihi na thamani ni namba
        df_prophet['ds'] = pd.to_datetime(df_prophet['ds'], errors='coerce')
        df_prophet['y'] = pd.to_numeric(df_prophet['y'], errors='coerce')
        
        # Safisha mistari yote yenye NaN
        df_prophet_clean = df_prophet.dropna(subset=['ds', 'y'])

        # Prophet inahitaji angalau mistari 2 halali kufanya kazi
        if len(df_prophet_clean) < 2:
            st.info("ℹ️ Data ya mauzo haitoshi kufanya utabiri kwa sasa. Inahitajika angalau rekodi za siku 2 tofauti.")
            return None

        # Anzisha na ufunze model kwa kutumia data iliyosafishwa
        m = Prophet(changepoint_prior_scale=0.05, daily_seasonality=False)
        m.fit(df_prophet_clean)

        # Tengeneza tarehe za mbeleni
        future = m.make_future_dataframe(periods=siku_za_mbele)
        forecast = m.predict(future)

        return forecast
    except Exception as e:
        # Hapa bado inalinda kama kuna hitilafu nyingine yoyote isiyotegemewa
        st.error(f"Error kwenye Prophet: {e}")
        return None
    

def image_to_base64(image_path):
   with open(image_path, "rb")as image_file:
      return base64.b64encode(image_file.read()).decode()
      

def password_entered():
   if st.session_state.get("password")=="shirima2026":
    st.session_state["password_correct"]=True
    #del st.session_state["password"]
   else:
    st.session_state["password_correct"]=False

def save_inventory():
   data = []
   for bidhaa,kiasi in st.session_state.inventory_awal.items():
      bei = st.session_state.get('prices',{}).get(bidhaa,0)
      data.append({"Category":bidhaa,"Total_Stock":kiasi,"Buying_Price":bei})
      new_df = pd.DataFrame(data)
      conn.update(worksheet="stoo", data=new_df)

def load_inventory():
   return stoo_global.copy() if not stoo_global.empty else pd.DataFrame(columns=['Category', 'Total_Stock', 'Buying_Price'])
      
   
def style_status(val):
   if val=='Pending':
      return'color:#ff4b4b;font-weight:bold;'
   elif val=='Completed':
      return'color:#00ff00;font-weight:bold;'
   elif val=='Canceled':
      return'color:#00f2ff;font-weight:bold;'
   return
   


#
def calculate_inventory_value():
   
   try:
        #1. Soma data mpya yenye Buying_Price
        df_stoo = stoo_global.copy()
        df_mauzo = mauzo_global.copy()
         
        #soma data hakikisha majina ya bidhaa yanafanana
        df_stoo['Category']=df_stoo['Category'].str.strip().str.lower()
        df_mauzo['Category']=df_mauzo['Category'].str.strip().str.lower()
        
        #step1 temgeneza zilizounzwa kwa kupiga jumla ya mauzo
        mauzo_sum=df_mauzo.groupby('Category')['Qty'].sum().reset_index()
        mauzo_sum.columns=['Category','Zilizouzwa']

        #tengeneza zilizobaki kwey csv hatunsa tunaipata apa
        df_final=pd.merge(df_stoo,mauzo_sum,on='Category',how='left').fillna(0)
        df_final['Zilizobaki']=df_final['Total_Stock']-df_final['Zilizouzwa']
        
        #piga hesabu ya thamani halisi
        df_final['Actual_Value']=df_final['Zilizobaki']*df_final['Buying_Price']
      
        # 3. Rudisha jumla kuu
        thamani_kuu = df_final['Actual_Value'].sum()
        idadi_kuu = df_final['Zilizobaki'].sum()
        return thamani_kuu,idadi_kuu
   except Exception as e:
        print(f"Error kwenye Thamani: {e}")
   return 0, 0

pesa_stoo,vitu_stoo=calculate_inventory_value()
  
    
def check_password():
   if "welcomed" not in st.session_state:
      st.session_state["welcomed"]=False
   #ARVISI
   st.markdown("""
      
      
      <style>
      @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
      
               
      /*rangi ya background ya ukurasa wote wa log in*/
       .stApp { background-color: #0e1117; }
      }
      }
      /*Box la password*/
      div[data-baseweb="input"]{
         boarder:2px solid #00f2ff !important;
         boarder-radius:10px;
         box-shadow:none !important;
         input[type="password"]{box-shadow:0 0 15px #00f2ff !important;}
         
         
         
      }
      /*Maandishi ya jarvis*/
      .jarvis-title{
         color:#002ff;
         font-family:'Courier New',Courier,monospace
         text-align:left !important;
         margin-left:0px !important;
         padding-left:0px !important;
         margin-bottom;10px;
         text-shadow:2px 2px 10px #002ff;
         font-size:40px;
         font-weight:bold;
         letter-spacing: 5px;
         text-transform: uppercase;
         text-shadow:0 0 5px #00f2ff,0 0 10px #00f2ff,0 0 20px #00f2ff;
         margin-left:0px !important;
       
        
       
               
      }
               
       
       
               
      /*nembo ya kali linuc*/
      .kali-container{
         display:block;
         margin-left:auto;
         margin-rigth:auto;
         width:300px !important;
         height:auto !important;
         opacity:0.9;
         filter:invert(1)brightness(1.2)drop-shadow(0 0 15px #00f2ff);
         text-align:centre;
         margin-bottom:20px;
      }
      
      .stTextInput label p{
         font-family: 'Orbitron',sans-serif !important;
         color: #00f2ff !important;
         letter-spacing:2px;
         letter-shadow:0 0 5px #00f2ff;
         text-transform:uppercase;
      }
      
    
      
               
      </style>
      """,unsafe_allow_html=True)
   
   
  

   if "password_correct" not in st.session_state:
  
      st.info("System Locked:Waiting for Athorization From Frank Shirima")
      st.text_input("ENTER ACCESSS CODE",type="password",on_change=password_entered,key="password")
      col1, col2, col3=st.columns([1,2,1])
      with col2:
     
        st.markdown('<div class="kali-container"><img src="data:image/png;base64,{}"></div>'.format(image_to_base64("kali.png")),unsafe_allow_html=True)
        st.markdown('<p class="jarvis-title"style="font-size:20px; margin-top:10px; ">CYBERGATES LABS</p>',unsafe_allow_html=True)
      
      return False

   elif not st.session_state['password_correct']:
     st.markdown("""
               <p style="
               color:#ff0000;
               font-family:'Orbitron',sans-serif;
               text-align:centre;
               text-shadow:0 0 15px #ff0000;
               font-size:18px;
               font-weight:bold;
               letter-spacing:5px;
               margin-top:20px;
               ">
                 ACCESS DENIED
               </p>
               
                """,unsafe_allow_html=True)
     st.text_input("ENTER ACCESS CODE", type="password", on_change=password_entered,key="password")
     st.error("Authetication Failed:Security Breach Protocol Initilized")
     return False
   else:
    if st.session_state["password_correct"] and not st.session_state["welcomed"]:

      st.balloons()
      st.toast("Access Granted Welcome Back, Mr Shrima.")
      st.session_state["welcomed"] = True

    
    
    
   return True


if check_password():
 


 
   
  


 st.set_page_config(page_title="KWA SHIRIMA AI", layout="wide")
 st.title("📊 Prophet Dashboard  - KWA SHIRIMA Store")

# 1. Pakia Dat
 df = mauzo_global.copy()
 try:
   # 1. Hifadhi inventory kwenye session_state ili isifutike
    if 'inventory_awal' not in st.session_state:
     st.session_state.inventory_awal = {
        'Mapazia': 1000,
        'Saa za Ukutani': 950,
        'Mazulia': 900,
        'Taa za Kupamba': 850,
        'Vases': 920
    }
# 2. Sasa hapa ndipo unapopiga hesabu (Hii iwe chini ya session state ya juu)

    # 1. Geuza session state kuwa DataFrame (Hakikisha jina la column ni 'Total_Stock')
    df_stock = pd.DataFrame(list(st.session_state.inventory_awal.items()), columns=['Category', 'Total_Stock'])

# 2. Piga hesabu ya mauzo (Tumia reset_index TU, usiweke .to_dict())
    
    mauzo_kwa_bidhaa = df.groupby('Category')['Qty'].sum().reset_index()

# 3. Unganisha meza mbili (Hapa sasa itakubali bila error)
    df_hali_ya_stoo = pd.merge(df_stock, mauzo_kwa_bidhaa, on='Category', how='left').fillna(0)

# 4. Piga hesabu ya stock iliyobaki
    df_hali_ya_stoo['iliyobaki'] = df_hali_ya_stoo['Total_Stock'] - df_hali_ya_stoo['Qty']
      
    df['Date'] = pd.to_datetime(df['Date'])

    # 1. Maandalizi ya tarehe
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    #leo_halisi = df['Date'].max()
    leo_halisi = datetime.datetime.now().date()

     # 2. Dropdown ya kuchagua kipindi
    pamoja = st.selectbox("Linganisha Mauzo ya:", ["Siku (Leo vs Jana)", "Wiki (Hii vs Iliyopita)", "Mwezi (Huu vs Uliopita)"])

    
# 3. Logic ya kulinganisha
    if pamoja == "Siku (Leo vs Jana)":
       k1_start, k1_end = leo_halisi, leo_halisi
       k2_start, k2_end = leo_halisi - timedelta(days=1), leo_halisi - timedelta(days=1)
       label1, label2 = "Leo", "Jana"

      
    elif pamoja == "Wiki (Hii vs Iliyopita)":
       k1_start, k1_end = leo_halisi - timedelta(days=6), leo_halisi
       k2_start, k2_end = k1_start - timedelta(days=7), k1_start - timedelta(days=1)
       label1, label2 = "Wiki Hii", "Wiki Iliyopita"

    
    else: # Mwezi (Kalenda)
    # Mwezi huu: Kuanzia tarehe 1 ya mwezi huu mpaka leo
       k1_start = leo_halisi.replace(day=1)
       k1_end = leo_halisi
    
    # Mwezi uliopita: Siku ya mwisho ya mwezi uliopita
       punda = k1_start - timedelta(days=1) 
    # Kuanzia tarehe 1 ya mwezi uliopita mpaka mwisho wake
       k2_start = punda.replace(day=1)
       k2_end = punda
    
       label1, label2 = "Mwezi Huu ", "Mwezi Uliopita "


    # 4. Piga hesabu za jumla
    m1 = df[(df['Date'] >= k1_start) & (df['Date'] <= k1_end)]['Total'].sum()
    m2 = df[(df['Date'] >= k2_start) & (df['Date'] <= k2_end)]['Total'].sum()
    diff = m1 - m2


    # 2. Side Bar ya Utabiri
    with st.sidebar:
     st.header("⚙️ Mipangilio ya AI")
     siku_za_mbele = st.slider("Chagua Siku za Kutabiri Mauzo:", 7, 90, 30)

    st.sidebar.divider()
 
    # 1. Pakia dictionary ya bei
    df_stoo = stoo_global.copy()
    bei_kununua_dict = dict(zip(df_stoo['Category'], df_stoo['Buying_Price']))
    

    # --- FORM MPYA YA KUINGIZA MAUZO ---
    
# 2. Ujanja wa 'Session State' ili ku-update bei live
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = list(bei_kununua_dict.keys())[0]


    categories_options = list(bei_kununua_dict.keys()) if bei_kununua_dict else ["Hakuna Bidhaa"]

    new_category = st.sidebar.selectbox(
    "Aina ya Bidhaa",
    options=categories_options,
    )

# 3. ANZA FORM (Sasa bei itaonekana humu ndani ikiwa imeshabadilika)
    with st.sidebar.form("sales_form", clear_on_submit=True):
    # Tunachukua bei kulingana na ulichochagua hapo juu
     current_price = bei_kununua_dict.get(new_category, 0)
     
     mauzo_ya_sasa = mauzo_global[mauzo_global['Category'] == new_category]['Qty'].sum()
     jumla_stoo = stoo_global[stoo_global['Category'] == new_category]['Total_Stock'].sum()   
     stock_qty = int(jumla_stoo) - int(mauzo_ya_sasa)
     # HAPA NDIPO INAPOONEKANA NDANI YA BOX KABLA YA SUBMIT
     if stock_qty > 0:
        st.success(f"📦 Zilizobaki stoo: {stock_qty}")
     else:
        st.error(f"⚠️ Zilizobaki stoo: {stock_qty}")


     st.markdown(f"💰 **Bei ya Stoo kwa {new_category}:**")
     st.code(f"TSh {current_price:,.0f}") 
    
     tarehe_mpya = st.date_input("Tarehe", value=datetime.date.today())
     new_qty = st.number_input("Idadi (Qty)", min_value=1, step=1)
     new_total = st.number_input("Jumla ya Pesa uliyopokea (TZS)", min_value=0, step=5000)
     # Hii inatengeneza button, lakini kama stock ni 0, button inakuwa 'disabled' (haiwezi kubonyezwa)
     submitted = st.form_submit_button(
    "Hifadhi Mauzo" if stock_qty > 0 else "Out of Stock",
     disabled=(stock_qty <= 0)
     )

    if submitted:
    # Mahesabu ya faida na bei
     profit_made = new_total - (current_price * new_qty)
     unit_price = int(new_total / new_qty) if new_qty > 0 else 0
    
    # Kutengeneza row mpya ya data
     new_row = pd.DataFrame([[
        tarehe_mpya.strftime("%Y-%m-%d"), new_category, new_qty, 
        unit_price, new_total, profit_made
     ]], columns=['Date', 'Category', 'Qty', 'Unit_Price', 'Total', 'Profit'])
    
    # Kuhifadhi kwenye Google Sheets
     updated_mauzo = pd.concat([mauzo_global, new_row], ignore_index=True)
     conn.update(worksheet="mauzo", data=updated_mauzo)
     st.success("Mauzo yamehifadhiwa kikamilifu!")
     st.rerun() 
  

    

     
# 2. Sukuma data yote iliyohuishwa kwenda Google Sheets
    # 2. Sukuma data yote iliyohuishwa kwenda Google Sheets
     
       

    # 2. Onyesha kwenye Sidebar (Pemben Kabisa)
    st.sidebar.markdown("---") # Mstari wa kutenganisha
    st.sidebar.subheader("💼 Duka Portfolio")
    st.sidebar.write("Thamani ya stoo(Total)")
    st.sidebar.subheader(f"{pesa_stoo:,.0f}")

    st.divider()
    st.sidebar.write("idadi ya bidhaa(Total)")
    st.sidebar.subheader(f"{vitu_stoo:,.0f}Pcs")

     # Piga hesabu ya thamani ya sasa hivi
    total_value = calculate_inventory_value()

    st.sidebar.markdown("---")







   # --- Hesabu za Wastani (Sidebar) ---
# Tunatafuta wastani wa mwezi huu uliopo kwenye CSV
    mwezi_huu_data = df[df['Date'] >= (leo_halisi - timedelta(days=30))]
    wastani_kwa_siku = mwezi_huu_data.groupby('Date')['Total'].sum().mean()

    st.sidebar.divider() # Mstari wa kutenganisha
    st.sidebar.subheader("Muhtasari wa Haraka")

# Onyesha wastani kwa maandishi madogo au metric ndogo
    st.sidebar.metric(label="Wastani wa Mauzo/Siku", value=f"{wastani_kwa_siku:,.0f} TZS")






   

# Unaweza pia kuweka lengo la mwezi hapa kidogo
    st.sidebar.divider()
    st.sidebar.subheader("🎯 Target Control")
    
    # Hapa sasa unaset lengo mwenyewe kwenye Dashboard!
    lengo_la_mwezi = st.sidebar.number_input("Weka Lengo la Mwezi (TZS)", value=900000, step=1000000)
    # 2. Piga hesabu ya asilimia (Hapa ndipo variable inatengenezwa sasa)
    # Hakikisha 'm1' imeshapigiwa hesabu juu, kama bado tumia: m1 = df['Total'].sum()
    asilimia_ya_lengo = (m1 / lengo_la_mwezi) * 100
    asilimia_ya_lengo_display = min(asilimia_ya_lengo, 100.0)
    
    # Piga hesabu ya asilimia
    # Chagua rangi kulingana na maendeleo
    bar_color = "#ff0000" if asilimia_ya_lengo < 50 else "#ffaa00" if asilimia_ya_lengo < 80 else "#00ff00"
    
    st.sidebar.markdown(f"""
        <div style="width: 100%; background-color: #262730; border-radius: 20px; border: 1px solid #444;">
            <div style="
                width: {asilimia_ya_lengo}%; 
                background: linear-gradient(90deg, {bar_color}, #ffffff); 
                height: 20px; 
                border-radius: 20px; 
                box-shadow: 0 0 15px {bar_color};
                transition: width 1s ease-in-out;
            "></div>
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
    

       
    #hpa kiwango ch chini
    
# 3. Tengeneza ripoti ya Low Stock
    st.sidebar.divider()
    st.sidebar.subheader("🚀 Low Stock Alerts")

    def get_low_stock_data():
        df_stoo = stoo_global.copy()
        df_mauzo= mauzo_global.copy()

        #safisha data
        df_stoo['Category']=df_stoo['Category'].astype(str).str.strip()
        df_mauzo['Category']=df_mauzo['Category'].astype(str).str.strip()

        #piga hesabu ya mauzo
        mauzo_sum=df_mauzo.groupby('Category')['Qty'].sum().reset_index()

        #unganisha na hesabun iliyobaki
        df_final=pd.merge(df_stoo,mauzo_sum,on='Category',how='left').fillna(0)
        df_final['iliyobaki']=df_final['Total_Stock']-df_final['Qty']

        return df_final
    
    #pata data sas hiv
    current_hali = get_low_stock_data()

    #weka kikom chako
    LOW_STOCK_LIMIT = 10

    #chuja bihdaa
    low_stock_items = current_hali[current_hali['iliyobaki']<=LOW_STOCK_LIMIT]




# 3. Kama kuna bidhaa, toa onyo (Alert)
    if not low_stock_items.empty:
     for _,row in low_stock_items.iterrows():
        baki = int(row['iliyobaki'])
        bidhaa = row['Category']

        if baki <=0:
         st.sidebar.error(f"⚠️ **{bidhaa}** IMEKWISHA!:{baki}")
        else:
         st.sidebar.error(f"⚠️**{bidhaa}** imebaki:{baki}")
    else:
      st.sidebar.success("✅ Bidhaa zote zipo za kutosha!") 

   
  
    
    st.sidebar.divider()
    st.sidebar.subheader("📦 Ongeza Mzigo Mpya")
    
    #soma fail la stoo kupsta list kamil ya bidhaa
    df_stoo_list = stoo_global.copy()
    list_ya_bidhaa = df_stoo_list['Category'].unique().tolist()

# 1. Tengeneza Form ya kuingiza mzigo
    with st.sidebar.form("stock_form"):
      bidhaa_mpya = st.selectbox("Chagua Bidhaa",list_ya_bidhaa)
      kiasi_kipya = st.number_input("idadi",min_value=1)
      submit_stock = st.form_submit_button("Hifadhi mzigo")
    
    if submit_stock:
        # 1. Soma faili la stoo
        df_stoo = stoo_global.copy()
        
        # 2. Tafuta mstari wa bidhaa
        mask = df_stoo['Category'] == bidhaa_mpya
        
        if mask.any():
            # A. Pata idadi ya sasa (Hakikisha ni namba)
            idadi_ya_sasa = int(pd.to_numeric(df_stoo.loc[mask, 'Total_Stock']).iloc[0])
            idadi_mpya = idadi_ya_sasa + int(kiasi_kipya)
            
            # B. SASISHA CSV MOJA KWA MOJA (Usiguse bei hapa ili isirudi 0)
            df_stoo.loc[mask, 'Total_Stock'] = idadi_mpya
            conn.update(worksheet="stoo", data=df_stoo)
            
            # C. SASISHA SESSION STATE ILI GRAPH IONYESHE NAMBA MPYA
            if 'inventory_awal' in st.session_state:
                st.session_state.inventory_awal[bidhaa_mpya] = idadi_mpya
            
            st.success(f"✅ Imefanikiwa! {bidhaa_mpya} sasa zipo {idadi_mpya}")
            st.rerun()
        else:
            st.error("Bidhaa haijapatikana!")

    st.sidebar.divider()
    st.sidebar.subheader("🆕 Ongeza Bidhaa Mpya Kabisa")

# 1. Form ya kuingiza bidhaa ambayo haipo kwenye list
    

    with st.sidebar.form("new_item_form", clear_on_submit=True):
     jina_la_bidhaa = st.text_input("Andika jina la bidhaa ")
     idadi_ya_mwanzo = st.number_input("Idadi ya mwanzo", min_value=1)
     bei_ya_kununulia = st.number_input("Bei ya kununulia(moja)",min_value=1)
     submit_new = st.form_submit_button("Sajili Sasa")

    if submit_new and jina_la_bidhaa:
    # 1. Soma faili la sasa
       df_stoo = stoo_global.copy()
    
    # 2. Tengeneza mstari wa bidhaa mpya
       new_row = {
        'Category': jina_la_bidhaa,
        'Total_Stock': int(idadi_ya_mwanzo),
        'Buying_Price': float(bei_ya_kununulia)
       }
    
    # 3. Ongeza bidhaa mpya kwenye DataFrame
       df_stoo = pd.concat([df_stoo, pd.DataFrame([new_row])], ignore_index=True)
    
    # 4. HIFADHI KWA NGUVU KWENYE CSV (Hii inazuia isipotee ukirefresh)
       conn.update(worksheet="stoo", data=df_stoo)
    
    # 5. Sasisha session state ili ionekane kwenye graph na selectbox papo hapo
       if 'inventory_awal' in st.session_state:
           st.session_state.inventory_awal[jina_la_bidhaa] = int(idadi_ya_mwanzo)
    
       st.toast(f"✅ {jina_la_bidhaa} imesajiliwa milele!")
       st.rerun()





    st.subheader(f"Uchambuzi wa Mauzo: {pamoja}")
    col_a, col_b = st.columns(2)

    with col_a:
      st.metric(label=label1, value=f"{m1:,.0f} TZS", delta=f"{diff:,.0f} TZS")

    with col_b:
      st.metric(label=label2, value=f"{m2:,.0f} TZS")

    #piga hesabu za faida
    m1_profit = df[(df['Date'] >= k1_start) & (df['Date'] <= k1_end)]['Profit'].sum()
    m2_profit = df[(df['Date'] >= k2_start) & (df['Date'] <= k2_end)]['Profit'].sum()

    #tafuta asilimia
    if m2_profit > 0:
       growth_pct =((m1_profit-m2_profit)/m2_profit)*100
    else:
       growth_pct = 0

    #onyesh matokeo
    st.write("___")
    st.subheader(f"Uchambuzi wa Faida:{pamoja}")
    p_col1,p_col2 = st.columns(2)

    with p_col1:
       st.metric(label=f"Fida({label1})",
                 value=f"{m1_profit:,.0f}TZS",
                 delta=f"{growth_pct:,.1f}% vs {label2}")
       
    with p_col2:
       st.metric(label=f"Faida({label2})", value=f"{m2_profit:,.0f}TZS")
       


    # 4. Onyesha Matokeo kwenye Dashboard
    col1, col2 = st.columns(2)

    with col1:
           st.subheader("Mwenendo wa Mauzo ya Nyuma")
           df_graph = mauzo_global.copy()
           df_graph['Date']=pd.to_datetime(df_graph['Date']).dt.date

           daily_sales=df_graph.groupby('Date')['Total'].sum().reset_index().sort_values('Date')
      
           st.line_chart(data=daily_sales,x='Date',y='Total',use_container_width=True)



    with col2:
        # Hakikisha unatumia jina sahihi la faili lako la CSV
        df_mauzo_csv = mauzo_global.copy()

# Muhimu: Badilisha column ya Date iwe tarehe halisi ili Prophet isilete error
        df_mauzo_csv['Date'] = pd.to_datetime(df_mauzo_csv['Date']).dt.date
   
        st.markdown(f"#### 🔮 Utabiri wa Mauzo")
    
    # Ita function ya Prophet
        forecast = piga_utabiri_wa_mauzo(df_mauzo_csv, siku_za_mbele)
    
        if forecast is not None:
        # 1. Chora Grafu kwanza (Inakaa juu)
         future_only = forecast.tail(siku_za_mbele)
         st.line_chart(future_only.set_index('ds')['yhat'])
        
        # 2. Weka namba ya matokeo kwa chini (Hitimisho)
         mauzo_yatarajiwa = forecast['yhat'].iloc[-1]
         st.metric(
            label=f"Mauzo ya Siku ya {siku_za_mbele}", 
            value=f"{mauzo_yatarajiwa:,.0f} TZS"
        )
         
    st.divider()
    st.write("### 📜 Historia ya Mauzo: Kwa Shirima Store")

# 1. Hakikisha tarehe zipo kwenye format sahihi
    df_mauzo_csv['Date'] = pd.to_datetime(df_mauzo_csv['Date'], errors='coerce')

    # Angalia kama kuna tarehe yoyote halali, la sivyo weka tarehe ya leo kama default
    if not df_mauzo_csv['Date'].dropna().empty:
        default_start = df_mauzo_csv['Date'].min().date()
        default_end = df_mauzo_csv['Date'].max().date()
    else:
        import datetime
        default_start = datetime.date.today()
        default_end = datetime.date.today()

# 2. Sehemu ya kuchuja tarehe (Filter)
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        t_anza = st.date_input("Kuanzia tarehe:", default_start, key="start_hist")
    with col_h2:
        t_isha = st.date_input("Mpaka tarehe:", default_end, key="end_hist")
# 3. Logic ya kuchuja (Masking)
    # 3. Logic ya kuchuja (Masking) kwa kulinganisha tarehe tupu pekee
    mask = (df_mauzo_csv['Date'].dt.date >= t_anza) & (df_mauzo_csv['Date'].dt.date <= t_isha)
    df_filtered = df_mauzo_csv.loc[mask].copy()

# 4. Onyesha Table
    if not df_filtered.empty:
    # Tunatengeneza column ya pesa iliyopambwa (Format)
     df_filtered['Total (Tsh)'] = df_filtered['Total'].apply(lambda x: f"{x:,.0f}")
    
    # Hapa tunachagua column zinazoendana na biashara yako (Bidhaa, Idadi, Bei, Jumla)
    # Tuseme CSV yako ina: Date, Product, Quantity, Price, Total
     st.dataframe(
        df_filtered[['Date', 'Category', 'Qty', 'Unit_Price', 'Total']], 
        use_container_width=True,
        hide_index=True
    )
    
    # 5. Jumla ya Pesa kwa chini
     st.success(f"💰 Jumla ya Mapato Kipindi Hiki: **Tsh {df_filtered['Total'].sum():,.0f}**")
    else:
     st.warning("Hakuna mauzo yaliyopatikana katika kipindi ulichochagua.")
    


   

    # 5. Uchambuzi wa Bidhaa (Next Wants)
    st.divider()
    st.subheader("🔍 Wateja wanapenda nini zaidi? (Product Analysis)")
    
    top_5_data = df.groupby('Category')['Qty'].sum().sort_values(ascending=False).head(5)
    names = list(top_5_data.index)
    vals = list(top_5_data.values)

    c1,c2,c3,c4,c5=st.columns(5)

    if len(names)>0:c1.metric(names[0],f"{int(vals[0])}Pcs")
    if len(names)>1:c2.metric(names[1],f"{int(vals[1])}Pcs")
    if len(names)>2:c3.metric(names[2],f"{int(vals[2])}Pcs")
    if len(names)>3:c4.metric(names[3],f"{int(vals[3])}Pcs")
    if len(names)>4:c5.metric(names[4],f"{int(vals[4])}Pcs")
    st.divider()


   

# 1. TAYARISHA DATA (Hapa unatumia mauzo yako)
# Tunatumia top_5_data yako iliyopo kwenye picha
    if not top_5_data.empty:
       labels = top_5_data.index
       sizes = top_5_data.values
    
    # 2. TUNABANISHA GRAPH KATIKATI KWA COLUMNS (Ukubwa unadhibitiwa hapa)
    # columns=[1, 2, 1] maana yake graph itakuwa katikati ya kioo
    # Na itachukua nusu tu ya kioo (ukilinganisha na columns=[1,1,1])
       colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99', '#c2c2f0', '#ffb3e6']
       col1, col2, col3 = st.columns([1, 2, 1])
    
       with col2:
       
         fig, ax1 = plt.subplots(figsize=(5, 5)) 
    
    # Hapa tumeweka rangi ya majina (labels) kuwa 'black'
         wedges, texts, autotexts = ax1.pie(
         sizes, 
         labels=labels, 
         autopct='%1.1f%%', 
         startangle=90, 
         colors=colors, 
         pctdistance=0.75,   
         labeldistance=1.1,  
         textprops={'color': "black", 'fontsize': 10, 'fontweight': 'bold'} # 'black' hapa kwa ajili ya majina
        )

        # 4. CHORA DUARA JEUPE KATIKATI (Tundu la Donut)
        # fc='black' ili iendane na theme yako ya Dark Mode
         centre_circle = plt.Circle((0,0), 0.70, fc='black')
         fig = plt.gcf()
         fig.gca().add_artist(centre_circle)

        # 5. REMBA ASILIMIA KATIKATI YA DUARA
         for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_weight('bold')
            autotext.set_fontsize(10) # Inafanya asilimia zisiwe kubwa sana

        # 6. ONGEZA JUMLA YA MAUZO KATIKATI (Kama ukipenda)
         jumla_mauzo = int(sizes.sum())
         ax1.text(
            0, 0, f"{jumla_mauzo}\nPcs", 
            ha='center', va='center', 
            fontsize=14, color='white', fontweight='bold'
        )

         ax1.axis('equal') 
         plt.tight_layout()
        
        # 7. ONYESHA KWENYE STREAMLIT
        # use_container_width=True sasa hivi itatumia upana wa Column 2 tu
         st.pyplot(fig, use_container_width=True) 
    else:
     st.warning("Hakuna data za mauzo bado!")



    
    st.divider()
    st.subheader("📊 Mauzo ya Bidhaa Zote")
    st.bar_chart(df.groupby('Category')['Qty'].sum().sort_values(ascending=False))
  
    st.markdown("### 📋 Mchanganuo wa Stoo (Inventory)")

    # 1. Soma data za Stoo
    df_stoo = stoo_global.copy()

    # 2. Soma data za Mauzo na piga hesabu ya jumla ya kila bidhaa
    try:
      df_mauzo = mauzo_global.copy()
      mauzo_sum = df_mauzo.groupby('Category')['Qty'].sum().reset_index()
      mauzo_sum.columns = ['Category', 'Zilizouzwa']
    except:
    # Kama faili halipo bado, weka 0
       mauzo_sum = pd.DataFrame(columns=['Category', 'Zilizouzwa'])

    # 3. Unganisha Stoo na Mauzo (Merge)
    df_final = pd.merge(df_stoo, mauzo_sum, on='Category', how='left').fillna(0)

    # 4. Piga hesabu ya Zilizobaki na badilisha kuwa Integer (Namba kamili)
    df_final['Zilizobaki'] = (df_final['Total_Stock'] - df_final['Zilizouzwa']).astype(int)
    df_final['Total_Stock'] = df_final['Total_Stock'].astype(int)
    df_final['Zilizouzwa'] = df_final['Zilizouzwa'].astype(int)

    # 5. Pangilia safu (Columns) kwa majina unayotaka
    df_display = df_final[['Category', 'Total_Stock', 'Zilizouzwa', 'Zilizobaki']]
    df_display.columns = ['Aina ya Bidhaa', 'Mzigo Ulioingia', 'Zilizouzwa', 'Zilizobaki']

    # 6. FUNCTION YA RANGI: Inapaka nyekundu ikiwa Zilizobaki < 5
    def highlight_low_stock(row):
      color = 'background-color: #ff4b4b; color: white' if row['Zilizobaki'] < 10 else ''
      return [color] * len(row)

    # 7. Onyesha Jedwali lenye urembo wa rangi
    st.dataframe(df_display.style.apply(highlight_low_stock, axis=1), use_container_width=True)


    st.divider()
    st.subheader("Orders Table")


    bidhaa_zilizopo=list(df_stoo['Category'].unique())
   
    #form ya kuongeza mteja
    with st.expander("Bonyeza hapa kusajili Oda Mpya"):
       with st.form("new_order_form",clear_on_submit=True):
          col1,col2=st.columns(2)
          with col1:
             mteja_mpya=st.text_input("Jina la Mteja")
             simu_mpya=st.text_input("Namba Mpya")
             #soma bidhaa halisi toka kwy stoo
             chaguo=st.selectbox("Chagua Bidhaa",bidhaa_zilizopo)

             bidhaa_mpya_text=st.text_input("Kama Bidhaa ni Mpya,andika apa:")
             location_mpya=st.text_input("Mteja anatokea wapi:")
             # Ongeza mstari huu ndani ya 'with col2':
            
       with col2:
          qty_mpya=st.number_input("Idadi(Qty)",min_value=1,step=1)
          advanced_mpya=st.number_input("Advanced(TZS)",min_value=0,step=5000)
          hali_mpya = st.selectbox("Hali ya Oda",["Pending","Completed","Canceled"])
          tarehe_mpya = st.date_input("Chagua Tarehe")

          if bidhaa_mpya_text.strip()!="":
             bidhaa_final = bidhaa_mpya_text
          else:
             bidhaa_final=chaguo


       
          if st.form_submit_button("Hifadhi Oda"):
           if mteja_mpya and simu_mpya and bidhaa_final:
             mpya={
                'Tarehe':tarehe_mpya.strftime("%Y-%m-%d"),
                'Mteja':mteja_mpya,
                'Simu':str(simu_mpya),
                'Bidhaa':bidhaa_final,
                'Qty':qty_mpya,
                'Advanced':advanced_mpya,
                'Status':hali_mpya,
                'Location':location_mpya
             }
             # 1. Unda DataFrame ya oda mpya
             new_order_df = pd.DataFrame([mpya])

# 2. Unganisha na data ya zamani
             df_updated = pd.concat([orders_global, new_order_df], ignore_index=True)

# 3. Kitu muhimu: Geuza DataFrame nzima kuwa string ili kuzuia automatic formatting
             df_updated = df_updated.astype(str)

# 4. Safisha 'NaT' au 'nan' zozote zilizojitokeza wakati wa ku-convert
             df_updated = df_updated.replace({'NaT': '', 'nan': ''})

# 5. Tuma kwenye Google Sheets
             conn.update(worksheet="orders", data=df_updated)

# 6. Malizia na ujumbe wa mafanikio na refresh
             st.success(f"Oda ya {mteja_mpya} imepokelewa!")
             st.rerun()
 
        



    #soma data ya sas


    df_orders = orders_global.copy()

    # Badilisha tarehe kuwa format inayoeleweka
    # 1. Badilisha tarehe kuwa format inayoeleweka kisha ondoa zilizo tupu
    df_orders['Tarehe'] = pd.to_datetime(df_orders['Tarehe'], errors='coerce')
    
    
    # --- ONGEZA HII SEHEMU YA KUSAFISHA DATA ---
    # Badilisha namba kuwa integer ili kuondoa .00000
    df_orders['Qty'] = pd.to_numeric(df_orders['Qty'], errors='coerce').fillna(0).astype(int)
    df_orders['Advanced'] = pd.to_numeric(df_orders['Advanced'], errors='coerce').fillna(0).astype(int)
    
    # Badilisha Simu kuwa string ili isipoteze sifuri za mwanzo
    df_orders['Simu'] = df_orders['Simu'].astype(str).str.replace('.0', '', regex=False)
    # --------------------------------------------
    valid_order_dates = df_orders['Tarehe'].dropna()

    if not valid_order_dates.empty:
        default_order_start = valid_order_dates.min().date()
        default_order_end = valid_order_dates.max().date()
    else:
        import datetime
        default_order_start = datetime.date.today()
        default_order_end = datetime.date.today()

    st.write("Chuja Oda Kwa Tarehe")
    col_date1, col_date2 = st.columns(2)

    with col_date1:
        start_date = st.date_input("Kuanzia:", default_order_start, key="start_order_hist")
    with col_date2:
        end_date = st.date_input("Mpaka:", default_order_end, key="end_order_hist")

    st.write("Filter Status")
    status_options = df_orders['Status'].unique().tolist()
    status_filter = st.multiselect("Chagua Hali:", options=status_options, default=status_options)

    # Logic ya kuchuja (Masking) kwa kulinganisha tarehe pekee (.dt.date)
    # Hakikisha safu ya 'Tarehe' ni datetime na jaza tupu ili isiwe na NaT
    temp_dates = pd.to_datetime(df_orders['Tarehe'], format='%Y-%m-%d', errors='coerce')

    # Fanya masking kwa kutumia series iliyosafishwa
    mask = (temp_dates.dt.date >= start_date) & \
           (temp_dates.dt.date <= end_date) & \
           (df_orders['Status'].isin(status_filter))

    df_filtered = df_orders[mask]
   
    # 1. Badilisha hapa kuweka "Kinga" ya if
    if not df_filtered.empty:
       total_advance= int(df_filtered['Advanced'].sum())
       st.metric(label=f"Jumla ya Advance({start_date} mpaka {end_date})",value=f"{total_advance:,.0f}TZS")
    else:
       st.info("Hakuna Oda ya Kipindi iki")
                 
                 
    st.dataframe(df_filtered.style.applymap(style_status,subset=['Status']), use_container_width=True)

    #chagua order unayotaka
    if not df_orders.empty:
       target_customer = st.selectbox("Chagua mteja wa kumfanyia marekebisho:",df_orders['Mteja'].unique())

       col_a,col_b,col_c=st.columns(3)

       with col_a:
          #badilisha status
          new_status=st.selectbox("Badilisha Hali(Status):",["Pending","Completed","Canceled"])
          ongeza_hela=st.number_input("Ongeza Pesa Ya Advance(TZS):",min_value=0,step=5000)

          if st.button("Update Status"):
             df_temp = orders_global.copy()

             idx = df_temp[df_temp['Mteja']==target_customer].index

             if not idx.empty:
                hela_ya_zamani=df_temp.at[idx[0],'Advanced']

                hela_ya_jumla = hela_ya_zamani+ongeza_hela

                df_temp.at[idx[0],'Advanced']=hela_ya_jumla
                df_temp.at[idx[0],'Status']=new_status

                conn.update(worksheet="orders", data=df_temp)
             
                st.success(f"Oda ya {target_customer}sasa ni {new_status}")
                st.rerun()



       with col_b:
            with st.popover("Futa Oda Hii"):
                st.write("Je, una uhakika unataka kufuta oda hii? Hatua hii haiwezi kutenduliwa!")
                
           
          #futa oda kabisa
                if st.button("Futa Oda Hii"):
                   df_orders=df_orders[df_orders['Mteja']!=target_customer]
                   conn.update(worksheet="orders", data=df_orders)
                   st.warning(f"Oda ya {target_customer}imefutwa!")
                   st.rerun()

       with col_c:
          st.write("**Maelekezo ya Order:**")
          info = df_orders[df_orders['Mteja']==target_customer].iloc[0]

          st.write(f"Tarehe:{info['Tarehe']}")
          st.write(f"Bidhaa:{info['Bidhaa']}")
          st.write(f"Idadi:{info['Qty']}Pcs")
          st.write(f"Simu:{info['Simu']}")
          st.write(f"Advanced:{info['Advanced']}TZS")
          st.write(f"Location:{info['Location']}")


          #logic ya rangi
          status_sasa =info['Status']
          if status_sasa=="Pending":
             st.error(f"Hali:{status_sasa}")
          elif status_sasa == "Completed":
             st.success(f"Hali:{status_sasa}")
          else:
             st.info(f"Hali:{status_sasa}")
    else:
       st.info("Hakuna oda za kufanyiwa marekebisho kwa sasa")

    st.divider()
    st.subheader("🔮 Frank AI: Profit Analysis")

    col_top1, col_top2 = st.columns([2, 1])
    with col_top2:
        siku_adjust = st.slider("Adjust Siku:", 7, 90, 30, key="fs_slider")

    # Hapa ndipo sasa tunaita function na kuonyesha grafu
    with st.spinner("Frank AI is analysing profit..."):
        matokeo = piga_utabiri_wa_faida(df_mauzo_csv, siku_adjust)
    
        if matokeo is not None:
            c1, c2 = st.columns([2, 1])
            with c1:
                # --- TOLEO JIPYA: GRAFU YA KIJANJA YA PLOTLY ---
                import plotly.graph_objects as go
                
                fig = go.Figure()

                # 1. Weka kivuli cha usalama (Upper and Lower bounds)
                fig.add_trace(go.Scatter(
                    x=pd.concat([matokeo['ds'], matokeo['ds'][::-1]]),
                    y=pd.concat([matokeo['yhat_upper'], matokeo['yhat_lower'][::-1]]),
                    fill='toself',
                    fillcolor='rgba(0, 176, 246, 0.15)', # Rangi ya bluu ya uwazi
                    line=dict(color='rgba(255,255,255,0)'),
                    hoverinfo="skip",
                    showlegend=True,
                    name='Mipaka ya Utabiri (Usalama)'
                ))

                # 2. Weka mstari mkuu wa utabiri wa AI (Trend Line)
                fig.add_trace(go.Scatter(
                    x=matokeo['ds'],
                    y=matokeo['yhat'],
                    mode='lines',
                    line=dict(color='#00B0F6', width=3), # Mstari wa bluu uliokolea
                    name='Utabiri wa Faida'
                ))

                # 3. Muonekano wa Kijasusi (Dark Theme Layout)
                fig.update_layout(
                    title='Mwelekeo wa Faida na Maeneo ya Kiusalama',
                    xaxis_title='Tarehe',
                    yaxis_title='Faida (TZS)',
                    template='plotly_dark', # Inafanya grafu iwe na giza
                    hovermode='x unified',  # Inapakia data zote ukisogeza mouse juu ya tarehe
                    paper_bgcolor='rgba(0,0,0,0)', # Inafanya background iendane na app
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )

                # Onyesha grafu ya Plotly kwenye Streamlit
                st.plotly_chart(fig, use_container_width=True)
                # --- MWISHO WA GRAFU YA PLOTLY ---

            with c2:
                faida_ijayo = matokeo['yhat'].iloc[-1]
                st.metric(label=f"Faida ya Siku {siku_adjust}", value=f"{faida_ijayo:,.0f} TZS")
        else:
            st.error("AI imeshindwa kusoma data. Hakikisha CSV ina 'Date' na 'Profit'.")
            
# 3. Onyesha data za sasa kwa ufupi (Comparison)
    st.write("---")
    total_profit_now = df_mauzo_csv['Profit'].sum()
    st.write(f"**Jumla ya Faida Mpaka Sasa:** TSh {total_profit_now:,.0f}") 
       
      
   
    st.divider()
    st.write("### 📊 Ripoti na Uchambuzi wa Biashara (Mauzo & Stoo)")

# Soma faili la mauzo moja kwa moja hapa kwa ajili ya ripoti
    try:
      df_mauzo_ripoti = mauzo_global.copy()
    except Exception:
     df_mauzo_ripoti = pd.DataFrame()

    if not df_mauzo_ripoti.empty:
    # 1. Menu ya kuchagua kipindi
     aina_ya_ripoti = st.selectbox(
        "Chagua Kipindi cha Ripoti:",
        ["Ripoti ya Siku (Leo)", "Ripoti ya Wiki Hii", "Ripoti ya Mwezi Huu", "Ripoti ya Mwaka Huu"],
        key="ripoti_kipindi_real_box"
    )
    
    # Hakikisha Tarehe ipo kwenye format sahihi
     df_mauzo_ripoti['Date'] = pd.to_datetime(df_mauzo_ripoti['Date']).dt.date
     leo = dt.now().date()
    
    # 2. Logic ya kuchuja data ya mauzo kulingana na kipindi ulichochagua
     if aina_ya_ripoti == "Ripoti ya Siku (Leo)":
        df_rep = df_mauzo_ripoti[df_mauzo_ripoti['Date'] == leo]
        f_name = f"ripoti_ya_siku_{leo}.csv"
     elif aina_ya_ripoti == "Ripoti ya Wiki Hii":
         mwanzo_wa_wiki = leo - pd.Timedelta(days=6)
         df_rep = df_mauzo_ripoti[(df_mauzo_ripoti['Date'] >= mwanzo_wa_wiki) & (df_mauzo_ripoti['Date'] <= leo )]
         f_name = f"ripoti_ya_wiki_{leo}.csv"
     elif aina_ya_ripoti == "Ripoti ya Mwezi Huu":
         df_rep = df_mauzo_ripoti[pd.to_datetime(df_mauzo_ripoti['Date']).dt.month == leo.month]
         f_name = f"ripoti_ya_mwezi_{leo.month}_{leo.year}.csv"
     else:
        df_rep = df_mauzo_ripoti[pd.to_datetime(df_mauzo_ripoti['Date']).dt.year == leo.year]
        f_name = f"ripoti_ya_mwaka_{leo.year}.csv"

    # 3. Kuanza Kupiga Hesabu za Mauzo halisi
     if not df_rep.empty:
        # A. Jumla ya Mauzo na Profit kutokea kwenye faili la mauzo
        jumla_mauzo = df_rep['Total'].sum()
        jumla_profit = df_rep['Profit'].sum()
        
        # B. Idadi ya bidhaa zote zilizouzika (Sum ya Qty)
        bidhaa_zilizouzwa = df_rep['Qty'].sum()
        
        # C. Bidhaa iliyouzika kwa asilimia kubwa (Inasoma column ya 'Category')
        #top_bidhaa_df = df_rep.groupby('Category')['Qty'].sum().reset_index()
        # Badilisha mstari huu kwenye kodi yako
        top_bidhaa_df = df_rep.groupby('Category').agg({'Qty': 'sum', 'Total': 'sum'}).reset_index()
        top_bidhaa_df['Asilimia'] = (top_bidhaa_df['Qty'] / bidhaa_zilizouzwa) * 100
        top_bidhaa_safi = top_bidhaa_df.sort_values(by='Qty', ascending=False).iloc[0]
        
        top_jina = top_bidhaa_safi['Category']
        top_asilimia = top_bidhaa_safi['Asilimia']

        # D. Soma faili la stoo kujua vitu vilivyobaki stoo kwa ujumla wake
        try:
            df_stoo_real = stoo_global.copy()
            vitu_vya_stoo = df_stoo_real['Total_Stock'].sum()
        except Exception:
            vitu_vya_stoo = 0

        # 4. KUONYESHA MATOKEO KWENYE DASHBOARD (Metrics Cards)
        c_rep1, c_rep2, c_rep3 = st.columns(3)
        with c_rep1:
            st.metric(label="💰 Jumla ya Mauzo", value=f"{jumla_mauzo:,.0f} TZS")
            st.metric(label="📦 Jumla ya Vitu Vilivyouzwa", value=f"{bidhaa_zilizouzwa:,} Pcs")
            
        with c_rep2:
            st.metric(label="📈 Faida Halisi (Profit)", value=f"{jumla_profit:,.0f} TZS")
            st.metric(label="🏬 Vitu Vilivyobaki Stoo kwa Ujumla", value=f"{vitu_vya_stoo:,} Pcs")
            
        with c_rep3:
            st.metric(label="🥇 Bidhaa Inayoongoza", value=f"{top_jina}")
            st.metric(label="📊 Asilimia ya Soko", value=f"{top_asilimia:.1f}%")

        st.info(f"Kipindi hiki, bidhaa kutoka kundi la **{top_jina}** ndizo zilizouzika kwa wingi zaidi, zikichukua **{top_asilimia:.1f}%** ya bidhaa zote zilizotoka stoo.")
        
          # Anzisha class ya FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

  
# 1. Maandalizi ya Data (Panga kuanzia nyingi kwenda ndogo)
        top_bidhaa_df = top_bidhaa_df.sort_values(by='Qty', ascending=False)

        pdf = FPDF()
        pdf.add_page()

# 2. Kichwa cha Habari (Header) - Times New Roman
        pdf.set_font("Times", "B", 18)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(200, 10, txt="KWA SHIRIMA STORE - DODOMA", ln=True, align="C")

        pdf.set_font("Times", "B", 12)
        pdf.set_text_color(0,0, 0)
        pdf.cell(200, 8, txt=f"Ripoti ya Biashara: {aina_ya_ripoti}", ln=True, align="C")
        pdf.cell(200, 8, txt=f"Tarehe ya Ripoti: {leo.strftime('%Y-%m-%d')}", ln=True, align="C")
        pdf.ln(10)

# 3. Jumla ya Mauzo (Maandishi ya kawaida)
        # --- JUMLA YA MAUZO NA FAIDA (Kushoto) ---
        # --- JUMLA YA MAUZO NA FAIDA (Bila Bold na namba chini) ---
        pdf.ln(5)
        pdf.set_font("Times", "", 12) # Hakuna "B" hapa ili maandishi yasiwe bold
        pdf.set_text_color(0, 0, 0)

# Jumla ya Mauzo
        pdf.cell(200, 7, txt="Jumla ya Mauzo:", ln=True, align="L")
        pdf.set_font("Times", "B", 14) # Bold kwa namba tu kama unataka, au ondoa "B" kama unataka iwe ya kawaida
        pdf.cell(200, 7, txt=f"{jumla_mauzo:,.0f} TZS", ln=True, align="L")

        pdf.ln(3) # Nafasi kidogo

# Faida ya Siku
        pdf.set_font("Times", "", 12) # Maandishi ya kawaida
        pdf.cell(200, 7, txt="Jumla ya Faida :", ln=True, align="L")
        pdf.set_font("Times", "B", 14) # Bold kwa namba
        pdf.cell(200, 7, txt=f"{jumla_profit:,.0f} TZS", ln=True, align="L")

        pdf.ln(5)
        pdf.ln(10)

# 4. Bidhaa 3 Zinazoongoza
        pdf.set_font("Times", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(200, 8, txt="Top 3: Bidhaa Zinazouza Zaidi", ln=True)
        pdf.set_font("Times", "", 11)
        pdf.set_text_color(0, 0, 0)
        for i, row in top_bidhaa_df.head(3).iterrows():
         pdf.cell(200, 6, txt=f"- {row['Category']}: {row['Asilimia']:.1f}% ya soko", ln=True)
        pdf.ln(5)

     

        top3_data = top_bidhaa_df.nlargest(3, 'Qty')
        # 1. Tumia asilimia zile zile ulizotengeneza kwenye dataframe
        labels = top3_data['Category']
        sizes = top3_data['Asilimia'] # Hizi ndizo asilimia za soko zima

# 2. Chora Pie Chart na utumie 'pctdistance' kuonyesha asilimia unazozitaka
        plt.figure(figsize=(6, 6))

# Tunatumia 'autopct' kuonyesha asilimia zenyewe
# Ili zionekane kama zilivyo kwenye list, tunatumia format ndefu kidogo
        plt.pie(sizes, labels=labels, autopct=lambda p: f'{p:.1f}%', textprops={'fontsize': 12})

# 3. Kurekebisha Title (Kuongeza size na Bold)
        plt.title("Top 3 Bidhaa Zinazouza Zaidi", fontsize=16, fontweight='bold')

# Hifadhi na uweke kwenye PDF kama kawaida
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png')
        img_buf.seek(0)
        pdf.image(img_buf, x=65, w=80)
        plt.close()

       
# 6. Mchanganuo wa Kina (Table)
        # --- MCHANGANUO WA MAUZO (Table) ---
        pdf.set_font("Times", "B", 12)
        pdf.set_text_color(0, 0, 0) # Maandishi meusi
        pdf.cell(200, 10, txt="Mchanganuo wa Kina kwa Category", ln=True, align="C")

# Headers za Table
        pdf.set_font("Times", "B", 10)
        pdf.set_fill_color(200, 200, 200) # Kijivu kidogo kwa header
        pdf.set_text_color(0, 0, 0) # Maandishi meusi
        pdf.cell(50, 8, "Category", 1, 0, 'C', True)
        pdf.cell(40, 8, "Idadi", 1, 0, 'C', True)
        pdf.cell(50, 8, "Thamani (TZS)", 1, 0, 'C', True)
        pdf.cell(50, 8, "% ya Soko", 1, 1, 'C', True)

# Data za Table (Loop hii itapanga kila bidhaa kwenye mstari wake)
        pdf.set_font("Times", "", 10)
        # Ndani ya loop ya PDF table
        for idx, row in top_bidhaa_df.iterrows():
            pdf.cell(50, 8, str(row['Category']), 1)
            pdf.cell(40, 8, f"{int(row['Qty']):,}", 1, 0, 'C')
    # Hapa tunatumia 'Total' badala ya 'Mauzo'
            pdf.cell(50, 8, f"{float(row['Total']):,.0f}", 1, 0, 'C') 
            pdf.cell(50, 8, f"{float(row['Asilimia']):.1f}%", 1, 1, 'C')
        pdf.ln(5)

# --- FOOTER (Hii ikae hapa baada ya table) ---
        pdf.set_font("Times", "I", 8)
        pdf.cell(0, 10, txt="This software created by Frank Shirima ", ln=True, align="C")
        pdf.cell(0, 10, txt=" @all rights reserved", ln=True, align="C")

      
            
         # 4. Kutoa PDF kama byte string kwa ajili ya Streamlit Download Button
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            pdf_data = pdf_output(dest='S') # fpdf ya zamani inatoa string
        else:
            pdf_data = bytes(pdf_output)# fpdf2 mpya inatoa bytes moja kwa moja
            
        # 5. Kitufe cha Streamlit
        st.download_button(
            label=f"📥 Pakua {aina_ya_ripoti} (PDF)",
            data=pdf_data,
            file_name=f_name.replace('.csv', '.pdf'),
            mime='application/pdf',
            key='download_fpdf_report_btn'
        )
        
        
       
             



 except FileNotFoundError:
    st.error("Tafadhali kwanza run ile script ya kutengeneza CSV!")
