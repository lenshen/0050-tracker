import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定你要追蹤的 11 檔標的清單
TARGET_STOCKS = {
    "聯電(2303)": "2303.TW",
    "友訊(2332)": "2332.TW",
    "佳世達(2352)": "2352.TW",
    "開發金(2883)": "2883.TW",
    "玉山金(2884)": "2884.TW",
    "兆豐金(2886)": "2886.TW",
    "聯合再生(3576)": "3576.TW",
    "台灣50(0050)": "0050.TW",
    "ESG永續(00850)": "00850.TW",
    "半導體收益(00927)": "00927.TW",
    "凱基TOP50(009816)": "009816.TW"
}

file_name = 'stocks_history.xlsx'
GITHUB_USERNAME = 'lenshen'  # 你的 GitHub 帳號

def get_stock_prices():
    results = []
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    for name, ticker in TARGET_STOCKS.items():
        try:
            stock = yf.Ticker(ticker)
            
            # 1. 取得近2日數據以計算今日漲跌幅
            hist_2d = stock.history(period="2d")
            if hist_2d.empty:
                print(f"⚠️ 無法抓取 {name} 的股價資料")
                continue
                
            # 計算今日收盤與昨日收盤
            if len(hist_2d) >= 2:
                prev_close = float(hist_2d['Close'].iloc[-2])
                current_price = round(float(hist_2d['Close'].iloc[-1]), 2)
                change_price = round(current_price - prev_close, 2)
                change_percent = round((change_price / prev_close) * 100, 2)
            else:
                current_price = round(float(hist_2d['Close'].iloc[-1]), 2)
                change_price = 0.0
                change_percent = 0.0
            
            # 2. 計算近一年報酬率
            hist_1y = stock.history(period="1y")
            if not hist_1y.empty and len(hist_1y) > 20:
                price_1y_ago = float(hist_1y['Close'].iloc[0])
                annual_return = ((current_price / price_1y_ago) - 1) * 100
                annual_return_str = f"{annual_return:.2f}%"
            else:
                annual_return_str = "上市未滿一年"
                
            # 3. 計算真實殖利率 (過去 365 天配息總和 / 目前股價)
            divs = stock.dividends
            if not divs.empty:
                one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
                last_year_divs = divs[divs.index >= one_year_ago]
                total_div = last_year_divs.sum()
                yield_str = f"{(total_div / current_price) * 100:.2f}%" if total_div > 0 else "0.00%"
            else:
                yield_str = "0.00%"
                
            # 4. 取得本益比 (Trailing P/E)
            pe_ratio = stock.info.get('trailingPE')
            pe_str = f"{pe_ratio:.2f}" if pe_ratio else "N/A"
            
            # 將整理好的單檔數據存入列表
            results.append({
                "日期": date_str, 
                "股票名稱": name, 
                "收盤價": current_price,
                "漲跌價": change_price,
                "漲跌幅": f"{change_percent}%",
                "年報酬率": annual_return_str,
                "殖利率": yield_str,
                "本益比": pe_str
            })
            print(f"✅ 成功抓取: {name} (今日漲跌: {change_percent}%)")
            
        except Exception as e:
            print(f"❌ 抓取 {name} 失敗: {e}")
            
    return date_str, results

def update_excel(results):
    if not results:
        return
        
    df_today = pd.DataFrame(results)
    date_str = results[0]['日期']
    
    # 讀取或建立歷史紀錄總表
    if os.path.exists(file_name):
        try:
            # 讀取舊的歷史紀錄分頁
            df_history_old = pd.read_excel(file_name, sheet_name="歷史紀錄")
            # 移除舊紀錄中今天的資料，避免重複測試時重複寫入
            df_history_old = df_history_old[df_history_old['日期'].astype(str) != date_str]
            df_history_all = pd.concat([df_history_old, df_today], ignore_index=True)
        except Exception as e:
            print(f"⚠️ 讀取歷史紀錄分頁失敗，建立新歷史紀錄: {e}")
            df_history_all = df_today
    else:
        df_history_all = df_today

    # 使用 ExcelWriter 同時寫入多個分頁
    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        df_today.to_excel(writer, sheet_name="今日總覽", index=False)
        df_history_all.to_excel(writer, sheet_name="歷史紀錄", index=False)
        
    print(f"📝 Excel 檔案多分頁更新完成！(已寫入 今日總覽 與 歷史紀錄)")

def send_line_message(date_str, results):
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not token:
        print("⚠️ 未設定 LINE Token，跳過發送訊息。")
        return

    excel_url = f"https://github.com/{GITHUB_USERNAME}/0050-tracker/raw/main/{file_name}"
    
    # 組合給客戶的進階文字訊息版面 (著重在收盤價與今日漲跌幅)
    message_lines = [f"📊 【每日台股收盤與精選指標】", f"📅 日期: {date_str}", ""]
    
    for item in results:
        # 根據漲跌數值給予視覺符號
        change_val = float(item['漲跌價'])
        if change_val > 0:
            status_sign = f"▲ +{item['漲跌價']} ({item['漲跌幅']})"
        elif change_val < 0:
            status_sign = f"▼ {item['漲跌價']} ({item['漲跌幅']})"
        else:
            status_sign = f"— 0.00 (0.00%)"
            
        message_lines.append(f"🔹 {item['股票名稱']}")
        message_lines.append(f"  收盤價: {item['收盤價']} 元 ({status_sign})")
        message_lines.append(f"  殖利率: {item['殖利率']} | 本益比: {item['本益比']}")
        message_lines.append("") # 空行分隔
        
    message_lines.append(f"📂 點擊下載完整 Excel 歷史報表 (內含今日總覽與歷史紀錄分頁)：")
    message_lines.append(excel_url)
    
    message_text = "\n".join(message_lines)
    
    url = 'https://api.line.me/v2/bot/message/broadcast'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {"messages": [{"type": "text", "text": message_text}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("🚀 LINE 廣播訊息發送成功！")
        else:
            print(f"❌ LINE 發送失敗: {response.text}")
    except Exception as e:
        print(f"❌ 發送 LINE 發生錯誤: {e}")

if __name__ == "__main__":
    try:
        date_str, results = get_stock_prices()
        if results:
            update_excel(results)
            send_line_message(date_str, results)
        else:
            print("沒有取得任何股票資料。")
    except Exception as e:
        print(f"運行錯誤: {e}")
