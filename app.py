from flask import Flask, render_template
import json

app = Flask(__name__)

@app.route('/')
def home():
    # 1. 讀取你爬好的新聞 JSON 檔案
    try:
        with open("news_data.json", "r", encoding="utf-8") as file:
            news_list = json.load(file)
    except FileNotFoundError:
        # 如果還沒跑爬蟲，就先給一個空清單
        news_list = []
    
    # 2. 把資料傳給前端網頁範本 (index.html)，變數名稱叫做 news
    return render_template("index.html", news=news_list)

if __name__ == "__main__":
    # 啟動本地網頁伺服器，debug=True 代表改程式網頁會自動刷新
    app.run(debug=True, port=5000)