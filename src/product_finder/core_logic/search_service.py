# src/product_finder/core_logic/search_service.py
import asyncio
import json
from typing import List, Dict, Any, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .. import config
from .llm import find_category_with_gemini_rag
from .retriever import HybridRetriever

# REFACTOR: This new service class encapsulates all search-related logic,
# decoupling it from the FastAPI server layer.

class SearchService:
    """
    Handles the entire search process, from query preprocessing to result fusion.
    """

    def __init__(
        self,
        embedding_model: SentenceTransformer,
        faiss_index: faiss.Index,
        product_metadata: List[Dict[str, Any]],
        hybrid_retriever: HybridRetriever,
    ):
        """
        Initializes the service with pre-loaded components.
        This follows the Dependency Injection pattern.
        """
        self.embedding_model = embedding_model
        self.faiss_index = faiss_index
        self.product_metadata = product_metadata
        self.hybrid_retriever = hybrid_retriever
        self._load_query_expansions()

    def _load_query_expansions(self):
        """Loads query expansion synonyms from a config file."""
        try:
            with open(config.QUERY_EXPANSIONS_FILE, 'r', encoding='utf-8') as f:
                self.query_expansions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.query_expansions = {}
            print(f"Warning: Query expansion file not found or invalid at {config.QUERY_EXPANSIONS_FILE}")

    def _preprocess_query(self, query: str) -> str:
        """Preprocesses and expands the query."""
        query_lower = query.strip().lower()
        for term, expansion in self.query_expansions.items():
            if term in query_lower:
                return expansion  # Return first match for simplicity
        return query_lower

    async def _search_faiss_index(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Performs the raw vector search."""
        processed_query = self._preprocess_query(query)
        query_text = config.EMBEDDER_QUERY_PREFIX + processed_query
        
        query_vector = await asyncio.to_thread(
            self.embedding_model.encode,
            [query_text],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        query_vector = query_vector.astype('float32').reshape(1, -1)

        search_k = min(top_k * config.MAX_SEARCH_EXPANSION, self.faiss_index.ntotal)
        distances, indices = await asyncio.to_thread(
            self.faiss_index.search, query_vector, search_k
        )

        results = []
        if len(indices[0]) == 0:
            return []

        min_dist, max_dist = np.min(distances[0]), np.max(distances[0])

        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= 0:
                product = self.product_metadata[idx].copy()
                similarity = 1.0 - ((dist - min_dist) / (max_dist - min_dist)) if max_dist > min_dist else 1.0
                if similarity >= config.SIMILARITY_THRESHOLD:
                    product['similarity_score'] = round(similarity, 4)
                    product['search_rank'] = i + 1
                    results.append(product)
        return results

    async def _find_best_category(self, query: str) -> Optional[Dict[str, Any]]:
        """Finds the best category using hybrid retrieval and LLM."""
        retrieved_categories = await asyncio.to_thread(
            self.hybrid_retriever.search, query, top_k=config.RETRIEVER_TOP_K
        )
        if not retrieved_categories:
            return None

        if not config.GEMINI_API_KEY:
             # Fallback: if no API key, return the top retrieved category
            return retrieved_categories[0]

        final_choice = await asyncio.to_thread(
            find_category_with_gemini_rag, query, retrieved_categories
        )

        if isinstance(final_choice, list) and final_choice:
            final_choice = final_choice[0]
        
        if isinstance(final_choice, dict) and 'subcategory_name' in final_choice:
            return final_choice
        
        # Fallback if LLM fails
        return retrieved_categories[0]

    def _fuse_and_rerank_results(
        self, vector_results: List[Dict[str, Any]], selected_category: Optional[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Applies boosting and diversification to the results."""
        enhanced_results = []
        category_name = selected_category['subcategory_name'].lower() if selected_category else ""
        query_terms = query.lower().split()

        for res in vector_results:
            score = res.get('similarity_score', 0.0)
            
            # Category boost
            if category_name and category_name in res.get('category', '').lower():
                score *= config.CATEGORY_BOOST_FACTOR
                res['category_match'] = True

            # Term match boost
            term_matches = sum(1 for term in query_terms if term in res.get('title', '').lower())
            if term_matches > 0:
                score *= (1 + (term_matches * config.TERM_MATCH_BOOST))
            
            res['final_score'] = min(1.0, score)
            enhanced_results.append(res)
            
        enhanced_results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        return self._diversify_results(enhanced_results)

    def _diversify_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple diversification based on product category to avoid visual clutter."""
        if len(results) <= 3:
            return results
        
        diversified = []
        seen_categories = set()
        for res in results:
            category = res.get('category')
            if category not in seen_categories:
                diversified.append(res)
                seen_categories.add(category)
        
        # Fill with remaining best results if diversification reduced the list too much
        for res in results:
            if res not in diversified:
                diversified.append(res)
                
        return diversified

    async def search(self, query: str, max_results: int) -> Dict[str, Any]:
        """
        Executes the full parallel search and fusion pipeline.
        """
        # Run category selection and vector search in parallel
        category_task = asyncio.create_task(self._find_best_category(query))
        search_task = asyncio.create_task(self._search_faiss_index(query, top_k=config.SEARCH_TOP_K))

        selected_category, vector_results = await asyncio.gather(category_task, search_task)

        # Rerank and finalize results
        final_products = self._fuse_and_rerank_results(vector_results, selected_category, query)

        return {
            "selected_category": selected_category,
            "products": final_products[:max_results]
        }
