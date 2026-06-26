import ollama
import vk_api
import os
import re
import requests
import tempfile
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL")
GROUP_ID = int(os.getenv("GROUP_ID"))
TOKEN = os.getenv("VK_API")

BASE_URL = os.getenv("BASE_URL")
BLOG_URL = os.getenv("BLOG_URL")

# Заголовки, чтобы сайт не думал, что мы злобные боты
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

LAST_ID_FILE = "last_news_id.txt"
DEFAULT_START_ID = 160

def get_last_id():
    #Читает последний известный ID новости из файла
    if os.path.exists(LAST_ID_FILE):
        try:
            with open(LAST_ID_FILE, "r") as f:
                return int(f.read().strip())
        except:
            return DEFAULT_START_ID
    return DEFAULT_START_ID

def save_last_id(news_id):
    #Сохраняет ID, чтобы в следующий раз искать от него
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(news_id))

def clean_markdown(text):
    #Удаляет Markdown-разметку (страховка)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'^[\*\-]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text.strip()

def get_latest_news_url():
    #Находит URL самой свежей новости, перебирая ID по порядку
    print(f"🔎 Ищу свежие новости на {BLOG_URL}...")
    current_id = get_last_id()
    
    # Перебираем ID от current_id до current_id + 30 (защита от бесконечного цикла)
    for i in range(current_id, current_id + 30):
        url = f"{BASE_URL}/blog/news_{i}"
        try:
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                print(f"✅ Найдена свежая новость: {url}")
                # Сохраняем СЛЕДУЮЩИЙ ID, чтобы при следующем запуске не проверять эту новость
                save_last_id(i + 1) 
                return url
            elif response.status_code == 404:
                continue # Новость с таким ID не существует (или удалена), пробуем следующий
            else:
                continue
        except Exception as e:
            print(f"⚠️ Ошибка запроса {url}: {e}")
            continue
            
    print("❌ Не удалось найти новые новости (проверено 30 ID подряд).")
    return None


def parse_news_content(url):
    #Парсит заголовок и текст конкретной новости
    print(f"📖 Загружаю текст новости...")
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_container = soup.find('div', class_='rounded-3xl')
        
        if not news_container:
            print("❌ Не найден контейнер новости (rounded-3xl). Возможно, изменилась верстка.")
            # Фолбэк: ищем h1 на всей странице
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Новости"
            content = ""
            image_url = None
        else:
            # Заголовок внутри контейнера
            title_tag = news_container.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Новости"
            
            # 🖼️ Ищем картинку (она лежит в div с классом, содержащим "relative h-64")
            image_url = None
            img_container = news_container.find('div', class_=lambda c: c and 'relative' in c and 'h-64' in c)
            if img_container:
                img_tag = img_container.find('img')
                if img_tag and img_tag.get('src'):
                    # URL может быть относительным (/_next/image?url=...), делаем абсолютным
                    image_url = urljoin(BASE_URL, img_tag['src'])
                    print(f"🖼️ Найдена картинка: {image_url}")
            
            # 📝 Текст новости: ищем div с классом "space-y-6" (там лежат абзацы)
            content_div = news_container.find('div', class_='space-y-6')
            
            content_paragraphs = []
            if content_div:
                for p_tag in content_div.find_all('p'):
                    text = p_tag.get_text(strip=True)
                    # Пропускаем пустые абзацы и разделители "---"
                    if text and text != '---':
                        content_paragraphs.append(text)
            
            content = "\n".join(content_paragraphs)
        
        # Фолбэк: если текст не нашли в контейнере, берем все длинные абзацы
        if not content:
            all_p = soup.find_all('p')
            long_paragraphs = [p.get_text(strip=True) for p in all_p if len(p.get_text(strip=True)) > 50]
            if long_paragraphs:
                content = "\n".join(long_paragraphs[:10])
        
        if not content:
            print("⚠️ Не удалось извлечь текст новости.")
            return None
            
        return {
            "title": title,
            "url": url,
            "content": content,
            "image_url": image_url  # <-- Новое поле
        }
    except Exception as e:
        print(f"❌ Ошибка парсинга текста новости: {e}")
        return None

def download_image(image_url):
    """
    Скачивает картинку по URL во временный файл.
    Возвращает путь к файлу или None, если не удалось.
    """
    if not image_url:
        return None
    
    print(f"⬇️  Скачиваю картинку...")
    try:
        response = requests.get(image_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Определяем расширение по Content-Type
        content_type = response.headers.get('Content-Type', '')
        is_webp = 'webp' in content_type or '.webp' in image_url
        
        # Создаем временный файл
        if is_webp:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webp')
            temp_file.write(response.content)
            temp_file.close()
            
            # Конвертируем webp → jpg
            print("🔄 Конвертирую webp в jpg...")
            try:
                img = Image.open(temp_file.name)
                jpg_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                img.convert('RGB').save(jpg_file.name, 'JPEG', quality=90)
                jpg_file.close()
                
                # Удаляем исходный webp
                os.remove(temp_file.name)
                
                print(f"✅ Картинка сконвертирована: {jpg_file.name}")
                return jpg_file.name
            except Exception as conv_err:
                print(f"⚠️ Ошибка конвертации webp: {conv_err}. Использую исходный файл.")
                return temp_file.name
        else:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(response.content)
            temp_file.close()
            print(f"✅ Картинка сохранена: {temp_file.name}")
            return temp_file.name
        
    except Exception as e:
        print(f"❌ Ошибка скачивания картинки: {e}")
        return None

def upload_photo_to_vk(image_path):
    """
    Загружает картинку на сервер ВК для публикации на стене.
    Возвращает строку attachment вида "photo123_456" или None.
    """
    print(f"📤 Загружаю картинку в ВКонтакте...")
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    try:
        # 1. Получаем URL сервера для загрузки
        upload_url = vk.photos.getWallUploadServer(group_id=GROUP_ID)['upload_url']
        
        # 2. Загружаем файл на сервер
        with open(image_path, 'rb') as photo_file:
            response = requests.post(upload_url, files={'photo': photo_file})
        
        if response.status_code != 200:
            print(f"❌ Ошибка загрузки на сервер ВК: {response.status_code}")
            return None
            
        upload_result = response.json()
        
        # Проверяем, нет ли ошибки в ответе
        if 'error' in upload_result:
            print(f"❌ ВК вернул ошибку: {upload_result}")
            return None
        
        # 3. Сохраняем фото и получаем его ID
        save_result = vk.photos.saveWallPhoto(
            group_id=GROUP_ID,
            photo=upload_result['photo'],
            server=upload_result['server'],
            hash=upload_result['hash']
        )
        
        photo = save_result[0]
        attachment = f"photo{photo['owner_id']}_{photo['id']}"
        
        print(f"✅ Картинка загружена: {attachment}")
        return attachment
        
    except Exception as e:
        print(f"❌ Ошибка загрузки фото в ВК: {e}")
        return None
    finally:
        # Удаляем временный файл
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"🗑️  Временный файл удален")
            except:
                pass

def generate_news_post_text(news_data):
    #Генерирует пост для ВК на основе новости с сайта
    prompt = f"""Ты — SMM-специалист компании. Твоя задача — написать новостной пост для ВКонтакте на основе новости с нашего корпоративного сайта.

НОВОСТЬ С САЙТА:
Заголовок: {news_data['title']}
Текст: {news_data['content']}

ТРЕБОВАНИЯ К ПОСТУ:
1. НЕ КОПИРУЙ текст новости дословно. Переработай его и скрати в формат поста для соцсетей.
2. Начни с цепляющего заголовка (используй ЗАГЛАВНЫЕ БУКВЫ или эмодзи ❗️🔥💡).
3. Кратко перескажи суть новости (2-3 предложения), чтобы читатель понял, о чем речь.
4. Тон голоса: экспертный, уверенный, но дружелюбный. Без воды.
5. Используй эмодзи в меру (2-3 штуки).
6. В конце задай вопрос аудитории или предложи обсудить новость в комментариях.
7. НЕ ИСПОЛЬЗУЙ Markdown (звездочки, решетки, дефисы).
8. В самом низу поста добавь ссылку на полный текст: Читать подробнее на сайте: {news_data['url']}

Верни ТОЛЬКО готовый текст поста, без лишних слов.
"""
    print("🧠 Генерирую пост на основе новости...")
    try:
        response = ollama.chat(model=LLM_MODEL, messages=[{"role": "user", "content": prompt}])
        raw_text = response['message']['content'].strip()
        clean_text = clean_markdown(raw_text)
        
        if clean_text.startswith('"') and clean_text.endswith('"'):
            clean_text = clean_text[1:-1]
            
        return clean_text
    except Exception as e:
        print(f"❌ Ошибка генерации текста: {e}")
        return None

def publish_post(text, attachment=None):
    #Публикует пост в ВК
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    try:
        params = {
            "owner_id": -GROUP_ID,
            "from_group": 1,
            "message": text
        }
        
        # Если есть картинка — прикрепляем её
        if attachment:
            params["attachments"] = attachment
            
        response = vk.wall.post(**params)
        return response['post_id']
    except vk_api.ApiError as e:
        raise Exception(f"Ошибка ВК API (код {e.code}): {e.message}")

def write_and_publish_news(publish_now=False):
    #Главная функция агента. Берет свежую новость, делает пост и публикует
    print("\n" + "="*60)
    print("📰 ЗАПУСК АГЕНТА-НОВOСTНИКА")
    print("="*60)
    
    # 1. Ищем ссылку на свежую новость
    news_url = get_latest_news_url()
    if not news_url:
        return False
        
    # 2. Парсим её содержимое
    news_data = parse_news_content(news_url)
    if not news_data:
        return False
        
    print(f"📰 Заголовок: {news_data['title']}")
    
    # 3. Скачиваем и загружаем картинку в ВК (если она есть)
    attachment = None
    if news_data.get('image_url'):
        image_path = download_image(news_data['image_url'])
        if image_path:
            attachment = upload_photo_to_vk(image_path)
    else:
        print("⚠️ Картинка не найдена в новости. Пост будет опубликован без изображения.")

    # 4. Генерируем пост
    post_text=news_data
    post_text = generate_news_post_text(news_data)
    if not post_text:
        return False
        
    print(f"\n{'='*60}")
    print(f"Превью поста:\n{post_text}...")
    print(f"{'='*60}\n")
    
    # 5. Публикуем
    try:
        post_id = publish_post(post_text,attachment=attachment)
        print(f"🎉 Новостной пост опубликован! ID: {post_id}")
        print(f"🔗 Ссылка: https://vk.com/wall-{GROUP_ID}_{post_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")
        return False

if __name__ == "__main__":
    write_and_publish_news()