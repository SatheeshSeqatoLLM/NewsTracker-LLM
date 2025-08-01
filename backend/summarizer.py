from transformers import pipeline
from newsapi import NewsApiClient
import requests
from bs4 import BeautifulSoup
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Caching ---
cached_news_data = {}
last_cache_time = {}
CACHE_DURATION = 1800  # 30 minutes
# ----------------

# --- AI Summarizer ---
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")
# ---------------------

# --- NewsAPI Configuration ---
# Init with your API key
# You MUST replace 'YOUR_API_KEY' in backend/config.py with your actual key
NEWS_API_KEY = os.environ.get('NEWS_API_KEY') # Get from environment variable
if not NEWS_API_KEY:
    from config import NEWS_API_KEY as CONFIG_NEWS_API_KEY
    NEWS_API_KEY = CONFIG_NEWS_API_KEY

newsapi = NewsApiClient(api_key=NEWS_API_KEY)
# -----------------------------

def scrape_image_from_article(url):
    """Attempts to scrape a main image URL from an article page."""
    if not url: return None
    print(f"Attempting to scrape image from: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.text, 'html.parser')

        # Try to find og:image meta tag
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            print(f"Scraped og:image: {og_image.get('content')}")
            return og_image.get('content')

        # Try to find a large image within the article content (simple heuristic)
        main_content = soup.find('article') or soup.find('main') or soup.find('body')
        if main_content:
            img = main_content.find('img', class_=lambda x: x and ('hero' in x or 'main' in x or 'article' in x), src=True)
            if img and img.get('src'):
                # Ensure it's an absolute URL
                img_url = img.get('src')
                if not img_url.startswith('http'):
                    from urllib.parse import urljoin
                    img_url = urljoin(url, img_url)
                print(f"Scraped img tag: {img_url}")
                return img_url

    except requests.exceptions.RequestException as e:
        print(f"HTTP/Network error scraping image from {url}: {e}")
    except Exception as e:
        print(f"Error scraping image from {url}: {e}")
    return None

def fetch_news_headlines(topic=None):
    """Fetches top headlines using NewsAPI."""
    print(f"Fetching headlines from NewsAPI for topic: {topic}")
    articles = []

    try:
        params = {'language': 'en', 'page_size': 20}
        if topic:
            params['q'] = topic

        if 'q' not in params:
             top_headlines = newsapi.get_top_headlines(language='en', page_size=20)
        else:
             top_headlines = newsapi.get_top_headlines(**params)

        if top_headlines and top_headlines['articles']:
            for article in top_headlines['articles']:
                articles.append({
                    'title': article.get('title'),
                    'url': article.get('url'),
                    'description': article.get('description'),
                    'image_url': article.get('urlToImage')
                })
        print(f"Fetched {len(articles)} headlines from NewsAPI.")
    except Exception as e:
        print(f"Could not fetch headlines from NewsAPI: {e}")
    return articles

def summarize_text(texts):
    """Summarizes a batch of texts using our AI model."""
    if not texts: return []
    try:
        # The pipeline is most efficient when processing a batch of texts
        summaries = summarizer(texts, max_length=150, min_length=30, do_sample=False)
        return [s['summary_text'] for s in summaries]
    except Exception as e:
        print(f"Error summarizing texts: {e}")
        return [""] * len(texts)

def get_news_data(topic=None, force_refresh=False):
    """Tracks news, processes, and summarizes it using a cache."""
    global cached_news_data, last_cache_time
    
    cache_key = f"{topic or 'general'}"

    if not force_refresh and cache_key in cached_news_data and (time.time() - last_cache_time.get(cache_key, 0) < CACHE_DURATION):
        print(f"\n--- Serving from Cache for key: {cache_key} ---")
        return cached_news_data[cache_key]

    print(f"\n--- Tracking new data from NewsAPI for topic: {topic or 'general'} ---")

    
    articles = fetch_news_headlines(topic=topic)

    print(f"Number of articles fetched: {len(articles)}")

    if not articles:
        print("No articles found from NewsAPI.")
        return {"trending": [], "featured": None, "related": [], "highlights": []}

    start_time = time.time()

    # --- Parallel Image Scraping ---
    articles_to_scrape = [article for article in articles if not article.get('image_url')]
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_article = {executor.submit(scrape_image_from_article, article.get('url')): article for article in articles_to_scrape}
        for future in as_completed(future_to_article):
            article = future_to_article[future]
            try:
                scraped_image_url = future.result()
                if scraped_image_url:
                    article['image_url'] = scraped_image_url
            except Exception as exc:
                print(f"{article.get('title')} generated an exception: {exc}")
    
    # --- Batch Summarization ---
    descriptions = [article.get('description', '') or '' for article in articles]
    summaries = summarize_text(descriptions)
    for i, article in enumerate(articles):
        article['summary'] = summaries[i]

    news_data = {"trending": [], "featured": None, "related": [], "highlights": []}
    for article in articles:
        news_item = {
            "title": article.get('title'), 
            "summary": article.get('summary'), 
            "url": article.get('url'),
            "image_url": article.get('image_url')
        }
        if news_data['featured'] is None:
            news_data['featured'] = news_item
        elif len(news_data['trending']) < 5:
            news_data['trending'].append(news_item)
        elif len(news_data['related']) < 5:
            news_data['related'].append(news_item)
        elif len(news_data['highlights']) < 5:
            news_data['highlights'].append(news_item)
    
    end_time = time.time()
    print(f"\n--- Article processing took: {end_time - start_time:.2f} seconds ---")
            
    print("\nFinished processing all articles.")
    
    cached_news_data[cache_key] = news_data
    last_cache_time[cache_key] = time.time()
    
    return news_data