import os
from flask import Flask, request, Response

app = Flask(__name__)

CONFIRMATION_CODE = "e0b370c6"  # твой код

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Получен запрос:", data)  # это попадет в логи Render
    
    if data and data.get('type') == 'confirmation':
        # Возвращаем ТОЛЬКО код, ничего больше
        return Response(CONFIRMATION_CODE, status=200, mimetype='text/plain')
    
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
