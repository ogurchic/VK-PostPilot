import ollama
import vk_api
import os
import re
from dotenv import load_dotenv


# иницилизация
load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL") 
GROUP_ID = int(os.getenv("GROUP_ID"))
TOKEN = os.getenv("VK_API")

# Логика
def clean_markdown(text):
    """
    Удаляет Markdown-разметку из текста, так как ВК её не понимает.
    Это страховка на случай, если LLM всё-таки сгенерирует звездочки.
    """
    # Убираем жирный текст **текст** или __текст__
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Убираем курсив *текст* или _текст_
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    
    # Убираем маркеры списков - элемент или * элемент
    text = re.sub(r'^[\*\-]\s+', '• ', text, flags=re.MULTILINE) # Заменяем на красивый буллит
    
    # Убираем обратные кавычки `код`
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    return text.strip()

def generate_post():
    with open("primary prompt.txt", "r", encoding="utf-8") as file:
        prompt = file.read()

    response = ollama.chat(model=LLM_MODEL, messages=[{"role": "user", "content": prompt}])
    raw_text = response['message']['content'].strip()
    
    # Чистим текст от возможного Markdown
    clean_text = clean_markdown(raw_text)
    
    # Иногда LLM может добавить лишние кавычки в начале/конце, почистим и их
    if clean_text.startswith('"') and clean_text.endswith('"'):
        clean_text = clean_text[1:-1]
        
    return clean_text

def publish_post(text):
    """Публикует пост в ВК."""
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()

    response = vk.wall.post(owner_id=-GROUP_ID, from_group=1, message=text)
    return response['post_id']

if __name__ == "__main__":
    print("🚀 Запуск автономного пайплайна...")
    
    # 1. Мозг генерирует
    print("1. Генерирую текст...")
    post_text = generate_post()
    print(f"Сгенерированный текст:\n{post_text}\n")
    
    # 2. Руки публикуют
    print("2. Публикую в ВКонтакте...")
    try:
        post_id = publish_post(post_text)
        print(f"🎉 Готово! Пост {post_id} улетел на стену.")
    except Exception as e:
        print(f"Не удалось опубликовать: {e}")