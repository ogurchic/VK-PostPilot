import ollama
import vk_api
import random
import os
from dotenv import load_dotenv


# иницилизация
load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL") 
GROUP_ID = int(os.getenv("GROUP_ID"))
TOKEN = os.getenv("VK_API")

# Логика
def generate_post():
    with open("primary prompt.txt", "r", encoding="utf-8") as file:
        prompt = file.read()

    response = ollama.chat(model=LLM_MODEL, messages=[{"role": "user", "content": prompt}])
    return response['message']['content'].strip()

def publish_post(text):
    """Публикует пост в ВК."""
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    # Иногда LLM может добавить лишние кавычки в начале/конце, почистим текст
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

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