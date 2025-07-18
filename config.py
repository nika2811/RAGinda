import os
from dotenv import load_dotenv

# --- General ---
# Load environment variables from .env file for secrets like API keys
load_dotenv()

# --- Paths ---
# Directory for all generated output
OUTPUT_DIR = "output"
# Input data
CATEGORIES_FILE = "categories.json"
# Scraped data from Zoommer
SCRAPED_DATA_FILE = os.path.join(OUTPUT_DIR, "zoommer_scraping.json")
# FAISS vector index and its corresponding metadata
FAISS_INDEX_FILE = os.path.join(OUTPUT_DIR, "index.faiss")
FAISS_METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")

# --- Models ---
# Model for creating product embeddings (in embedder.py)
# 'intfloat/multilingual-e5-small' is a good choice for multilingual passage/query tasks
EMBEDDER_MODEL = "intfloat/multilingual-e5-small"
# Model-specific prefixes required by E5 models
EMBEDDER_PASSAGE_PREFIX = "passage: "
EMBEDDER_QUERY_PREFIX = "query: "

# Model for retrieving categories (in retriever.py)
# 'paraphrase-multilingual-MiniLM-L12-v2' is fast and effective for semantic similarity
RETRIEVER_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'


# --- Retriever & RAG Parameters ---
# Number of initial candidates to retrieve for the RAG step
RETRIEVER_TOP_K = 3
# Weights for combining semantic and keyword scores in the hybrid retriever
HYBRID_SEMANTIC_WEIGHT = 0.6
HYBRID_KEYWORD_WEIGHT = 0.4
# Minimum score for a result to be considered a match
HYBRID_SCORE_THRESHOLD = 0.2

# --- Semantic Search (FAISS) ---
# Number of similar products to return from the final search
SEARCH_TOP_K = 5

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_GENERATION_CONFIG = {
    "temperature": 0.0,
    "responseMimeType": "application/json"
}

# --- Scraper ---
WEBSITE_BASE_URL = "https://zoommer.ge"
# Number of pages to scrape per category. Set higher for full scraping.
SCRAPER_MAX_PAGES_PER_CATEGORY = 1
# Number of concurrent product detail pages to scrape
SCRAPER_CONCURRENT_REQUESTS = 10
# Timeouts in milliseconds
SCRAPER_PAGE_TIMEOUT = 60000
SCRAPER_SELECTOR_TIMEOUT = 10000