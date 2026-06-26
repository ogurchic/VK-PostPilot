import ollama
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL")

def get_next_monday():
    #Возвращает дату ближайшего понедельника
    today = datetime.now()
    days_ahead = 0 - today.weekday()  # Понедельник = 0
    if days_ahead <= 0:  # Если сегодня уже понедельник или позже
        days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)
    return next_monday.strftime("%Y-%m-%d")

def generate_content_plan():
    #Генерирует контент-план на неделю с помощью LLM
    print("🧠 Генерирую контент-план на неделю...")
    
    try:
        with open("planner_prompt.txt", "r", encoding="utf-8") as file:
            prompt = file.read()
    except FileNotFoundError:
        print("❌ Файл planner_prompt.txt не найден!")
        return None
        
    # 🔥 ВАЖНО: LLM плохо считают календарь. Подставляем реальные даты в конец промпта.
    next_monday = get_next_monday()
    today_str = datetime.now().strftime("%Y-%m-%d")
    date_context = f"\n\nСПРАВКА ПО ДАТАМ: Сегодня {today_str}. Ближайший понедельник — {next_monday}. Обязательно используй эти точные даты для первого дня плана и отсчитывай неделю от них."
    prompt += date_context
    
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_response = response['message']['content'].strip()
        
        # Иногда LLM может обернуть JSON в markdown-код, убираем это
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]
        if raw_response.startswith("```"):
            raw_response = raw_response[3:]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3]
        
        raw_response = raw_response.strip()
        
        # Парсим JSON
        plan = json.loads(raw_response)
        
        print(f"✅ План успешно сгенерирован! {len(plan)} постов.")
        return plan
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        print(f"Сырой ответ LLM:\n{raw_response}")
        return None
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
        return None

def save_plan(plan, filename="content_plan.json"):
    #Сохраняет контент-план в JSON файл.
    if not plan:
        print("❌ Нечего сохранять: план пуст.")
        return False
    
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(plan, file, ensure_ascii=False, indent=2)
        print(f"💾 План сохранен в файл: {filename}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения файла: {e}")
        return False

def display_plan(plan):
    #Красиво выводит план в консоль
    if not plan:
        return
    
    print("\n" + "=" * 60)
    print("📅 КОНТЕНТ-ПЛАН НА НЕДЕЛЮ")
    print("=" * 60)
    
    for post in plan:
        print(f"\n📌 {post['day']} ({post['date']}) в {post['time']}")
        print(f"   Формат: {post['format']}")
        print(f"   Тема: {post['topic']}")
        print(f"   Хук: {post['hook']}")
        print(f"   Ключевые тезисы:")
        for point in post['key_points']:
            print(f"     • {point}")
        print(f"   Призыв к действию: {post['call_to_action']}")
    
    print("\n" + "=" * 60)

def run_strategist_agent():
    """
    Главная функция агента. Вызывается оркестратором (main.py).
    Генерирует, показывает и сохраняет контент-план.
    """
    print("\n" + "="*60)
    print("📅 ЗАПУСК АГЕНТА-ПЛАНИРОВЩИКА")
    print("="*60)
    
    plan = generate_content_plan()
    
    if plan:
        display_plan(plan)
        save_plan(plan)
        print("\n🎉 Контент-план успешно создан и сохранен!")
        return True
    else:
        print("\n❌ Не удалось сгенерировать план. Попробуйте еще раз.")
        return False

if __name__ == "__main__":
    # Если файл запущен напрямую — выполняем основную функцию
    run_strategist_agent()