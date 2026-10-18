import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    # Render передает порт в переменной PORT
    port = int(os.environ.get("PORT", 8080))
    print(f"[Flask] Запуск веб-сервера на порту {port}...", flush=True)
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
