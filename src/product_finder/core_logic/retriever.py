# src/product_finder/core_logic/retriever.py
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from .. import config

class HybridRetriever:
    def __init__(self, all_categories, model_name=config.RETRIEVER_MODEL):
        print(f"HybridRetriever-ის ინიციალიზაცია... მოდელის ჩატვირთვა: '{model_name}'")
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

        print("სემანტიკური ვექტორული ინდექსის შექმნა...")
        self.index = self.model.encode(texts_to_index, show_progress_bar=True)
        print("ვექტორული ინდექსი წარმატებით შეიქმნა.")

    def search(self, user_query, top_k=config.RETRIEVER_TOP_K):
        # ... (search method code remains unchanged)
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

        hybrid_scores = (semantic_scores * config.HYBRID_SEMANTIC_WEIGHT) + (keyword_scores * config.HYBRID_KEYWORD_WEIGHT)
        top_k_indices = np.argsort(hybrid_scores)[-top_k:][::-1]

        results = [self.all_subcategories[i] for i in top_k_indices if hybrid_scores[i] > config.HYBRID_SCORE_THRESHOLD]
        return [{k: v for k, v in res.items() if k != 'keywords'} for res in results]