import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.subplots as sp
import plotly.graph_objects as go

# ตั้งค่าหน้าเว็บ Streamlit
st.set_page_config(
    page_title="Global Smart Money & SET100 Sector Flow Analyzer",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 Global Smart Money & SET100 Sector Flow Analyzer (THB Currency)")
st.markdown("เรดาร์วิเคราะห์กระแสเงินสดและงบการเงินเชิงลึก แปลงทุกค่าเป็น **บาทไทย (THB)** เจาะลึกหุ้นเล่นรอบ นวัตกรรม สิทธิบัตรโลก และกลุ่มอุตสาหกรรม SET100")

# ปุ่มซ่อน/แสดง Sidebar
show_settings = st.sidebar.checkbox("แสดงแผงตั้งค่าเรดาร์", value=True)
if not show_settings:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True
    )

st.sidebar.header("⚙️ ตั้งค่าเรดาร์ลงทุน & SET100")
time_period = st.sidebar.selectbox("เลือกช่วงเวลาวิเคราะห์กราฟ", ["6mo", "1y", "2y"], index=1)
ma_window = st.sidebar.slider("ค่าเฉลี่ยเคลื่อนที่ (Moving Average Window)", min_value=3, max_value=20, value=7)

# เลือกกลุ่ม SET100 Sector ที่ต้องการส่อง
set100_sectors = st.sidebar.multiselect(
    "เลือกกลุ่มอุตสาหกรรม SET100 เพื่อเจาะลึก",
    ["SET100 - Banking (ธนาคาร)", "SET100 - Energy (พลังงาน)", "SET100 - Commerce (ค้าปลีก)", "SET100 - ICT (สื่อสาร)", "SET100 - Food (อาหาร)"],
    default=["SET100 - Banking (ธนาคาร)", "SET100 - Energy (พลังงาน)"]
)

with st.spinner("กำลังดึงข้อมูลเรดาร์ตลาดโลกและแปลงค่าเป็นเงินบาท (THB) พร้อมเจาะลึก SET100... รอแป๊บนะเพื่อน!"):
    
    # ดึงค่าเงิน USD/THB ล่าสุดเพื่อแปลงค่าสินทรัพย์ต่างประเทศให้เป็นบาท
    try:
        df_usdhb = yf.download('USDTHB=X', period='5d', interval='1d', progress=False)
        if isinstance(df_usdhb.columns, pd.MultiIndex):
            df_usdhb.columns = df_usdhb.columns.droplevel(1)
        current_usdhb = float(df_usdhb['Close'].iloc[-1])
    except:
        current_usdhb = 35.0 # เรทสำรองกรณีดึงไม่สำเร็จ

    # สินทรัพย์ต่างประเทศ (แปลงเป็น THB โดยคูณเรท USDTHB)
    global_assets = {
        'Tech (XLK)': 'XLK',
        'Healthcare (XLV)': 'XLV',
        'Energy (XLE)': 'XLE',
        'Financials (XLF)': 'XLF',
        'Comm Services (XLC)': 'XLC',
        'China (FXI)': 'FXI',
        'Japan (EWJ)': 'EWJ',
        'Korea (EWY)': 'EWY',
        'Gold (GLD)': 'GLD'
    }

    data_thb_vol = pd.DataFrame()

    # 1. ดึงข้อมูลหุ้นต่างประเทศและแปลงเป็น THB Dollar Volume
    for name, ticker in global_assets.items():
        try:
            df = yf.download(ticker, period=time_period, interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            if 'Close' in df.columns and 'Volume' in df.columns:
                # คำนวณ Dollar Volume เป็น USD แล้วแปลงเป็น THB
                calc_vol_thb = df['Close'] * df['Volume'] * current_usdhb
                if not calc_vol_thb.empty and calc_vol_thb.sum() > 0:
                    data_thb_vol[name] = calc_vol_thb
        except Exception as e:
            pass

    # 2. ดึงข้อมูลตัวแทนกลุ่ม SET100 Sectors (หน่วยเป็นบาทอยู่แล้ว)
    set100_tickers_map = {
        "SET100 - Banking (ธนาคาร)": "KBANK.BK",
        "SET100 - Energy (พลังงาน)": "PTT.BK",
        "SET100 - Commerce (ค้าปลีก)": "CPALL.BK",
        "SET100 - ICT (สื่อสาร)": "ADVANC.BK",
        "SET100 - Food (อาหาร)": "CPF.BK"
    }

    for sector_name in set100_sectors:
        t = set100_tickers_map.get(sector_name)
        if t:
            try:
                df_s = yf.download(t, period=time_period, interval="1d", progress=False)
                if isinstance(df_s.columns, pd.MultiIndex):
                    df_s.columns = df_s.columns.droplevel(1)
                if 'Close' in df_s.columns and 'Volume' in df_s.columns:
                    s_vol = df_s['Close'] * df_s['Volume']
                    if not s_vol.empty:
                        data_thb_vol[sector_name] = s_vol
            except Exception as e:
                pass

    if not data_thb_vol.empty:
        data_thb_vol = data_thb_vol.ffill().dropna(how='all')
        
        # คำนวณ Macro Total Market Volume (ในหน่วย THB) เฉพาะหุ้นโลก
        macro_cols = [c for c in data_thb_vol.columns if not c.startswith("SET100")]
        if macro_cols:
            data_thb_vol['Global Total Liquidity (THB)'] = data_thb_vol[macro_cols].sum(axis=1)
            
        vol_smooth = data_thb_vol.rolling(window=ma_window, min_periods=1).mean()

        # สร้าง Subplots 2 ช่อง
        fig = sp.make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.35, 0.65],
            subplot_titles=(
                "Global Macro Liquidity & Safe Haven (THB Value)", 
                "Global Sectors, Asian Markets & SET100 Sectors (THB Value)"
            )
        )

        # ชุดสีเด่นชัด
        colors = {
            'Tech (XLK)': 'rgb(0, 255, 255)',         # ฟ้าสว่าง
            'Healthcare (XLV)': 'rgb(0, 255, 128)',   # เขียวมิ้นท์
            'Energy (XLE)': 'rgb(255, 128, 0)',       # ส้ม
            'Financials (XLF)': 'rgb(192, 128, 255)', # ม่วงอ่อน
            'Comm Services (XLC)': 'rgb(255, 0, 128)',# ชมพู
            'China (FXI)': 'rgb(255, 50, 50)',       # แดง
            'Japan (EWJ)': 'rgb(255, 255, 0)',       # เหลือง
            'Korea (EWY)': 'rgb(128, 128, 255)',     # น้ำเงิน
            'Gold (GLD)': 'rgb(255, 215, 0)',         # ทองคำ
            'Global Total Liquidity (THB)': 'rgb(255, 255, 255)', # ขาว
            'SET100 - Banking (ธนาคาร)': 'rgb(0, 200, 100)',
            'SET100 - Energy (พลังงาน)': 'rgb(255, 100, 100)',
            'SET100 - Commerce (ค้าปลีก)': 'rgb(100, 200, 255)',
            'SET100 - ICT (สื่อสาร)': 'rgb(255, 200, 0)',
            'SET100 - Food (อาหาร)': 'rgb(200, 100, 255)'
        }

        for name in vol_smooth.columns:
            if name in ['Global Total Liquidity (THB)', 'Gold (GLD)']:
                r = 1
                line_width = 3.5
            else:
                r = 2
                line_width = 2.5

            fig.add_trace(
                go.Scatter(
                    x=vol_smooth.index,
                    y=vol_smooth[name],
                    mode='lines',
                    name=name,
                    line=dict(width=line_width, color=colors.get(name, 'rgb(200,200,200)')),
                    hovertemplate=(
                        f"<b>{name}</b><br>"
                        "Date: %{x}<br>"
                        "Volume (THB): ฿%{y:,.0f}<br>"
                        "<extra></extra>"
                    )
                ),
                row=r, col=1
            )

        fig.update_layout(
            template="plotly_dark",
            hovermode="x unified",
            legend=dict(x=1.02, y=0.95, bgcolor="rgba(0,0,0,0.5)", font=dict(size=10)),
            margin=dict(l=50, r=180, t=80, b=50),
            height=750,
            hoverlabel=dict(namelength=-1)
        )

        fig.update_yaxes(title_text="Macro Liquidity (THB)", row=1, col=1)
        fig.update_yaxes(title_text="Sectors & SET100 (THB)", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)
        st.success("เรดาร์แปลงค่าเป็นบาท (THB) และแยก Sector SET100 สำเร็จเรียบร้อยเพื่อน ลุยส่องฟันด์โฟลว์กันเลย!")
    else:
        st.error("⚠️ ไม่สามารถดึงข้อมูลได้ในขณะนี้ ลองตรวจสอบการเชื่อมต่ออินเทอร์เน็ตแล้วรีเฟรชใหม่อีกครั้งเพื่อน!")
