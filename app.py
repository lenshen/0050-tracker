import os
import yfinance as yf
import twstock
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 讀取 .env 檔案中的 LINE 金鑰
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    # 取得 LINE 傳遞過來的加密簽章與內容
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip()
    
    custom_dict = {
        "發哥": "2454.TW",
        "航海王": "2603.TW",
        "0050": "0050.TW"
    }
    
    stock_symbol = None
    found_name = user_input 

    # 🔍 第一關：查黑話字典
    if user_input in custom_dict:
        stock_symbol = custom_dict[user_input]
        
    # 🔍 第二關：純數字代號
    elif user_input.isdigit():
        if user_input in twstock.codes:
            market = twstock.codes[user_input].market
            suffix = ".TWO" if market == "上櫃" else ".TW"
            stock_symbol = f"{user_input}{suffix}"
            found_name = twstock.codes[user_input].name
        else:
            stock_symbol = f"{user_input}.TW"
            
    # 🔍 第三關：模糊搜尋
    else:
        matched_stocks = []
        for code, data in twstock.codes.items():
            # 🚀 關鍵修復 1：只抓「股票」與「ETF」，徹底排除幾千檔「權證」
            if user_input in data.name and data.type in ['股票', 'ETF']:
                matched_stocks.append(data)
                
        if len(matched_stocks) == 1:
            data = matched_stocks[0]
            suffix = ".TWO" if data.market == "上櫃" else ".TW"
            stock_symbol = f"{data.code}{suffix}"
            found_name = data.name
            
        elif len(matched_stocks) > 1:
            reply_lines = [f"🔍 找到多檔標的，請輸入代號："]
            for data in matched_stocks[:10]:
                reply_lines.append(f"• {data.name} ({data.code})")
            
            if len(matched_stocks) > 10:
                reply_lines.append(f"...等共 {len(matched_stocks)} 檔")
                
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="\n".join(reply_lines))
            )
            return

        else:
            stock_symbol = user_input.upper()

    # ====== 🚀 關鍵修復 2：最穩定的歷史抓價法 ======
    try:
        stock = yf.Ticker(stock_symbol)
        hist = stock.history(period="1d") # 抓取最近一天的交易紀錄
        
        if not hist.empty:
            current_price = hist['Close'].iloc[-1] # 取最新收盤價/現價
            reply_text = f"📈 【{found_name} ({stock_symbol})】 最新報價：{current_price:.2f}"
        else:
            reply_text = f"無法取得 '{user_input}' 的報價 😢\n請確認代號是否正確 (若是美股請輸入代號)。"
            
    except Exception as e:
        print(f"Error fetching {stock_symbol}: {e}")
        reply_text = f"查詢 '{user_input}' 時發生錯誤 😢"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )
if __name__ == "__main__":
    # 在 Docker 內運行，必須對外綁定 0.0.0.0
    app.run(host='0.0.0.0', port=5000)
