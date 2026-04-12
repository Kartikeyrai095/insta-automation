"""
Curated RSS feed sources for news matching.
All sources are free, reliable, and publicly accessible.
"""

NEWS_FEEDS = [
    {
        "name": "Google News India",
        "url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
        "category": "general",
        "priority": 1,
    },
    {
        "name": "BBC News",
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "category": "general",
        "priority": 2,
    },
    {
        "name": "BBC News Technology",
        "url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "category": "tech",
        "priority": 3,
    },
    {
        "name": "Reuters World",
        "url": "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
        "category": "general",
        "priority": 2,
    },
    {
        "name": "NDTV India",
        "url": "https://feeds.feedburner.com/ndtvnews-top-stories",
        "category": "india",
        "priority": 1,
    },
    {
        "name": "Times of India",
        "url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "category": "india",
        "priority": 1,
    },
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "tech",
        "priority": 3,
    },
    {
        "name": "ESPN Sports",
        "url": "https://www.espn.com/espn/rss/news",
        "category": "sports",
        "priority": 4,
    },
    {
        "name": "Entertainment Weekly",
        "url": "https://ew.com/feed/",
        "category": "entertainment",
        "priority": 4,
    },
]

# Whitelisted domains for verified sources
VERIFIED_DOMAINS = [
    "bbc.com", "bbc.co.uk",
    "reuters.com",
    "ndtv.com",
    "timesofindia.indiatimes.com",
    "techcrunch.com",
    "espn.com",
    "theguardian.com",
    "cnn.com",
    "news.google.com",
    "ew.com",
    "hindustantimes.com",
    "indianexpress.com",
]
