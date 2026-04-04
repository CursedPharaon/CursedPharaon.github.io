import os
import json
import time
import requests
from flask import Flask, request, Response
from threading import Thread

app = Flask(__name__)

# ===== НАСТРОЙКИ =====
VK_TOKEN = os.environ.get("VK_TOKEN")
ADMIN_ID = 1076312001
GROUP_ID = 237327488  # ID вашей группы (положительное число)
CONFIRMATION_CODE = "0c9c7a75"
# =====================

DATA_FILE = "broadcast_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"chats": [], "promo_text": "Привет! Это тестовая рассылка."}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_message(peer_id, text):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "v": "5.199",
        "peer_id": peer_id,
        "message": text,
        "random_id": 0
    }
    try:
        requests.post(url, params=params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ===== ПРОВЕРКА ПОДПИСКИ НА КАНАЛ =====
def check_subscription(user_id):
    """
    Проверяет, подписан ли пользователь на канал.
    Возвращает True, если подписан.
    """
    url = "https://api.vk.com/method/groups.isMember"
    params = {
        "access_token": VK_TOKEN,
        "v": "5.199",
        "group_id": GROUP_ID,
        "user_id": user_id
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Проверяем, есть ли ошибка в ответе
        if "error" in data:
            print(f"Ошибка API: {data['error']}")
            return False
        
        # Метод groups.isMember возвращает 1 если подписан, 0 если нет [citation:4]
        return data.get("response", 0) == 1
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False
# ====================================

bot_data = load_data()

# ===== РАССЫЛКА КАЖДЫЕ 3 МИНУТЫ =====
def broadcast_loop():
    while True:
        time.sleep(180)
        if bot_data["chats"] and bot_data["promo_text"]:
            print(f"📤 Рассылка в {len(bot_data['chats'])} чатов")
            for chat_id in bot_data["chats"]:
                send_message(chat_id, bot_data["promo_text"])
                time.sleep(1)

thread = Thread(target=broadcast_loop)
thread.daemon = True
thread.start()
# ===================================

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    # Код подтверждения
    if data.get('type') == 'confirmation':
        return Response(CONFIRMATION_CODE, status=200, mimetype='text/plain')
    
    if data.get('type') == 'message_new':
        msg = data['object']['message']
        user_id = msg.get('from_id')
        text = msg.get('text', '')
        peer_id = msg.get('peer_id')
        
        # Проверка подписки (для всех команд, кроме администратора)
        # Администратору даём полный доступ без проверки подписки
        if user_id != ADMIN_ID:
            if not check_subscription(user_id):
                send_message(peer_id, "❌ Для использования бота нужно быть подписчиком канала!")
                return 'ok'
        
        # Команда .текст (только админ в ЛС)
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.текст '):
            new_text = text[7:]
            bot_data['promo_text'] = new_text
            save_data(bot_data)
            send_message(peer_id, f"✅ Текст обновлен: {new_text}")
            return 'ok'
        
        # Команда .чаты
        if user_id == ADMIN_ID and peer_id == user_id and text == '.чаты':
            if bot_data['chats']:
                chats_list = "\n".join([f"- {c}" for c in bot_data['chats']])
                send_message(peer_id, f"📋 Чаты:\n{chats_list}\nВсего: {len(bot_data['chats'])}")
            else:
                send_message(peer_id, "📭 Чатов нет")
            return 'ok'
        
        # Команда .удалить
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.удалить '):
            try:
                chat_id = int(text[9:])
                if chat_id in bot_data['chats']:
                    bot_data['chats'].remove(chat_id)
                    save_data(bot_data)
                    send_message(peer_id, f"✅ Чат {chat_id} удален")
                else:
                    send_message(peer_id, f"❌ Чат {chat_id} не найден")
            except:
                send_message(peer_id, "❌ Укажите ID")
            return 'ok'
        
        # Добавление чата при приглашении бота
        if 'action' in msg and msg['action'].get('type') == 'chat_invite_user':
            invited_id = msg['action'].get('member_id')
            if invited_id == -GROUP_ID:
                if peer_id not in bot_data['chats']:
                    bot_data['chats'].append(peer_id)
                    save_data(bot_data)
                    send_message(peer_id, "✅ Чат добавлен в рассылку!\nСообщения будут приходить каждые 3 минуты.")
            return 'ok'
    
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
