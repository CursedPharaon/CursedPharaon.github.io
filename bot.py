import asyncio
import json
import os
from vkbottle.bot import Bot, Message

BOT_TOKEN = "YOUR_TOKEN"
ADMIN_ID = 123456789  # ID пользователя @kalashnikov3002
DATA_FILE = "broadcast_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"chats": [], "promo_text": "Привет! Это рассылка."}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

bot_data = load_data()
bot = Bot(token=BOT_TOKEN)

@bot.on.private_message(text=".текст <text>")
async def set_promo_text(message: Message, text: str):
    if message.from_id != ADMIN_ID:
        return
    bot_data["promo_text"] = text
    save_data(bot_data)
    await message.answer(f"✅ Текст обновлен: {text}")

@bot.on.chat_message()
async def on_chat_message(message: Message):
    # Проверяем, что бота добавили в чат
    if message.action and message.action.type == "chat_invite_user":
        if message.action.member_id == -bot.group_id:
            if message.chat_id not in bot_data["chats"]:
                bot_data["chats"].append(message.chat_id)
                save_data(bot_data)
                await message.answer("Чат добавлен в рассылку")

async def broadcast():
    while True:
        if bot_data["chats"] and bot_data["promo_text"]:
            for chat_id in bot_data["chats"]:
                try:
                    await bot.api.messages.send(
                        peer_id=2000000000 + chat_id,
                        message=bot_data["promo_text"],
                        random_id=0
                    )
                except Exception as e:
                    print(f"Ошибка: {e}")
                await asyncio.sleep(1)
        await asyncio.sleep(240)

async def main():
    asyncio.create_task(broadcast())
    await bot.run_polling()

if __name__ == "__main__":
    asyncio.run(main())