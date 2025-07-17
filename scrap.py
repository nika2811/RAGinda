import os
import json
import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- კონფიგურაცია ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
CATEGORIES_FILE_PATH = "categories.json"
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'


def load_categories_from_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Categories file not found at '{path}'")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{path}'")
        return None

# --- ნაბიჯი 2: Production-Grade HYBRID Retriever (FIXED) ---
class HybridRetriever:
    """
    გამართული ჰიბრიდული საძიებო სისტემა, რომელიც სწორად აერთიანებს
    ვექტორულ (სემანტიკურ) და საკვანძო სიტყვების (keyword) ძებნას.
    """
    def __init__(self, all_categories, model_name=EMBEDDING_MODEL_NAME):
        print(f"Initializing HybridRetriever... Loading '{model_name}' model.")
        self.model = SentenceTransformer(model_name)
        self.all_subcategories = []
        texts_to_index = []
        
        for category in all_categories:
            for subcategory in category['subcategories']:
                # ტექსტი ინდექსაციისთვის (სემანტიკური ნაწილი)
                combined_text = f"{category['category_name']} {subcategory['subcategory_name']} {' '.join(subcategory.get('keywords', []))}"
                texts_to_index.append(combined_text)
                
                # ვინახავთ მონაცემებს და საკვანძო სიტყვებს keyword search-ისთვის
                self.all_subcategories.append({
                    "category_name": category['category_name'],
                    "subcategory_name": subcategory['subcategory_name'],
                    "subcategory_url": subcategory['subcategory_url'],
                    "keywords": set(kw.lower() for kw in subcategory.get('keywords', []))
                })
        
        print("Creating semantic vector index...")
        self.index = self.model.encode(texts_to_index, show_progress_bar=True)
        print("Vector index created successfully.")

    def search(self, user_query, top_k=3):
        if not user_query:
            return []
        
        query_lower = user_query.lower()

        # --- ეტაპი 1: სემანტიკური ქულების გამოთვლა ---
        query_embedding = self.model.encode([query_lower])
        semantic_scores = cosine_similarity(query_embedding, self.index)[0]

        # --- ეტაპი 2: საკვანძო სიტყვების ქულების გამოთვლა (გასწორებული ლოგიკა) ---
        keyword_scores = np.zeros(len(self.all_subcategories))
        for i, subcat in enumerate(self.all_subcategories):
            # ვამოწმებთ, თუ რომელიმე საკვანძო სიტყვა (რომელიც შეიძლება ფრაზა იყოს)
            # არის მომხმარებლის მოთხოვნის ტექსტის ნაწილი.
            for keyword in subcat['keywords']:
                if keyword in query_lower:
                    keyword_scores[i] = 1.0  # ვანიჭებთ მაქსიმალურ ბონუსს
                    break  # ერთი დამთხვევაც საკმარისია ბონუსისთვის

        # --- ეტაპი 3: ქულების გაერთიანება (ჰიბრიდული ქულა) ---
        # ვაძლევთ წონებს: 60% სემანტიკურ ძებნას, 40% საკვანძო სიტყვების ბონუსს
        hybrid_scores = (semantic_scores * 0.6) + (keyword_scores * 0.4)
        
        top_k_indices = np.argsort(hybrid_scores)[-top_k:][::-1]
        
        results = [self.all_subcategories[i] for i in top_k_indices if hybrid_scores[i] > 0.2]
        
        # დავაბრუნოთ სუფთა ლექსიკონი, 'keywords'-ის გარეშე
        return [{k: v for k, v in res.items() if k != 'keywords'} for res in results]

# --- ნაბიჯი 3: Generator (API გამოძახება) ---
def find_category_with_gemini_rag(user_query, retrieved_context):
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not set."}
    
    if not retrieved_context:
        return {"candidates": [{"content": {"parts": [{"json": {"error": "No suitable category found by retriever."}}]}}]}

    context_json_string = json.dumps(retrieved_context, indent=2, ensure_ascii=False)

    prompt = f"""
    You are an expert classification system. Your task is to analyze a user's request and select the single most appropriate subcategory from a pre-filtered list of relevant options.

    Here is the pre-filtered list of the MOST RELEVANT subcategories based on a hybrid (semantic + keyword) search. You MUST choose from this list only.
    ```json
    {context_json_string}
    ```

    User's request: "{user_query}"

    Instructions:
    1. From the JSON list above, identify the SINGLE BEST matching subcategory for the user's request. For example, if the user asks for "iPhone charger", prefer the "Lightning" subcategory over the more generic "Adapter".
    2. Respond ONLY with a JSON object copied directly from the list for the subcategory you selected. It must include "category_name", "subcategory_name", and "subcategory_url".
    3. If even among these options none are a good fit, respond with: `{{"error": "No suitable category found."}}`
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": { "temperature": 0.0, "responseMimeType": "application/json" }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(f"{API_ENDPOINT}?key={GEMINI_API_KEY}", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}", "details": str(e)}

# --- მთავარი შესრულებადი კოდი ---
if __name__ == "__main__":
    all_categories_data = load_categories_from_file(CATEGORIES_FILE_PATH)
    
    if all_categories_data:
        retriever = HybridRetriever(all_categories_data)
        
        queries = [
            "სამსუნგის საათი მინდა ვიყიდო",
            "ლეპტოპი მჭირდება, თან რომ თამაშებიც გამიქაჩოს",
            "აიფონის დამტენი ხომ არ გაქვთ?",
            "პოვერ ბანკი",
            "ველოსიპედი",
        ]

        for query in queries:
            print(f"\n--- მომხმარებლის მოთხოვნა: '{query}' ---")
            
            retrieved_results = retriever.search(query, top_k=3)
            print(f"  Retriever-ის მიერ ნაპოვნი რელევანტური კანდიდატები: {[r['subcategory_name'] for r in retrieved_results]}")
            
            result_container = find_category_with_gemini_rag(query, retrieved_results)

            if result_container and result_container.get('candidates'):
                try:
                    parts = result_container['candidates'][0]['content']['parts'][0]
                    if 'json' in parts:
                        final_result = parts['json']
                    elif 'text' in parts:
                        final_result = json.loads(parts['text'])
                    else:
                        raise KeyError("'json' or 'text' key not found in response parts")

                    if "error" in final_result:
                        print(f"  საბოლოო შედეგი: {final_result['error']}")
                    else:
                        base_url = "https://zoommer.ge"
                        subcategory_url = final_result.get('subcategory_url', '')
                        print(f"  რეკომენდებული ლინკი: {base_url}{subcategory_url}")
                except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
                    print(f"  Gemini-ს პასუხის გარჩევისას მოხდა შეცდომა: {e}")
                    print(f"  სრული პასუხი API-დან: {result_container}")
            else:
                print(f"  API-მ დააბრუნა შეცდომა.")
                print(f"  სრული პასუხი API-დან: {result_container}")