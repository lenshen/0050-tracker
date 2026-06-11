import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定 Excel 檔名
file_name = '0050_history.xlsx'

def get_0050_price():
    # 抓取 0050 價格
    stock = yf.Ticker("0050.TW")
    df = stock.history(period="1d")
    
    if df.empty:
        raise Exception("無法抓取 0050 價格資料")
        
    # 確保抓取最後一筆交易日的日期與收盤價
    price = round(float(df['Close'].iloc[-1]), 2)
    date_str = df.index[-1].strftime('%Y-%m-%d')
    return date_str, price

def update_excel(date_str, price):
    new_data = pd.DataFrame({'日期': [date_str], '收盤價': [price]})
    
    if os.path.exists(file_name):
        try:
            df_old = pd.read_excel(file_name)
            if date_str in df_old['日期'].astype(str).values:
                print(f"日期 {date_str} 已存在，更新其收盤價。")
                df_old.loc[df_old['日期'].astype(str) == date_str, '收盤價'] = price
                df_all = df_old
            else:
                df_all = pd.concat([df_old, new_data], ignore_index=True)
        except Exception as e:
            print(f"⚠️ 讀取 Excel 失敗，將重新建立新檔: {e}")
            df_all = new_data
    else:
        df_all = new_data
        
    df_all.to_excel(file_name, index=False)
    print(f"📝 Excel 檔案已更新: {date_str} -> {price} 元")

def send_line_message(date_str, price):
    # 廣播只需要 Token，不需個人 ID，且金鑰安全鎖在 Secrets 中
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    
    if not token:
        print("⚠️ 未設定 LINE Token，跳過發送訊息。")
        return

    # 專屬於你的 Excel 直連下載網址 (使用 /raw/ 確保點擊後直接下載，不顯示 GitHub 網頁)
    excel_url = "https://github.com/lenshen/0050-tracker/raw/main/0050_history.xlsx"

    # LINE 訊息與文字內容，排版設計適合客戶閱讀
    message_text = (
        f"📊 【0050 每日收盤回報】\n"
        f"📅 日期: {date_str}\n"
        f"💰 收盤價: {price} 元\n\n"
        f"📂 最新歷史報表已同步，點擊下方連結直接下載：\n"
        f"{excel_url}"
    )
    
    # 這是 LINE Messaging API「廣播」的正確專屬網址
    url = 'https://api.line.me/v2/bot/message/broadcast'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("🚀 LINE 廣播訊息發送成功！")
        else:
            print(f"❌ LINE 發送失敗，狀態碼: {response.status_code}，回應: {response.text}")
    except Exception as e:
        print(f"❌ 發送 LINE 訊息時發生錯誤: {e}")

if __name__ == "__main__":
    try:
        date_str, price = get_0050_price()
        update_excel(date_str, price)
        send_line_message(date_str, price)
    except Exception as e:
        print(f"運行錯誤: {e}")
