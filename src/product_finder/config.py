# src/product_finder/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
# This needs to find the .env file from within the src directory
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# --- Paths ---
OUTPUT_DIR = os.path.join(project_root, "output")
DATA_DIR = os.path.join(project_root, "data")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
SCRAPED_DATA_FILE = os.path.join(OUTPUT_DIR, "zoommer_scraping.json")
FAISS_INDEX_FILE = os.path.join(OUTPUT_DIR, "index.faiss")
FAISS_METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")

# --- Models ---
EMBEDDER_MODEL = "intfloat/multilingual-e5-small"
EMBEDDER_PASSAGE_PREFIX = "passage: "
EMBEDDER_QUERY_PREFIX = "query: "
RETRIEVER_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'

# --- Retriever & RAG Parameters ---
RETRIEVER_TOP_K = 3
HYBRID_SEMANTIC_WEIGHT = 0.6
HYBRID_KEYWORD_WEIGHT = 0.4
HYBRID_SCORE_THRESHOLD = 0.2

# --- Semantic Search (FAISS) ---
SEARCH_TOP_K = 5

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_GENERATION_CONFIG = {
    "temperature": 0.0,
    "response_mime_type": "application/json"
}

# --- Scraper ---
WEBSITE_BASE_URL = "https://zoommer.ge"
SCRAPER_MAX_PAGES_PER_CATEGORY = 1
SCRAPER_CONCURRENT_REQUESTS = 10
SCRAPER_PAGE_TIMEOUT = 60000
SCRAPER_SELECTOR_TIMEOUT = 10000