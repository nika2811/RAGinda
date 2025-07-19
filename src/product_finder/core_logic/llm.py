# src/product_finder/core_logic/llm.py
import json
import requests

from .. import config

def find_category_with_gemini_rag(user_query, retrieved_context):
    if not config.GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not set in config.py or .env file."}

    if not retrieved_context:
        return {"error": "No suitable category found by retriever."}

    context_json_string = json.dumps(retrieved_context, indent=2, ensure_ascii=False)
    
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
    3. If even among these options none are a good fit, respond with: {{"error": "No suitable category found."}}
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": config.GEMINI_GENERATION_CONFIG
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(f"{config.GEMINI_API_ENDPOINT}?key={config.GEMINI_API_KEY}", headers=headers, json=payload)
        response.raise_for_status()
        
        # Extract the JSON part from the response
        response_data = response.json()
        parts = response_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0]
        # Handle both direct JSON and stringified JSON
        final_json = parts.get('json') or json.loads(parts.get('text', '{}'))
        return final_json
        
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except (json.JSONDecodeError, IndexError, KeyError) as e:
        return {"error": f"Failed to parse LLM response: {e}", "raw_response": response.text}