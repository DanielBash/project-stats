"""
Файл запуска приложения и объявление основных путей.
"""

# -- импорт модулей
import hashlib
from datetime import datetime
from flask import Flask, jsonify, request, make_response
from config import config
from utils import get_stats, render_image

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# -- коммуникация с пользователем
@app.route('/repo', methods=['GET'])
def get_stats_image():
    repo = request.args.get('repo')

    if not repo:
        return jsonify({"error": "Не указан репозиторий"}), 400

    stats = get_stats(repo, config)
    if not stats:
        return jsonify({"error": "Не удалось собрать статистику"}), 500

    img_buffer = render_image(stats)
    print(stats)

    response = make_response(img_buffer.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers['Content-Disposition'] = f'inline; filename=stats_{hashlib.md5(repo.encode()).hexdigest()[:8]}.png'

    return response

@app.route('/')
def index():
    life = datetime.now().isoformat()
    return f'[{life}] Сервер запущен'

# -- запуск приложения
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=config.PORT, debug=config.DEBUG)