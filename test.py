import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv
import os

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
BLOG_URL = os.getenv("BLOG_URL")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_latest_news_url():
    """Парсит главную страницу блога и возвращает ссылку на самую свежую новость."""
    print(f"🔎 Ищу свежие новости на {BLOG_URL}...")
    try:
        response = requests.get(BLOG_URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/blog/news_' in href or '/news/' in href:
                full_url = urljoin(BASE_URL, href)
                print(f"✅ Найдена свежая новость: {full_url}")
                return full_url
                
        print("❌ Не удалось найти ссылки на новости на странице блога.")
        return None
    except Exception as e:
        print(f"❌ Ошибка парсинга списка новостей: {e}")
        return None

def parse_news_content(url):
    """Парсит заголовок и текст конкретной новости."""
    print(f"📖 Загружаю текст новости...")
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем контейнер новости по характерному классу
        news_container = soup.find('div', class_='rounded-3xl')
        
        if not news_container:
            print("❌ Не найден контейнер новости")
            return None
        
        # Заголовок внутри контейнера
        title_tag = news_container.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "Без заголовка"
        
        # Текст новости: ищем div с классом "space-y-6" (там лежат абзацы)
        content_div = news_container.find('div', class_='space-y-6')
        
        content_paragraphs = []
        if content_div:
            for p_tag in content_div.find_all('p'):
                text = p_tag.get_text(strip=True)
                # Пропускаем пустые абзацы и разделители "---"
                if text and text != '---':
                    content_paragraphs.append(text)
        
        content = "\n".join(content_paragraphs)
        
        if not content:
            print("⚠️ Не удалось извлечь текст новости")
            return None
            
        return {
            "title": title,
            "url": url,
            "content": content
        }
    except Exception as e:
        print(f"❌ Ошибка парсинга текста новости: {e}")
        return None

# Тест
if __name__ == "__main__":
    news_url = get_latest_news_url()
    if news_url:
        news_data = parse_news_content(news_url)
        if news_data:
            print(f"\n{'='*60}")
            print(f"✅ ЗАГОЛОВОК: {news_data['title']}")
            print(f"{'='*60}")
            print(f"\n{news_data['content']}...")
            print(f"\n[Всего символов: {len(news_data['content'])}]")