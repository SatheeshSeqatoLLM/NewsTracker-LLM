from flask import Flask, render_template, jsonify, request
from summarizer import get_news_data
from config import PORT
from datetime import datetime

app = Flask(__name__, template_folder='../templates', static_folder='../static')

@app.route('/')
def index():
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    return render_template('index.html', current_date=current_date)

@app.route('/news')
def news():
    topic = request.args.get('topic')
    country = request.args.get('country')
    news_data = get_news_data(topic=topic, country=country)
    return jsonify(news_data)

if __name__ == '__main__':
    app.run(debug=True, port=PORT)
