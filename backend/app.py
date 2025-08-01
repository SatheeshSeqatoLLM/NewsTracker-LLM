from flask import Flask, render_template, jsonify, request
from summarizer import get_news_data
from config import PORT
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Initialize scheduler
scheduler = BackgroundScheduler()

def refresh_cache():
    print("\n--- Automatically refreshing news cache ---")
    get_news_data(topic=None, force_refresh=True) # Refresh general news
    # You can add more topics to refresh here if needed
    print("--- News cache refreshed ---")

# Schedule the job to run every 10 minutes
scheduler.add_job(func=refresh_cache, trigger="interval", minutes=10)

# Start the scheduler
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    # Ensure cache is populated on first load if empty
    if not get_news_data(topic=None): # Check if general news cache is empty
        refresh_cache()
    return render_template('index.html', current_date=current_date)

@app.route('/news')
def news():
    topic = request.args.get('topic')
    news_data = get_news_data(topic=topic)
    return jsonify(news_data)

if __name__ == '__main__':
    app.run(debug=True, port=PORT, use_reloader=False) # use_reloader=False to prevent scheduler from running twice