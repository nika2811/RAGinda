# src/product_finder/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Made path discovery more robust to run from any location
project_root = Path(__file__).resolve().parents[2]
load_dotenv(os.path.join(project_root, '.env'))

# --- Paths ---
OUTPUT_DIR = os.path.join(project_root, "output")
DATA_DIR = os.path.join(project_root, "data")
CONFIG_DIR = os.path.join(project_root, "config")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
SCRAPED_DATA_FILE = os.path.join(OUTPUT_DIR, "zoommer_scraping.json")
FAISS_INDEX_FILE = os.path.join(OUTPUT_DIR, "index.faiss")
FAISS_METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")
QUERY_EXPANSIONS_FILE = os.path.join(CONFIG_DIR, "query_expansions.json")

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
SEARCH_TOP_K = 10  # Increased to get more candidates for diversification
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score to include result
CATEGORY_BOOST_FACTOR = 1.2  # Boost score for category-matching products
TERM_MATCH_BOOST = 0.1  # Boost per matching query term in title
MAX_SEARCH_EXPANSION = 3  # Multiplier for initial search results before filtering

# --- Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Check for API key presence at startup
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY is not set. Category selection will be degraded.")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_GENERATION_CONFIG = {
    "temperature": 0.0,
    "response_mime_type": "application/json"
}

# --- Scraper ---
WEBSITE_BASE_URL = "https://zoommer.ge"
SCRAPER_MAX_PAGES_PER_CATEGORY = 3
SCRAPER_CONCURRENT_REQUESTS = 10
SCRAPER_PAGE_TIMEOUT = 60000
SCRAPER_SELECTOR_TIMEOUT = 10000

# --- Pipeline settings ---
PIPELINE_EMBEDDING_BATCH_SIZE = 32