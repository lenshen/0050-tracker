import os
import yfinance as yf
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

# 1. 啟動防護：讀取 .env 隱藏檔裡面的密碼
load_dotenv()

app = Flask(__name__)

# 2. 設定 LINE 機器人金鑰 (自動從保險箱抓取，絕對安全)
line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# 3. 接收 LINE 總部傳來訊息的專屬通道 (Webhook)
@app.route("/callback", methods=['POST'])
def callback():
    # 驗證數位簽章 (駭客防護機制)
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 4. 處理客戶傳來的文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip() # 取得客戶輸入的文字，並去除多餘空白
    
    # 你專屬的股票資料庫 (支援輸入代號或名稱)
    stock_dict = {
        "2303": "2303.TW", "聯電": "2303.TW",
        "2332": "2332.TW", "友訊": "2332.TW",
        "2352": "2352.TW", "佳世達": "2352.TW",
        "2883": "2883.TW", "開發金": "2883.TW",
        "2884": "2884.TW", "玉山金": "2884.TW",
        "2886": "2886.TW", "兆豐金": "2886.TW",
        "3576": "3576.TW", "聯合再生": "3576.TW",
        "0050": "0050.TW", "台灣50": "0050.TW",
        "00850": "00850.TW", "ESG永續": "00850.TW",
        "00927": "00927.TW", "半導體收益": "00927.TW",
        "009816": "009816.TW", "凱基TOP50": "009816.TW",
        "2330": "2330.TW", "台積電": "2330.TW" # 測試用的熱門股
    }
    
    try:
        # 判斷客戶輸入的是不是我們支援的股票
        if user_text in stock_dict:
            ticker = stock_dict[user_text]
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            
            if not hist.empty:
                price = round(float(hist['Close'].iloc[-1]), 2)
                reply_msg = f"📊 {user_text} 最新收盤價：{price} 元"
            else:
                reply_msg = f"⚠️ 抱歉，目前無法取得 {user_text} 的資料。"
                
        else:
            reply_msg = "💡 請輸入股票代號或名稱，例如：0050 或 台積電\n\n(目前支援的標的包含：聯電、友訊、佳世達、開發金、玉山金、兆豐金、聯合再生、0050、00850、00927、009816)"
            
    except Exception as e:
        print(f"查詢錯誤: {e}") # 印出錯誤在終端機給你自己看
        reply_msg = "❌ 系統查詢時發生錯誤，請稍後再試。"

    # 回傳訊息給客戶
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_msg)
    )

if __name__ == "__main__":
    # 啟動伺服器，監聽 5000 port
    app.run(host='0.0.0.0', port=5000)
