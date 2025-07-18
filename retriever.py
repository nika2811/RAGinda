# retriever.py

import os
import json
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import config # Import the configuration file

# --- Configuration ---
# Removed hardcoded constants, they are now in config.py

def load_categories_from_file(path):
    try:
        # Use config for file path
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Categories file not found at '{path}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{path}'")
        return None

class HybridRetriever:
    # Use config for default model name
    def __init__(self, all_categories, model_name=config.RETRIEVER_MODEL):
        print(f"Initializing HybridRetriever... Loading '{model_name}' model.")
        self.model = SentenceTransformer(model_name)
        self.all_subcategories = []
        texts_to_index = []

        for category in all_categories:
            for subcategory in category['subcategories']:
                combined_text = f"{category['category_name']} {subcategory['subcategory_name']} {' '.join(subcategory.get('keywords', []))}"
                texts_to_index.append(combined_text)
                self.all_subcategories.append({
                    "category_name": category['category_name'],
                    "subcategory_name": subcategory['subcategory_name'],
                    "subcategory_url": subcategory['subcategory_url'],
                    "keywords": set(kw.lower() for kw in subcategory.get('keywords', []))
                })

        print("Creating semantic vector index...")
        self.index = self.model.encode(texts_to_index, show_progress_bar=True)
        print("Vector index created successfully.")

    # Use config for default top_k value
    def search(self, user_query, top_k=config.RETRIEVER_TOP_K):
        if not user_query:
            return []

        query_lower = user_query.lower()
        query_embedding = self.model.encode([query_lower])
        semantic_scores = cosine_similarity(query_embedding, self.index)[0]

        keyword_scores = np.zeros(len(self.all_subcategories))
        for i, subcat in enumerate(self.all_subcategories):
            for keyword in subcat['keywords']:
                if keyword in query_lower:
                    keyword_scores[i] = 1.0
                    break

        # Use config for hybrid scoring weights and threshold
        hybrid_scores = (semantic_scores * config.HYBRID_SEMANTIC_WEIGHT) + (keyword_scores * config.HYBRID_KEYWORD_WEIGHT)
        top_k_indices = np.argsort(hybrid_scores)[-top_k:][::-1]

        results = [self.all_subcategories[i] for i in top_k_indices if hybrid_scores[i] > config.HYBRID_SCORE_THRESHOLD]
        return [{k: v for k, v in res.items() if k != 'keywords'} for res in results]

def find_category_with_gemini_rag(user_query, retrieved_context):
    # Use config for Gemini API key
    if not config.GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not set in config.py or .env file."}

    if not retrieved_context:
        return {
            "candidates": [{"content": {"parts": [{"json": {"error": "No suitable category found by retriever."}}]}}]}

    context_json_string = json.dumps(retrieved_context, indent=2, ensure_ascii=False)

    # FIXED: Escaped the curly braces in the JSON example with double braces {{ and }}
    prompt = f"""
    You are an expert classification system. Your task is to analyze a user's request and select the single most appropriate subcategory from a pre-filtered list of relevant options.

    Here is the pre-filtered list of the MOST RELEVANT subcategories based on a hybrid (semantic + keyword) search. You MUST choose from this list only.
    ```json
    {context_json_string}
    ```

    User's request: "{user_query}"

    Instructions:
    1. From the JSON list above, identify the SINGLE BEST matching subcategory for the user's request.
    2. Respond ONLY with a JSON object copied directly from the list.
    3. If even among these options none are a good fit, respond with: `{{"error": "No suitable category found."}}`
    """

    # Use config for Gemini payload
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": config.GEMINI_GENERATION_CONFIG
    }
    headers = {'Content-Type': 'application/json'}

    try:
        # Use config for Gemini API endpoint and key
        response = requests.post(f"{config.GEMINI_API_ENDPOINT}?key={config.GEMINI_API_KEY}", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}", "details": str(e)}