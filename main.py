import sys
from datetime import datetime

# Импортируем агентов
import writer_agent
# import planner_agent  # Будет добавлен позже
# import analyst_agent  # Будет добавлен позже


def show_menu():
    """Показывает главное меню."""
    print("\n" + "="*60)
    print("🤖 VK POSTPILOT — АВТОНОМНЫЙ SMM-БОТ")
    print("="*60)
    print(f"📅 Текущая дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nВыберите действие:")
    print("1. 📝 Написать и опубликовать первый пост из плана")
    print("2. 📅 Составить контент-план на неделю (скоро)")
    print("3. 📊 Проанализировать статистику постов (скоро)")
    print("4. 🔄 Запустить полный цикл (анализ → план → посты) (скоро)")
    print("0. Выход")
    print("="*60)


def main():
    """Главная функция — оркестратор агентов."""
    while True:
        show_menu()
        choice = input("\nВведите номер команды: ").strip()
        
        if choice == "1":
            print("\nВыберите режим публикации:")
            print("1. Поставить в отложку (рекомендуется)")
            print("2. Опубликовать сразу")
            pub_choice = input("Ваш выбор (1/2): ").strip()
            
            if pub_choice == "1":
                writer_agent.write_and_publish_first_post(publish_now=False)
            elif pub_choice == "2":
                confirm = input("⚠️  Пост будет опубликован СЕЙЧАС. Продолжить? (да/нет): ").strip().lower()
                if confirm == "да":
                    writer_agent.write_and_publish_first_post(publish_now=True)
                else:
                    print("Отменено.")
            else:
                print("❌ Неверный выбор.")
        
        elif choice == "2":
            print("\n🚧 Функция в разработке. Скоро здесь будет planner_agent.")
        
        elif choice == "3":
            print("\n🚧 Функция в разработке. Скоро здесь будет analyst_agent.")
        
        elif choice == "4":
            print("\n🚧 Функция в разработке. Скоро здесь будет полный пайплайн.")
        
        elif choice == "0":
            print("\n👋 До свидания!")
            break
        
        else:
            print("\n❌ Неверная команда. Попробуйте еще раз.")


if __name__ == "__main__":
    main()