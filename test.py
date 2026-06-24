import os
from dotenv import load_dotenv
import vk_api


load_dotenv()
TOKEN = os.getenv("VK_API")
GROUP_ID = int(os.getenv("GROUP_ID")) 

def main():
    # 1. Инициализируем сессию с токеном сообщества
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    print(f"📤 Публикую пост в группу {GROUP_ID}...")
    
    try:
        # 2. Отправляем запрос к методу wall.post
        response = vk.wall.post(
            owner_id=-GROUP_ID,  # ⚠️ ОБЯЗАТЕЛЬНО со знаком МИНУС!
            from_group=1,        # ⚠️ Публиковать от имени группы
            message="Hello, world! 🤖 Тестовый запуск нейросети."
        )
        
        # 3. Выводим результат
        post_id = response['post_id']
        print(f"✅ Успех! Пост опубликован. ID поста: {post_id}")
        print(f"🔗 Ссылка: https://vk.com/wall-{GROUP_ID}_{post_id}")
        
    except vk_api.ApiError as e:
        # Красивый вывод ошибок от самого ВКонтакте
        print(f"❌ Ошибка ВК (код {e.code}): {e.message}")
    except Exception as e:
        print(f"❌ Произошла непредвиденная ошибка: {e}")

if __name__ == "__main__":
    main()