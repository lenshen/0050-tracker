import os
import datetime
import yfinance as yf
import pandas as pd
import requests

def get_0050_price():
    try:
        # 使用 yfinance 抓取 0050.TW 最新數據
        ticker = yf.Ticker("0050.TW")
        df = ticker.history(period="1d")
        
        if df.empty:
            print("⚠️ 無法取得今日數據，可能當日非交易日。")
            return None, None
            
        # 獲取該筆資料的實際交易日期與收盤價
        trading_date = df.index[-1].strftime('%Y-%m-%d')
        close_price = float(df['Close'].iloc[-1])
        return round(close_price, 2), trading_date
    except Exception as e:
        print(f"❌ 抓取股價失敗: {e}")
        return None, None

def update_excel(date_str, price):
    file_name = '0050_history.xlsx'
    new_data = pd.DataFrame({'日期': [date_str], '收盤價': [price]})
    
    if os.path.exists(file_name):
        try:
            df_old = pd.read_excel(file_name)
            # 如果日期已存在，則更新價格，避免重複寫入
            if date_str in df_old['日期'].astype(str).values:
                print(f"ℹ️ 日期 {date_str} 已存在，更新其收盤價。")
                df_old.loc[df_old['日期'].astype(str) == date_str, '收盤價'] = price
                df_all = df_old
            else:
                df_all = pd.concat([df_old, new_data], ignore_index=True)
        except Exception as e:
            print(f"⚠️ 讀取舊 Excel 失敗，將重新建立新檔: {e}")
            df_all = new_data
    else:
        df_all = new_data
        
    df_all.to_excel(file_name, index=False)
    print(f"💾 Excel 檔案已更新: {date_str} -> {price} 元")

def send_line_message(date_str, price):
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.environ.get('LINE_USER_ID')
    
    if not token or not user_id:
        print("⚠️ 未設定 LINE Token 或 User ID，跳過發送訊息。")
        return
        
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    message_text = f"📊 【0050 每日收盤回報】\n📅 交易日期：{date_str}\n💰 收盤價：{price} 元\n\n歷史紀錄已成功同步至 Excel 檔案中！"
    
    payload = {
        'to': user_id,
        'messages': [
            {
                'type': 'text',
                'text': message_text
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("🚀 LINE 訊息發送成功！")
        else:
            print(f"❌ LINE 發送失敗，狀態碼：{response.status_code}, 回應：{response.text}")
    except Exception as e:
        print(f"❌ 發送 LINE 訊息時發生錯誤: {e}")

if __name__ == '__main__':
    price, date_str = get_0050_price()
    if price is not None:
        update_excel(date_str, price)
        send_line_message(date_str, price)
    else:
        print("⏭️ 未能取得有效收盤價，終止後續流程。")
