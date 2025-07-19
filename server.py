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
import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from contextlib import asynccontextmanager

import faiss
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# Import existing modules
from src.product_finder import config
from src.product_finder.utils.data_io import load_categories_from_file
from src.product_finder.utils.async_utils import read_json_async
from src.product_finder.core_logic.retriever import HybridRetriever
from src.product_finder.core_logic.llm import find_category_with_gemini_rag
from src.product_finder.core_logic.embedding import build_embedding_text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for pre-loaded components
embedding_model: Optional[SentenceTransformer] = None
hybrid_retriever: Optional[HybridRetriever] = None
faiss_index: Optional[faiss.Index] = None
product_metadata: List[Dict[str, Any]] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager to handle startup and shutdown events.
    """
    # Startup
    global embedding_model, hybrid_retriever, faiss_index, product_metadata
    
    logger.info("Starting component initialization...")
    startup_start = time.time()
    
    try:
        # Step 1: Load embedding model
        logger.info(f"Loading embedding model: {config.EMBEDDER_MODEL}")
        embedding_model = await asyncio.to_thread(
            SentenceTransformer, 
            config.EMBEDDER_MODEL
        )
        logger.info("✅ Embedding model loaded")
        
        # Step 2: Load categories and initialize hybrid retriever
        logger.info("Loading categories and initializing HybridRetriever...")
        categories = await asyncio.to_thread(
            load_categories_from_file,
            config.CATEGORIES_FILE
        )
        
        if not categories:
            raise ValueError("Categories file is empty or invalid")
            
        hybrid_retriever = await asyncio.to_thread(
            HybridRetriever,
            categories
        )
        logger.info("✅ HybridRetriever initialized")
        
        # Step 3: Load FAISS index
        logger.info(f"Loading FAISS index from: {config.FAISS_INDEX_FILE}")
        if not Path(config.FAISS_INDEX_FILE).exists():
            raise FileNotFoundError(f"FAISS index file not found: {config.FAISS_INDEX_FILE}")
            
        faiss_index = await asyncio.to_thread(
            faiss.read_index,
            config.FAISS_INDEX_FILE
        )
        logger.info(f"✅ FAISS index loaded with {faiss_index.ntotal} vectors")
        
        # Step 4: Load product metadata
        logger.info(f"Loading product metadata from: {config.FAISS_METADATA_FILE}")
        if not Path(config.FAISS_METADATA_FILE).exists():
            raise FileNotFoundError(f"Metadata file not found: {config.FAISS_METADATA_FILE}")
            
        product_metadata = await read_json_async(config.FAISS_METADATA_FILE)
        logger.info(f"✅ Product metadata loaded: {len(product_metadata)} products")
        
        # Validate consistency
        if len(product_metadata) != faiss_index.ntotal:
            logger.warning(
                f"Metadata count ({len(product_metadata)}) doesn't match "
                f"index size ({faiss_index.ntotal})"
            )
        
        startup_time = time.time() - startup_start
        logger.info(f"🚀 All components loaded successfully in {startup_time:.2f}s")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"❌ Component initialization failed: {str(e)}")
        raise RuntimeError(f"Failed to initialize server components: {str(e)}")
    
    # Shutdown
    logger.info("Shutting down server...")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="AI-Powered Product Search API",
    description="High-performance semantic search API for e-commerce products",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class SearchRequest(BaseModel):
    """Request model for product search endpoint."""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=500,
        description="User's search query"
    )
    max_results: Optional[int] = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of results to return"
    )


class ProductResult(BaseModel):
    """Individual product result model."""
    title: str
    price: str
    category: str
    description: Optional[str] = None
    specs: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    similarity_score: Optional[float] = None


class CategoryResult(BaseModel):
    """Category selection result model."""
    category_name: str
    subcategory_name: str
    subcategory_url: str
    confidence: Optional[float] = None


class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    query: str
    selected_category: CategoryResult
    products: List[ProductResult]
    total_results: int
    response_time_ms: float
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    components: Dict[str, str]


# In-memory search functions
async def search_faiss_index(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Perform optimized semantic search against the pre-loaded FAISS index.
    
    Features:
    - Query preprocessing and expansion
    - Similarity threshold filtering
    - Score normalization
    - Result diversification
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of matching products with similarity scores
    """
    if not embedding_model or not faiss_index or not product_metadata:
        raise HTTPException(
            status_code=503, 
            detail="Search components not properly initialized"
        )
    
    # Step 1: Query preprocessing and expansion
    processed_query = preprocess_query(query)
    
    # Step 2: Generate query embedding with proper prefix
    query_text = config.EMBEDDER_QUERY_PREFIX + processed_query
    query_vector = await asyncio.to_thread(
        embedding_model.encode, 
        [query_text],
        convert_to_numpy=True,
        normalize_embeddings=True  # L2 normalization for better similarity
    )
    query_vector = query_vector.astype('float32').reshape(1, -1)
    
    # Step 3: Search with expanded results for filtering
    search_k = min(max_results * 3, len(product_metadata))  # Get more for filtering
    distances, indices = await asyncio.to_thread(
        faiss_index.search,
        query_vector,
        search_k
    )
    
    # Step 4: Build results with normalized similarity scores
    results = []
    min_distance = min(distances[0]) if len(distances[0]) > 0 else 0
    max_distance = max(distances[0]) if len(distances[0]) > 0 else 1
    
    for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
        if idx >= 0 and idx < len(product_metadata):
            product = product_metadata[idx].copy()
            
            # Enhanced similarity calculation
            if max_distance > min_distance:
                # Normalize distance to 0-1 range, then convert to similarity
                normalized_distance = (distance - min_distance) / (max_distance - min_distance)
                similarity = 1.0 - normalized_distance
            else:
                similarity = 1.0
            
            # Apply similarity threshold
            if similarity >= config.HYBRID_SCORE_THRESHOLD:
                product['similarity_score'] = round(similarity, 4)
                product['search_rank'] = i + 1
                results.append(product)
    
    # Step 5: Apply result diversification and ranking
    results = diversify_results(results, query)
    
    # Step 6: Return top results
    return results[:max_results]


def preprocess_query(query: str) -> str:
    """
    Preprocess and expand query for better search results.
    
    Args:
        query: Raw user query
        
    Returns:
        Processed query string
    """
    # Basic cleaning
    query = query.strip().lower()
    
    # Georgian/English synonym expansion
    query_expansions = {
        'ლეპტოპი': 'ლეპტოპი laptop კომპიუტერი',
        'ტელეფონი': 'ტელეფონი smartphone მობილური',
        'მონიტორი': 'მონიტორი monitor ეკრანი',
        'gaming': 'gaming გეიმინგი თამაშების',
        'smart': 'smart სმარტ ჭკვიანი',
        'audio': 'audio აუდიო ხმა',
        'camera': 'camera კამერა ფოტო'
    }
    
    for term, expansion in query_expansions.items():
        if term in query:
            query = expansion
            break
    
    return query


def diversify_results(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """
    Apply result diversification to avoid showing too many similar products.
    
    Args:
        results: List of search results
        query: Original query for context
        
    Returns:
        Diversified results list
    """
    if len(results) <= 3:
        return results
    
    diversified = []
    seen_categories = set()
    seen_brands = set()
    
    # First pass: one from each category/brand
    for result in results:
        category = result.get('category', '').lower()
        title = result.get('title', '').lower()
        
        # Extract potential brand from title (first word often)
        brand = title.split()[0] if title else ''
        
        if category not in seen_categories or brand not in seen_brands:
            diversified.append(result)
            seen_categories.add(category)
            seen_brands.add(brand)
            
            if len(diversified) >= 3:
                break
    
    # Second pass: fill remaining slots with best scores
    remaining_slots = len(results) - len(diversified)
    for result in results:
        if result not in diversified and remaining_slots > 0:
            diversified.append(result)
            remaining_slots -= 1
    
    return diversified


def fuse_search_results(
    vector_results: List[Dict[str, Any]], 
    selected_category: Dict[str, Any],
    query: str,
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    Fuse vector search results with category-aware ranking.
    
    Args:
        vector_results: Results from FAISS vector search
        selected_category: Best matching category from LLM
        query: Original search query
        max_results: Maximum results to return
        
    Returns:
        Fused and ranked results list
    """
    if not vector_results:
        return []
    
    # Step 1: Category boost for relevant products
    category_name = selected_category.get('subcategory_name', '').lower()
    
    enhanced_results = []
    for result in vector_results:
        result_copy = result.copy()
        base_score = result_copy.get('similarity_score', 0.0)
        
        # Apply category boost
        product_category = result_copy.get('category', '').lower()
        if category_name and category_name in product_category:
            result_copy['similarity_score'] = min(1.0, base_score * 1.2)  # 20% boost
            result_copy['category_match'] = True
        else:
            result_copy['category_match'] = False
        
        # Apply query term boost
        title = result_copy.get('title', '').lower()
        query_terms = query.lower().split()
        term_matches = sum(1 for term in query_terms if term in title)
        if term_matches > 0:
            term_boost = 1 + (term_matches * 0.1)  # 10% per matching term
            result_copy['similarity_score'] = min(1.0, result_copy['similarity_score'] * term_boost)
        
        enhanced_results.append(result_copy)
    
    # Step 2: Sort by enhanced similarity score
    enhanced_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
    
    # Step 3: Apply final diversification
    final_results = diversify_results(enhanced_results, query)
    
    return final_results[:max_results]


async def find_best_category(query: str) -> Dict[str, Any]:
    """
    Find the best matching category using hybrid retrieval + LLM refinement.
    
    Args:
        query: User's search query
        
    Returns:
        Dictionary with selected category information
    """
    if not hybrid_retriever:
        raise HTTPException(
            status_code=503,
            detail="Category retriever not initialized"
        )
    
    # Step 1: Get candidate categories using hybrid retriever
    retrieved_categories = await asyncio.to_thread(
        hybrid_retriever.search,
        query,
        top_k=config.RETRIEVER_TOP_K
    )
    
    if not retrieved_categories:
        raise HTTPException(
            status_code=404,
            detail="No relevant categories found for the query"
        )
    
    # Step 2: Use LLM to refine category selection
    final_choice = await asyncio.to_thread(
        find_category_with_gemini_rag,
        query,
        retrieved_categories
    )
    
    if "error" in final_choice:
        raise HTTPException(
            status_code=404,
            detail=f"Category selection failed: {final_choice['error']}"
        )
    
    # Handle different response formats from LLM
    if isinstance(final_choice, list) and len(final_choice) > 0:
        final_choice = final_choice[0]
    
    if not isinstance(final_choice, dict) or 'subcategory_name' not in final_choice:
        raise HTTPException(
            status_code=500,
            detail="Invalid category selection response from LLM"
        )
    
    return final_choice


# API Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify all components are loaded."""
    from datetime import datetime
    
    components = {
        "embedding_model": "loaded" if embedding_model else "not_loaded",
        "hybrid_retriever": "loaded" if hybrid_retriever else "not_loaded", 
        "faiss_index": "loaded" if faiss_index else "not_loaded",
        "product_metadata": f"{len(product_metadata)} products" if product_metadata else "not_loaded"
    }
    
    all_loaded = all(status != "not_loaded" for status in components.values())
    
    return HealthResponse(
        status="healthy" if all_loaded else "unhealthy",
        timestamp=datetime.now().isoformat(),
        components=components
    )


@app.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """
    Main search endpoint for finding products based on user query.
    
    This endpoint performs the following steps:
    1. Find the best matching category using hybrid retrieval + LLM
    2. Search for similar products in the FAISS index
    3. Return structured results with category and product matches
    """
    start_time = time.time()
    from datetime import datetime
    
    try:
        # Step 1: Find best matching category (CPU-bound, use thread pool)
        logger.info(f"Processing search query: {request.query}")
        
        category_task = asyncio.create_task(find_best_category(request.query))
        search_task = asyncio.create_task(search_faiss_index(request.query, request.max_results))
        
        # Run category finding and product search in parallel
        selected_category, product_results = await asyncio.gather(
            category_task,
            search_task
        )
        
        # Apply hybrid result fusion and ranking
        product_results = fuse_search_results(
            vector_results=product_results,
            selected_category=selected_category,
            query=request.query,
            max_results=request.max_results
        )
        
        # Build response
        products = []
        for product in product_results:
            # Ensure price is always a string
            price_value = product.get('price', '')
            if isinstance(price_value, (int, float)):
                price_value = str(price_value)
            
            products.append(ProductResult(
                title=product.get('title', ''),
                price=price_value,
                category=product.get('category', ''),
                description=product.get('description'),
                specs=product.get('specs'),
                url=product.get('url'),
                similarity_score=product.get('similarity_score')
            ))
        
        category_result = CategoryResult(
            category_name=selected_category.get('category_name', ''),
            subcategory_name=selected_category.get('subcategory_name', ''),
            subcategory_url=selected_category.get('subcategory_url', '')
        )
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        response = SearchResponse(
            query=request.query,
            selected_category=category_result,
            products=products,
            total_results=len(products),
            response_time_ms=round(response_time, 2),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Search completed in {response_time:.2f}ms for query: {request.query}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for query '{request.query}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during search: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Get basic statistics about the loaded data."""
    return {
        "total_products": len(product_metadata),
        "index_dimension": faiss_index.d if faiss_index else 0,
        "index_size": faiss_index.ntotal if faiss_index else 0,
        "model_name": config.EMBEDDER_MODEL,
        "retriever_model": config.RETRIEVER_MODEL
    }


if __name__ == "__main__":
    """
    Development server entry point.
    
    For production, use:
        uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
    """
    try:
        import uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
    except ImportError:
        print("❌ uvicorn not installed. Please run: pip install uvicorn[standard]")
        print("Or use: python -m uvicorn server:app --host 0.0.0.0 --port 8000")
