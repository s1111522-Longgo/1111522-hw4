from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 儲存歷史對話
history = []

def generate_gemini_response(user_input):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": user_input}]}]
    }
    resp = requests.post(url, headers=headers, params={"key": GEMINI_API_KEY}, json=payload)
    try:
        resp.raise_for_status()
        data = resp.json()
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
        return reply
    except Exception:
        print("Gemini API 錯誤狀態：", resp.status_code)
        print("回應內容：", resp.text)
        return f"API 錯誤（{resp.status_code}），請稍後再試"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    reply_text = generate_gemini_response(user_text)

    # 儲存對話到歷史紀錄
    history.append({"user": user_text, "bot": reply_text})

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

# RESTful API：取得歷史對話
@app.route("/history", methods=['GET'])
def get_history():
    return jsonify(history)

# RESTful API：刪除歷史對話
@app.route("/history", methods=['DELETE'])
def delete_history():
    history.clear()
    return jsonify({"message": "歷史對話已清除"}), 200

if __name__ == "__main__":
    app.run(port=5000)
