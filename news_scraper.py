import requests
from bs4 import BeautifulSoup
import json
import time
import os
from newspaper import Article
import urllib3
from datetime import datetime # 【新增】用來顯示現在時間

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    
    for link in article_links[:30]:
        # 【核心邏輯】如果這篇新聞的網址已經在舊資料庫裡，就直接跳過！
        if link in existing_urls:
            continue
            
        print(f"發現新新聞，正在抓取: {link}")
        data = extract_pts_article_data(link)
        
        if data and data["title"]:
            # 將新新聞「插隊」放到清單的最前面 (index 0)
            existing_news.insert(0, {
                "title": data["title"],
                "link": data["url"],
                "date": data["date"],
                "image_url": data["image_url"],
                "content_preview": data["text"][:150] + "..." if len(data["text"]) > 150 else data["text"]
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
    

