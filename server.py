#!/usr/bin/env python3
"""
Online Serving API (server.py)

High-performance FastAPI server for real-time product search.
Provides millisecond-level response times by leveraging pre-built indexes.

Features:
- FastAPI with async/await for high concurrency
- Pre-loaded models and indexes in memory
- Thread pool execution for CPU-bound tasks
- Structured request/response models with Pydantic
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import faiss
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from src.product_finder import config
from src.product_finder.utils.data_io import load_categories_from_file, load_products
from src.product_finder.utils.async_utils import read_json_async
from src.product_finder.core_logic.retriever import HybridRetriever
# REFACTOR: Import the new centralized search service
from src.product_finder.core_logic.search_service import SearchService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# REFACTOR: Use a dictionary to hold application state, which is cleaner than globals.
app_state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager to load all necessary components into app_state on startup.
    """
    logger.info("🚀 Server starting up... Initializing components.")
    startup_start = time.time()
    
    try:
        # Load all components in parallel where possible
        model_task = asyncio.to_thread(SentenceTransformer, config.EMBEDDER_MODEL)
        categories_task = asyncio.to_thread(load_categories_from_file, config.CATEGORIES_FILE)
        index_task = asyncio.to_thread(faiss.read_index, config.FAISS_INDEX_FILE)
        metadata_task = read_json_async(config.FAISS_METADATA_FILE)

        embedding_model, categories, faiss_index, product_metadata = await asyncio.gather(
            model_task, categories_task, index_task, metadata_task
        )
        
        if not all([embedding_model, categories, faiss_index, product_metadata]):
            raise RuntimeError("One or more essential components failed to load.")

        # Initialize retriever (depends on categories)
        hybrid_retriever = HybridRetriever(categories)

        # REFACTOR: Initialize the single SearchService with all loaded components
        app_state["search_service"] = SearchService(
            embedding_model=embedding_model,
            faiss_index=faiss_index,
            product_metadata=product_metadata,
            hybrid_retriever=hybrid_retriever
        )
        app_state["product_count"] = len(product_metadata)
        
        startup_time = time.time() - startup_start
        logger.info(f"✅ All components loaded successfully in {startup_time:.2f}s. Server is ready.")
        
        yield  # Application runs here
        
    except FileNotFoundError as e:
        logger.error(f"❌ CRITICAL: A required file was not found: {e}. The application cannot start.")
        raise RuntimeError(f"Missing file: {e}") from e
    except Exception as e:
        logger.error(f"❌ CRITICAL: Component initialization failed: {e}")
        raise RuntimeError("Failed to initialize server components.") from e
    
    # Shutdown
    logger.info("...Server shutting down.")
    app_state.clear()


app = FastAPI(
    title="AI-Powered Product Search API",
    description="High-performance semantic search API for e-commerce products",
    version="1.1.0",  # REFACTOR: Version bump
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models (unchanged from original, but kept here for completeness)
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="User's search query")
    max_results: int = Field(default=5, ge=1, le=50, description="Maximum number of results to return")

class ProductResult(BaseModel):
    title: str
    price: str
    category: str
    url: Optional[str] = None
    final_score: Optional[float] = Field(None, alias="similarity_score")  # Use alias for frontend compatibility

class CategoryResult(BaseModel):
    category_name: str
    subcategory_name: str
    subcategory_url: str

class SearchResponse(BaseModel):
    query: str
    selected_category: Optional[CategoryResult] = None
    products: List[ProductResult]
    total_results: int
    response_time_ms: float
    timestamp: str

# --- API Endpoints ---

@app.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """
    Main search endpoint. Delegates the entire logic to the SearchService.
    """
    start_time = time.time()
    
    # REFACTOR: The entire logic is now in one clean call.
    search_service: Optional[SearchService] = app_state.get("search_service")
    if not search_service:
        raise HTTPException(status_code=503, detail="Search service is not available.")
        
    try:
        search_results = await search_service.search(request.query, request.max_results)
        
        response_time = (time.time() - start_time) * 1000
        
        response = SearchResponse(
            query=request.query,
            selected_category=search_results["selected_category"],
            products=search_results["products"],
            total_results=len(search_results["products"]),
            response_time_ms=round(response_time, 2),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Search for '{request.query}' completed in {response_time:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Search failed for query '{request.query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred during the search.")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    search_service = app_state.get("search_service")
    status = "healthy" if search_service else "unhealthy"
    return {"status": status, "timestamp": datetime.now().isoformat(), "total_products": app_state.get("product_count", 0)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
