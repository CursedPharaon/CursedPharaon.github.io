import os
import json
import requests
from flask import Flask, request, Response

app = Flask(__name__)

# ===== НАСТРОЙКИ (меняем на свои) =====
VK_TOKEN = os.environ.get("VK_TOKEN")
ADMIN_ID = 1076312001  # ID пользователя @kalashnikov3002 (число!)
GROUP_ID = 237327488  # ID вашего сообщества VK (число!)
CONFIRMATION_CODE = "e0b370c6"  # Из настроек Callback API
# ========================================

DATA_FILE = "broadcast_data.json"

# Загрузка данных из файла
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"chats": [], "promo_text": "Привет! Это тестовая рассылка."}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Отправка сообщения через VK API
def send_message(peer_id, text):
    url = "https://api.vk.com/method/messages.send"
    params = {
        "access_token": VK_TOKEN,
        "v": "5.131",
        "peer_id": peer_id,
        "message": text,
        "random_id": 0
    }
    try:
        response = requests.post(url, params=params)
        return response.json()
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return None

# Глобальные данные
bot_data = load_data()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    # 1. Подтверждение сервера
    if data.get('type') == 'confirmation':
        return Response(content=CONFIRMATION_CODE, media_type="text/plain")
    
    # 2. Обработка новых сообщений
    if data.get('type') == 'message_new':
        msg = data['object']['message']
        user_id = msg.get('from_id')
        text = msg.get('text', '')
        peer_id = msg.get('peer_id')
        
        # Команда .текст (только админ в личные сообщения)
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.текст '):
            new_text = text[7:]  # Убираем ".текст "
            bot_data['promo_text'] = new_text
            save_data(bot_data)
            send_message(peer_id, f"✅ Текст рассылки обновлен!\n\nНовый текст: {new_text}")
            return 'ok'
        
        # Команда .чаты (только админ) - посмотреть список чатов
        if user_id == ADMIN_ID and peer_id == user_id and text == '.чаты':
            if bot_data['chats']:
                chats_list = "\n".join([f"- {chat_id}" for chat_id in bot_data['chats']])
                send_message(peer_id, f"📋 Чаты в рассылке:\n{chats_list}\n\nВсего: {len(bot_data['chats'])}")
            else:
                send_message(peer_id, "📭 Список чатов пуст.")
            return 'ok'
        
        # Команда .удалить 123 (только админ)
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.удалить '):
            try:
                chat_id = int(text[9:])
                if chat_id in bot_data['chats']:
                    bot_data['chats'].remove(chat_id)
                    save_data(bot_data)
                    send_message(peer_id, f"✅ Чат {chat_id} удален из рассылки.")
                else:
                    send_message(peer_id, f"❌ Чат {chat_id} не найден.")
            except ValueError:
                send_message(peer_id, "❌ Укажите корректный ID чата")
            return 'ok'
        
        # Добавление чата, когда бота пригласили
        if 'action' in msg and msg['action'].get('type') == 'chat_invite_user':
            if msg['action'].get('member_id') == -GROUP_ID:
                # peer_id = 2000000000 + chat_id для бесед
                if peer_id not in bot_data['chats']:
                    bot_data['chats'].append(peer_id)
                    save_data(bot_data)
                    send_message(peer_id, "✅ Чат добавлен в рассылку!")
            return 'ok'
    
    return 'ok'

# Запуск сервера
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)