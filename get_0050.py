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
    price = round(df['Close'].iloc[0], 2)
    date_str = datetime.now().strftime('%Y-%m-%d')
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
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    user_id = os.environ.get('LINE_USER_ID')
    
    if not token or not user_id:
        print("⚠️ 未設定 LINE Token 或 User ID，跳過發送訊息。")
        return

    # LINE 訊息與文字內容
    message_text = f"📊 0050 每日價格更新\n日期: {date_str}\n收盤價: {price} 元\n\n最新 Excel 紀錄已附在下方！"
    
    url = 'https://line.me'
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    # 這裡改成同時發送文字與 Excel 檔案（使用 LINE Messaging API 規格）
    # 注意：LINE 原生 PUSH 檔案需透過特殊的 media 接口，或改用 LINE Notify
    # 為了讓您最方便直接收到檔案，我們在有 Excel 檔案時改用 LINE Notify API 或直接透過 python request 傳送
    # 如果您使用的是 LINE Bot 官方帳號，以下為發送文字與 Excel 檔案的標準作法：
    
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print("🚀 LINE 文字訊息發送成功！")
    else:
        print(f"❌ LINE 發送失敗，狀態碼: {response.status_code}，回應: {response.text}")

    # 傳送 Excel 檔案部分
    if os.path.exists(file_name):
        # 由於 LINE 官方帳號 (Messaging API) 傳送檔案（file 類型）需要將檔案傳到公開網址上給 LINE 抓，
        # 如果您的 LINE 憑證其實是「LINE Notify」，我們可以直接用以下代碼直接上傳檔案：
        notify_url = 'https://line.me'
        notify_headers = {'Authorization': f'Bearer {token}'}
        
        try:
            with open(file_name, 'rb') as f:
                files = {'imageFile' if file_name.endswith(('.jpg', '.png')) else 'file': (file_name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                # 如果您的 Token 其實是 LINE Notify，這行會成功：
                r = requests.post(notify_url, headers=notify_headers, data={'message': '附上最新 Excel 檔案'}, files=files)
                if r.status_code == 200:
                    print("📁 Excel 檔案已成功透過 LINE 發送！")
                    return
        except:
            pass
            
        print("💡 提示：如果檔案沒有成功傳到 LINE，代表您的 Token 是官方帳號機器人。")
        print("您可以搭配剛才改好的 auto_0500.yml，直接在 GitHub 主畫面點選下載 Excel，也是一個很方便的辦法喔！")

if __name__ == "__main__":
    try:
        date_str, price = get_0050_price()
        update_excel(date_str, price)
        send_line_message(date_str, price)
    except Exception as e:
        print(f"運行錯誤: {e}")
