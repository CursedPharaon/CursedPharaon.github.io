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
GROUP_ID = 237327488
CONFIRMATION_CODE = "0c9c7a75"
# =====================

DATA_FILE = "broadcast_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"chats": [], "promo_text1": "Текст рассылки №1", "promo_text2": "Текст рассылки №2"}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
        requests.post(url, params=params)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

bot_data = load_data()

# ===== РАССЫЛКА ДВУХ ТЕКСТОВ КАЖДЫЕ 3 МИНУТЫ =====
def broadcast_loop():
    while True:
        time.sleep(180)  # 3 минуты
        if bot_data["chats"]:
            for chat_id in bot_data["chats"]:
                # Отправляем первый текст
                if bot_data["promo_text1"]:
                    send_message(chat_id, bot_data["promo_text1"])
                    time.sleep(1)  # пауза между сообщениями
                # Отправляем второй текст
                if bot_data["promo_text2"]:
                    send_message(chat_id, bot_data["promo_text2"])
                    time.sleep(1)
            print(f"📤 Рассылка выполнена в {len(bot_data['chats'])} чатов")

thread = Thread(target=broadcast_loop)
thread.daemon = True
thread.start()
# =================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    if data.get('type') == 'confirmation':
        return Response(CONFIRMATION_CODE, status=200, mimetype='text/plain')
    
    if data.get('type') == 'message_new':
        msg = data['object']['message']
        user_id = msg.get('from_id')
        text = msg.get('text', '')
        peer_id = msg.get('peer_id')
        
        # Команда .текст1 (только админ в ЛС)
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.текст1 '):
            new_text = text[8:]  # убираем ".текст1 "
            bot_data['promo_text1'] = new_text
            save_data(bot_data)
            send_message(peer_id, f"✅ Текст №1 обновлен:\n{new_text}")
            return 'ok'
        
        # Команда .текст2 (только админ в ЛС)
        if user_id == ADMIN_ID and peer_id == user_id and text.startswith('.текст2 '):
            new_text = text[8:]  # убираем ".текст2 "
            bot_data['promo_text2'] = new_text
            save_data(bot_data)
            send_message(peer_id, f"✅ Текст №2 обновлен:\n{new_text}")
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
                    send_message(peer_id, "✅ Чат добавлен в рассылку!\nСообщения будут приходить каждые 3 минуты (2 сообщения)")
            return 'ok'
    
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
