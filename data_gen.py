import pandas as pd
import random
from datetime import datetime, timedelta

# 1. Pakia bei za kununulia kutoka stoo_data.csv
try:
    df_stoo = pd.read_csv('stoo_data.csv')
    bei_kununua_dict = dict(zip(df_stoo['Category'], df_stoo['Buying_Price']))
    bidhaa_zote = list(bei_kununua_dict.keys())
except FileNotFoundError:
    print("Error: Hakikisha stoo_data.csv ipo kwenye folder hili.")
    exit()

data_mipya = []
mwanzo = datetime(2026, 2, 1)
leo = datetime.now()

current_date = mwanzo
while current_date <= leo:
    for _ in range(random.randint(1, 4)):
        jina = random.choice(bidhaa_zote)
        idadi = random.randint(1, 10)
        bei_kununua = bei_kununua_dict[jina]
        
        # 2. Tengeneza Wastani wa Bei ya Kuuza (Unit_Price)
        # Tunauza kwa faida ya 20% mpaka 50%
        unit_price = int(bei_kununua * random.uniform(1.2, 1.5))
        
        # 3. Piga hesabu ya Jumla na Faida
        total_sales = unit_price * idadi
        total_profit = total_sales - (bei_kununua * idadi)
        
        data_mipya.append({
            "Date": current_date.strftime("%Y-%m-%d"),
            "Category": jina,
            "Quantity": idadi,
            "Unit_Price": unit_price, # Wastani unakaa hapa
            "Total": total_sales,      # Jumla inafuata
            "Profit": total_profit     # Profit mwisho
        })
    current_date += timedelta(days=1)

# 4. Hifadhi faili
df_mpya = pd.DataFrame(data_mipya)
df_mpya.to_csv('mauzo_data.csv', index=False)

print("Safii! mauzo_data.csv imetengenezwa kwa mpangilio ulioitaka.")