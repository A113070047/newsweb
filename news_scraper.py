import psycopg2
import requests
from bs4 import BeautifulSoup
import json
import time
import os
from newspaper import Article
import urllib3
from datetime import datetime # 【新增】用來顯示現在時間

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def auto_categorize(title, text):
    """
    進階版：利用「計分機制」讓分類更精準，並將預設改為「其他」
    """
    # 定義更豐富的關鍵字字典
    categories = {
        "政治": ["選舉", "立法院", "法案", "總統", "政治", "執政", "政黨", "官員", "外交", "內政"],
        "科技": ["AI", "蘋果", "台積電", "半導體", "科技", "晶片", "人工智慧", "微軟", "電動車", "伺服器"],
        "氣象": ["颱風", "地震", "降雨", "氣溫", "天氣", "大雨", "特報", "氣象署", "寒流"],
        "財經": ["股市", "經濟", "通膨", "央行", "台股", "升息", "投資", "美股", "GDP", "匯率"],
        "體育": ["棒球", "奧運", "籃球", "賽事", "體育", "羽球", "網球", "大聯盟", "中職", "冠軍"]
    }

    scores = {cat: 0 for cat in categories}
    
    # 1. 檢查標題：如果關鍵字在標題出現，權重極高 (加 3 分)
    for cat, keywords in categories.items():
        for keyword in keywords:
            if keyword in title:
                scores[cat] += 3
    
    # 2. 檢查內文：計算關鍵字在內文出現的總次數 (每次加 1 分)
    for cat, keywords in categories.items():
        for keyword in keywords:
            scores[cat] += text.count(keyword)
            
    # 3. 找出最高分的分類
    best_category = max(scores, key=scores.get)
    
    # 4. 如果最高分還是 0 (代表完全沒中)，就歸類為「其他」
    if scores[best_category] == 0:
        return "其他"
        
    return best_category


def extract_pts_article_data(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        article = Article(url, language='zh')
        article.download(input_html=response.text)
        article.parse()
        
        text = article.text.strip()
        if not text: text = "[找不到內文]"
            
        pub_date = article.publish_date
        date_str = str(pub_date)[:19] if pub_date else "未知時間"
        
        return {
            "title": article.title,
            "text": text,
            "image_url": article.top_image,
            "date": date_str,
            "url": url
        }
    except Exception as e:
        return None

def scrape_pts_news():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 啟動自動爬蟲任務...")
    
    # 1. 先讀取已經存下來的舊新聞，避免重複抓取
    existing_news = []
    existing_urls = set()
        
    if os.path.exists("news_data.json"):
        try:
            with open("news_data.json", "r", encoding="utf-8") as file:
                existing_news = json.load(file)
                # 把已經抓過的網址記錄下來
                for item in existing_news:
                    existing_urls.add(item["link"])
        except Exception:
            pass

    base_url = "https://news.pts.org.tw"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    response = requests.get(base_url, headers=headers, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    article_links = []
    
    for a_tag in soup.find_all("a"):
        href = a_tag.get("href")
        if href and "/article/" in href:
            full_url = href if href.startswith("http") else base_url + href
            if full_url not in article_links:
                article_links.append(full_url)
                
    # 2. 修改這裡！改成掃描前 30 篇 (或你想改成全部也可以)
    print(f"首頁掃描到 {len(article_links)} 篇新聞，準備過濾...")
    new_articles_count = 0
    
    for link in article_links:
        # 【核心邏輯】如果這篇新聞的網址已經在舊資料庫裡，就直接跳過！
        if link in existing_urls:
            continue
            
        print(f"發現新新聞，正在抓取: {link}")
        data = extract_pts_article_data(link)
        
        if data and data["title"]:
            # 將新新聞「插隊」放到清單的最前面
            existing_news.insert(0, {
                "title": data["title"],
                "link": data["url"],
                "date": data["date"],
                "image_url": data["image_url"],
                "content_preview": data["text"][:150] + "..." if len(data["text"]) > 150 else data["text"],
                # 【新增這行】呼叫自動分類函式，將標籤存下來
                "category": auto_categorize(data["title"], data["text"])
            })
            new_articles_count += 1
            
        time.sleep(2) # 禮貌性暫停

    # 3. 只有當有抓到「新新聞」時，才重新存檔
    if new_articles_count > 0:
        print(f"=== 任務完成！這次新增了 {new_articles_count} 篇新聞 ===")
        with open("news_data.json", "w", encoding="utf-8") as file:
            json.dump(existing_news, file, ensure_ascii=False, indent=4)
    else:
        print("=== 檢查完畢，目前沒有新的新聞 ===")

if __name__ == "__main__":
    # 程式一啟動，先強制手動執行一次
    scrape_pts_news()

    print("\n⏳ 自動排程已啟動！")
    print("請不要關閉這個終端機視窗。程式會在背景每 60 分鐘自動幫你巡邏並抓取新新聞...")

    
# 從環境變數安全地讀取密碼
    db_url = os.environ.get("DATABASE_URL")
    
    if db_url:
        try:
            # 連線到雲端 PostgreSQL
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()

            # 建立資料表 (如果還沒有建過的話)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pts_news (
                    id SERIAL PRIMARY KEY,
                    title TEXT UNIQUE,
                    link TEXT,
                    date TEXT,
                    image_url TEXT,
                    content_preview TEXT,
                    category TEXT
                )
            """)

            # 將剛抓到的新聞寫入資料庫
            for news in existing_news:
                # 這裡使用了 ON CONFLICT，遇到重複的標題就會自動跳過，非常聰明！
                cursor.execute("""
                    INSERT INTO pts_news (title, link, date, image_url, content_preview, category)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (title) DO NOTHING
                """, (news["title"], news["link"], news["date"], news["image_url"], news["content_preview"], news["category"]))

            # 確認存檔並關閉連線
            conn.commit()
            cursor.close()
            conn.close()
            print("成功將新聞同步至 PostgreSQL！")

        except Exception as e:
            print(f"資料庫寫入失敗: {e}")
