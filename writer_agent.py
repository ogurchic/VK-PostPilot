import ollama
import json
import vk_api
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL")
GROUP_ID = int(os.getenv("GROUP_ID"))
TOKEN = os.getenv("VK_API")


def clean_markdown(text):
    """Удаляет Markdown-разметку из текста."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'^[\*\-]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text.strip()


def load_plan(filename="content_plan.json"):
    #Загружает контент-план из файла
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"❌ Файл {filename} не найден. Сначала запустите planner_agent.py")
        return None
    except Exception as e:
        print(f"❌ Ошибка загрузки плана: {e}")
        return None


def generate_post_from_plan(post_plan):
    #Генерирует полный текст поста на основе пункта из контент-плана
    prompt = f"""Ты — опытный копирайтер и SMM-специалист. Твоя задача — написать полноценный пост для ВКонтакте на основе плана.

ПЛАН ПОСТА:
- День: {post_plan['day']}
- Тема: {post_plan['topic']}
- Формат: {post_plan['format']}
- Цепляющий заголовок/хук: {post_plan['hook']}
- Ключевые тезисы для раскрытия:
{chr(10).join(['  • ' + point for point in post_plan['key_points']])}
- Призыв к действию в конце: {post_plan['call_to_action']}

ТРЕБОВАНИЯ К ПОСТУ:
1. Начни пост с хука (цепляющего заголовка), чтобы привлечь внимание
2. Раскрой каждый ключевой тезис подробно, но без воды
3. Используй дружелюбный, экспертный тон
4. Добавь 2-3 эмодзи для визуального разнообразия (но не переборщи)
5. Закончи пост четким призывом к действию (вопросом к аудитории)
6. Разбей текст на абзацы (2-3 предложения в каждом) для легкости чтения
7. Используй ЗАГЛАВНЫЕ БУКВЫ для коротких акцентов
8. НЕ ИСПОЛЬЗУЙ Markdown (звездочки, решетки, дефисы для списков)

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО готовый текст поста, без лишних слов вроде "Вот ваш пост" или "Конечно!".
"""
    
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_text = response['message']['content'].strip()
        clean_text = clean_markdown(raw_text)
        
        # Убираем лишние кавычки
        if clean_text.startswith('"') and clean_text.endswith('"'):
            clean_text = clean_text[1:-1]
        
        return clean_text
        
    except Exception as e:
        print(f"❌ Ошибка генерации поста: {e}")
        return None


def publish_post(text, publish_date=None):
    #Публикует пост в ВК (с отложенной публикацией или сразу).
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    try:
        params = {
            "owner_id": -GROUP_ID,
            "from_group": 1,
            "message": text
        }
        
        # Если указана дата — ставим отложенный постинг
        if publish_date:
            params["publish_date"] = int(publish_date.timestamp())
        
        response = vk.wall.post(**params)
        return response['post_id']
        
    except vk_api.ApiError as e:
        raise Exception(f"Ошибка ВК API (код {e.code}): {e.message}")


def write_and_publish_first_post(publish_now=False):
    """
    Берет первый пост из контент-плана, генерирует текст и публикует.
    
    Args:
        publish_now: Если True — публикует сразу. Если False — ставит в отложку.
    
    Returns:
        int: ID поста, если успешно. None, если ошибка.
    """
    print("🚀 Агент-писатель начинает работу...")
    
    # Загружаем план
    plan = load_plan()
    if not plan or len(plan) == 0:
        print("❌ Контент-план пуст или не найден.")
        return None
    
    # Берем первый пост
    first_post = plan[0]
    print(f"📝 Работаю с постом: {first_post['topic']}")
    print(f"   День: {first_post['day']} ({first_post['date']}) в {first_post['time']}")
    
    # Генерируем текст
    print("🧠 Генерирую текст поста...")
    post_text = generate_post_from_plan(first_post)
    
    if not post_text:
        print("❌ Не удалось сгенерировать текст.")
        return None
    
    print(f"✅ Текст сгенерирован ({len(post_text)} символов)")
    print(f"\n{'='*60}")
    print(f"Превью поста:\n{post_text[:300]}...")
    print(f"{'='*60}\n")
    
    # Публикуем или ставим в отложку
    try:
        if publish_now:
            post_id = publish_post(post_text)
            print(f"🎉 Пост опубликован! ID: {post_id}")
            print(f"🔗 Ссылка: https://vk.com/wall-{GROUP_ID}_{post_id}")
        else:
            # Конвертируем дату и время в timestamp
            date_obj = datetime.strptime(f"{first_post['date']} {first_post['time']}", "%Y-%m-%d %H:%M")
            post_id = publish_post(post_text, publish_date=date_obj)
            print(f"⏰ Пост поставлен в отложку на {first_post['date']} {first_post['time']}. ID: {post_id}")
        
        return post_id
        
    except Exception as e:
        print(f"❌ Ошибка публикации: {e}")
        return None


if __name__ == "__main__":
    # Если файл запущен напрямую — выполняем основную функцию
    
    print("Выберите режим работы:")
    print("1. Поставить первый пост в отложку (рекомендуется)")
    print("2. Опубликовать первый пост сразу")
    
    choice = input("\nВведите номер (1/2): ").strip()
    
    if choice == "1":
        write_and_publish_first_post(publish_now=False)
    elif choice == "2":
        print("⚠️  ВНИМАНИЕ: Пост будет опубликован прямо сейчас!")
        confirm = input("Вы уверены? (да/нет): ").strip().lower()
        if confirm == "да":
            write_and_publish_first_post(publish_now=True)
        else:
            print("Отменено.")
    else:
        print("❌ Неверный выбор.")