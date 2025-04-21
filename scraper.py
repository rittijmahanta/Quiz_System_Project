import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import sqlite3

def clean_content(text):
    keywords = [
        "To enjoy additional benefits", "CONNECT WITH US", "Updated -",
        "BACK TO TOP", "Terms & conditions", "Institutional Subscriber",
        "Comments have to be in English", "Copyright©"
    ]
    for key in keywords:
        text = text.replace(key, '')
    return text.strip()

def extract_date_from_url(url):
    match = re.search(r'(\d{1,2}(st|nd|rd|th)?-[a-zA-Z]+-\d{4})', url)
    if match:
        raw_date = match.group(1).replace('st', '').replace('nd', '').replace('rd', '').replace('th', '')
        try:
            dt = datetime.strptime(raw_date, '%d-%B-%Y')
            return dt.strftime('%d-%m-%y')
        except:
            return None
    return None

def start_scraping(duration_minutes):
    url = "https://forumias.com/blog/mustread/"
    start_time = time.time()
    duration = duration_minutes * 60
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if "must-read-" not in href:
                continue
            if time.time() - start_time > duration:
                break
            date = extract_date_from_url(href)
            forum_res = requests.get(href)
            forum_soup = BeautifulSoup(forum_res.text, 'html.parser')

            for anchor in forum_soup.find_all('a', href=True):
                article_url = anchor['href']
                title = anchor.text.strip()
                if article_url.startswith("https://www.thehindu.com") or article_url.startswith("https://epaper.thehindu.com"):
                    try:
                        article_res = requests.get(article_url)
                        article_soup = BeautifulSoup(article_res.text, 'html.parser')
                        paras = article_soup.find_all('p')
                        content = clean_content("\n".join([p.get_text() for p in paras]))
                        c.execute("INSERT INTO articles (url, title, content, date) VALUES (?, ?, ?, ?)",
                                  (article_url, title, content, date))
                        conn.commit()
                        time.sleep(1)
                    except:
                        continue
    except:
        pass
    finally:
        conn.close()
