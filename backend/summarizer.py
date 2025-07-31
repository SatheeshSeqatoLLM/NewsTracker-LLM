from transformers import pipeline
from newsapi import NewsApiClient
import requests
from bs4 import BeautifulSoup
import time
import os

# --- Caching ---
cached_news_data = {}
last_cache_time = {}
CACHE_DURATION = 60  # 1 minute
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
        # This is a very basic attempt and might need refinement for specific sites
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

def fetch_news_headlines(topic=None, country=None):
    """Fetches top headlines using NewsAPI."""
    print(f"Fetching headlines from NewsAPI for topic: {topic}, country: {country}")
    articles = []
    
    # Map country codes to full names for better search queries
    country_names = {
        "us": "United States", "gb": "United Kingdom", "ca": "Canada", "au": "Australia", "in": "India",
        "de": "Germany", "fr": "France", "jp": "Japan", "cn": "China", "ru": "Russia", "br": "Brazil"
    }

    try:
        params = {
            'language': 'en',
            'page_size': 20
        }
        
        # If a topic is provided, use it as the main query.
        if topic:
            params['q'] = topic
            # You can still filter by country if the API plan supports it.
            if country:
                params['country'] = country
        # If only a country is provided, use the country's name as the search query.
        # This is the workaround for free plans that don't allow country + category.
        elif country:
            params['q'] = country_names.get(country, country) # Fallback to code if name not found

        # If neither topic nor country is provided, get general top headlines.
        # This requires removing 'q' to avoid an empty parameter.
        if 'q' not in params:
             top_headlines = newsapi.get_top_headlines(language='en', page_size=20)
        else:
             top_headlines = newsapi.get_top_headlines(**params)

        if top_headlines and top_headlines['articles']:
            for article in top_headlines['articles']:
                print(f"Raw article from NewsAPI: {article}")
                articles.append({
                    'title': article.get('title'),
                    'url': article.get('url'),
                    'description': article.get('description'), # NewsAPI provides a description
                    'image_url': article.get('urlToImage')
                })
        print(f"Fetched {len(articles)} headlines from NewsAPI.")
    except Exception as e:
        print(f"Could not fetch headlines from NewsAPI: {e}")
    return articles

def summarize_text(text):
    """Summarizes a given text using our AI model."""
    if not text: return ""
    truncated_text = text[:2000]
    input_length = len(truncated_text.split())
    max_len = min(150, input_length - 1)
    min_len = min(30, max_len // 2)
    if max_len <= min_len:
        return truncated_text
    try:
        summary = summarizer(truncated_text, max_length=max_len, min_length=min_len, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return ""

def get_news_data(topic=None, country=None):
    """Tracks news, processes, and summarizes it using a cache."""
    global cached_news_data, last_cache_time
    
    cache_key = f"{topic or 'general'}_{country or 'all'}"

    if cache_key in cached_news_data and (time.time() - last_cache_time.get(cache_key, 0) < CACHE_DURATION):
        print(f"\n--- Serving from Cache for key: {cache_key} ---")
        return cached_news_data[cache_key]

    print(f"\n--- Tracking new data from NewsAPI for topic: {topic or 'general'}, country: {country or 'all'} ---")
    
    articles = fetch_news_headlines(topic=topic, country=country)
    print(f"Number of articles fetched: {len(articles)}")

    if not articles:
        print("No articles found from NewsAPI.")
        return {"trending": [], "featured": None, "related": [], "highlights": []}

    news_data = {"trending": [], "featured": None, "related": [], "highlights": []}
    
    start_time = time.time()
    for i, article_info in enumerate(articles):
        if i >= 20: break # Limit to 20 articles for display
        
        print(f"\nProcessing article {i+1}: {article_info['title']}")
        
        # Use the description provided by NewsAPI for summarization
        summary = summarize_text(article_info.get('description', ''))
        print(f"Summary length: {len(summary) if summary else 0}")
        
        news_item = {
            "title": article_info.get('title'), 
            "summary": summary, 
            "url": article_info.get('url'),
            "image_url": article_info.get('urlToImage')
        }

        # If NewsAPI didn't provide an image, try to scrape it from the article URL
        if not news_item['image_url']:
            scraped_image = scrape_image_from_article(news_item['url'])
            if scraped_image:
                news_item['image_url'] = scraped_image

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