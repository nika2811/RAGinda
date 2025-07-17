import os
from dotenv import load_dotenv
import json
import requests

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# მოდელის სახელი შევცვალე 1.5 Flash-ით, რადგან 2.0 Flash ჯერ არ არის საჯაროდ ხელმისაწვდომი და 1.5 Flash იდეალურია ამ ამოცანისთვის.
API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# ნაბიჯი 2: მოვამზადოთ კატეგორიების სრული და თავდაპირველი მონაცემები
# არაფერი არ არის ამოკლებული.
categories_json = """
[
  {
    "category_name": "Canon",
    "category_url": "/canon-c568",
    "subcategories": [
      {
        "subcategory_name": "Instant",
        "subcategory_url": "/canon-instant-c571s",
        "keywords": ["Canon", "Instant", "Camera", "Photo", "ფოტო", "კამერა", "მომენტალური"]
      },
      {
        "subcategory_name": "EOS DSLR",
        "subcategory_url": "/canon-eos-dslr-c572s",
        "keywords": ["Canon", "EOS", "DSLR", "Camera", "Professional Camera", "ფოტოაპარატი", "კამერა"]
      },
      {
        "subcategory_name": "Compact",
        "subcategory_url": "/canon-compact-c1060s",
        "keywords": ["Canon", "Compact", "Camera", "Point and shoot", "კომპაქტური", "ფოტოაპარატი", "კამერა"]
      },
      {
        "subcategory_name": "Mirrorless",
        "subcategory_url": "/canon-mirrorless-c570s",
        "keywords": ["Canon", "Mirrorless", "Camera", "სარკის გარეშე", "ფოტოაპარატი", "კამერა"]
      }
    ]
  },
  {
    "category_name": "აუდიო სისტემა",
    "category_url": "/audio-sistema-c528",
    "subcategories": [
      {
        "subcategory_name": "Polaroid",
        "subcategory_url": "/audio-sistema-polaroid-c1054s",
        "keywords": ["აუდიო სისტემა", "დინამიკი", "ყურსასმენი", "Audio System", "Speaker", "Headphone", "Polaroid"]
      },
      {
        "subcategory_name": "JBL",
        "subcategory_url": "/audio-sistema-jbl-c811s",
        "keywords": ["აუდიო სისტემა", "დინამიკი", "ყურსასმენი", "JBL", "Speaker", "Headphone", "ჯიბიელი"]
      },
      {
        "subcategory_name": "Apple",
        "subcategory_url": "/audio-sistema-apple-c783s",
        "keywords": ["აუდიო სისტემა", "დინამიკი", "ყურსასმენი", "Apple", "Airpods", "Homepod", "Beats", "ეიფლი", "აირპოდსი"]
      },
      {
        "subcategory_name": "Samsung",
        "subcategory_url": "/audio-sistema-samsung-c795s",
        "keywords": ["აუდიო სისტემა", "დინამიკი", "ყურსასმენი", "Samsung", "Galaxy Buds", "სამსუნგი", "ბადსი"]
      },
      {
        "subcategory_name": "Sony",
        "subcategory_url": "/audio-sistema-sony-c964s",
        "keywords": ["აუდიო სისტემა", "დინამიკი", "ყურსასმენი", "Sony", "Speaker", "Headphone", "სონი"]
      }
    ]
  },
  {
    "category_name": "სხვა კონსოლები",
    "category_url": "/skhva-konsolebi-c1027",
    "subcategories": [
      {
        "subcategory_name": "Steam Deck",
        "subcategory_url": "/skhva-konsolebi-steam-deck-c456s",
        "keywords": ["სათამაშო კონსოლი", "პორტატული კონსოლი", "Steam Deck", "Gaming", "Console", "სტიმ დეკი"]
      },
      {
        "subcategory_name": "Asus ROG",
        "subcategory_url": "/skhva-konsolebi-asus-rog-c1194s",
        "keywords": ["სათამაშო კონსოლი", "პორტატული კონსოლი", "Asus ROG", "Gaming", "Console", "ასუსი"]
      },
      {
        "subcategory_name": "Oculus",
        "subcategory_url": "/skhva-konsolebi-oculus-c1028s",
        "keywords": ["VR", "ვირტუალური რეალობა", "Oculus", "Meta Quest", "VR სათვალე", "ოკულუსი"]
      }
    ]
  },
  {
    "category_name": "გრაფიკული ტაბები",
    "category_url": "/grafikuli-tabebi-c776",
    "subcategories": [
      {
        "subcategory_name": "Wacom",
        "subcategory_url": "/grafikuli-tabebi-wacom-c1248s",
        "keywords": ["გრაფიკული პლანშეტი", "სახატავი პლანშეტი", "Wacom", "Graphic Tablet", "Drawing tablet", "ვაკომი"]
      },
      {
        "subcategory_name": "Huion",
        "subcategory_url": "/grafikuli-tabebi-huion-c774s",
        "keywords": ["გრაფიკული პლანშეტი", "სახატავი პლანშეტი", "Huion", "Graphic Tablet", "Drawing tablet", "ჰუიონი"]
      },
      {
        "subcategory_name": "XP-Pen",
        "subcategory_url": "/grafikuli-tabebi-xp-pen-c591s",
        "keywords": ["გრაფიკული პლანშეტი", "სახატავი პლანშეტი", "XP-Pen", "Graphic Tablet", "Drawing tablet"]
      }
    ]
  },
  {
    "category_name": "კაბელები",
    "category_url": "/kabelebi-c1145",
    "subcategories": [
      {
        "subcategory_name": "Micro USB",
        "subcategory_url": "/kabelebi-micro-usb-c1147s",
        "keywords": ["კაბელი", "დამტენი", "Micro USB", "Cable", "Charger", "მიკრო იუესბი"]
      },
      {
        "subcategory_name": "Lightning",
        "subcategory_url": "/kabelebi-lightning-c1146s",
        "keywords": ["კაბელი", "დამტენი", "Lightning", "iPhone charger", "აიფონის კაბელი", "ლაითნინგი", "აიფონი"]
      },
      {
        "subcategory_name": "HDMI კაბელები",
        "subcategory_url": "/kabelebi-hdmi-kabelebi-c527s",
        "keywords": ["კაბელი", "HDMI", "Cable", " მონიტორის კაბელი", "ტელევიზორის კაბელი"]
      },
      {
        "subcategory_name": "Type-C",
        "subcategory_url": "/kabelebi-type-c-c1148s",
        "keywords": ["კაბელი", "დამტენი", "Type-C", "USB-C", "Cable", "Charger", "თაიფ სი"]
      }
    ]
  },
  {
    "category_name": "მობილურის აქსესუარები",
    "category_url": "/mobiluris-aqsesuarebi-c538",
    "subcategories": [
      {
        "subcategory_name": "დამტენი ადაპტერები",
        "subcategory_url": "/mobiluris-aqsesuarebi-damteni-adapterebi-c874s",
        "keywords": ["მობილურის აქსესუარი", "დამტენი", "ადაპტერი", "Charger", "Adapter", "კედლის დამტენი", "აიფონი"]
      },
      {
        "subcategory_name": "გარე დამტენები",
        "subcategory_url": "/mobiluris-aqsesuarebi-gare-damtenebi-c912s",
        "keywords": ["მობილურის აქსესუარი", "პოვერ ბანკი", "გარე დამტენი", "Power Bank", "External Battery"]
      },
      {
        "subcategory_name": "მანქანის დამტენები",
        "subcategory_url": "/mobiluris-aqsesuarebi-manqanis-damtenebi-c904s",
        "keywords": ["მობილურის აქსესუარი", "მანქანის დამტენი", "Car Charger"]
      },
      {
        "subcategory_name": "ეკრანის დამცავები",
        "subcategory_url": "/mobiluris-aqsesuarebi-ekranis-damcavebi-c915s",
        "keywords": ["მობილურის აქსესუარი", "ეკრანის დამცავი", "ბრონი", "Screen Protector"]
      },
      {
        "subcategory_name": "მობილურის ჩასადებები",
        "subcategory_url": "/mobiluris-aqsesuarebi-mobiluris-chasadebi-c983s",
        "keywords": ["მობილურის აქსესუარი", "ქეისი", "ჩასადები", "Phone Case", "Cover", "აიფონი"]
      },
      {
        "subcategory_name": "Micro SD მეხსიერების ბარათები",
        "subcategory_url": "/mobiluris-aqsesuarebi-micro-sd-mekhsierebis-baratebi-c993s",
        "keywords": ["მობილურის აქსესუარი", "მეხსიერების ბარათი", "ჩიპი", "Micro SD", "Memory Card"]
      }
    ]
  },
  {
    "category_name": "Gaming",
    "category_url": "/gaming-c463",
    "subcategories": [
      {
        "subcategory_name": "VR სათვალეები",
        "subcategory_url": "/gaming-vr-satvaleebi-c871s",
        "keywords": ["Gaming", "VR", "Virtual Reality", "VR სათვალე", "VR Glasses", "Oculus", "PSVR"]
      },
      {
        "subcategory_name": "კონსოლები",
        "subcategory_url": "/gaming-konsolebi-c930s",
        "keywords": ["Gaming", "Console", "PlayStation", "Xbox", "Nintendo", "კონსოლი", "სათამაშო აპარატი"]
      },
      {
        "subcategory_name": "Gaming ყურსასმენები",
        "subcategory_url": "/gaming-gaming-yursasmenebi-c956s",
        "keywords": ["Gaming", "Headset", "Headphones", "სათამაშო ყურსასმენი", "გეიმინგ ყურსასმენი", "ყურსასმენი"]
      },
      {
        "subcategory_name": "PC",
        "subcategory_url": "/gaming-pc-c559s",
        "keywords": ["Gaming", "PC", "Computer", "სათამაშო კომპიუტერი", "გეიმინგ პিসি"]
      },
      {
        "subcategory_name": "Gaming ლეპტოპები",
        "subcategory_url": "/gaming-gaming-leptopebi-c838s",
        "keywords": ["Gaming", "Laptop", "სათამაშო ლეპტოპი", "გეიმინგ ლეპტოპი", "ლეპტოპი"]
      }
    ]
  },
  {
    "category_name": "მობილური ტელეფონები",
    "category_url": "/mobiluri-telefonebi-c855",
    "subcategories": [
      {
        "subcategory_name": "Apple",
        "subcategory_url": "/mobiluri-telefonebi-apple-c724s",
        "keywords": ["მობილური", "სმარტფონი", "ტელეფონი", "Apple", "iPhone", "აიფონი", "ეპლი"]
      },
      {
        "subcategory_name": "Samsung",
        "subcategory_url": "/mobiluri-telefonebi-samsung-c814s",
        "keywords": ["მობილური", "სმარტფონი", "ტელეფონი", "Samsung", "Galaxy", "სამსუნგი", "გალაქსი"]
      },
      {
        "subcategory_name": "Xiaomi",
        "subcategory_url": "/mobiluri-telefonebi-xiaomi-c815s",
        "keywords": ["მობილური", "სმარტფონი", "ტელეფონი", "Xiaomi", "Redmi", "Poco", "შაომი", "ქსიაომი", "რედმი"]
      },
      {
        "subcategory_name": "Google",
        "subcategory_url": "/mobiluri-telefonebi-google-c968s",
        "keywords": ["მობილური", "სმარტფონი", "ტელეფონი", "Google", "Pixel", "გუგლი", "პიქსელი"]
      },
      {
        "subcategory_name": "Nothing",
        "subcategory_url": "/mobiluri-telefonebi-nothing-c554s",
        "keywords": ["მობილური", "სმარტფონი", "ტელეფონი", "Nothing Phone", "ნათინგი"]
      }
    ]
  },
    {
    "category_name": "ლეპტოპები",
    "category_url": "/leptopebi-c531",
    "subcategories": [
      {
        "subcategory_name": "Business ლეპტოპი",
        "subcategory_url": "/leptopebi-business-leptopi-c563s",
        "keywords": ["ლეპტოპი", "ნოუთბუქი", "ბიზნეს ლეპტოპი", "სამუშაო ლეპტოპი", "Laptop", "Notebook", "Business Laptop"]
      },
      {
        "subcategory_name": "Gaming ლეპტოპი",
        "subcategory_url": "/leptopebi-gaming-leptopi-c708s",
        "keywords": ["ლეპტოპი", "ნოუთბუქი", "გეიმინგ ლეპტოპი", "სათამაშო ლეპტოპი", "Gaming Laptop"]
      },
      {
        "subcategory_name": "Classic ლეპტოპი",
        "subcategory_url": "/leptopebi-classic-leptopi-c564s",
        "keywords": ["ლეპტოპი", "ნოუთბუქი", "კლასიკური ლეპტოპი", "ყოველდღიური ლეპტოპი", "Classic Laptop", "Notebook"]
      }
    ]
  },
  {
    "category_name": "სმარტ საათები",
    "category_url": "/smart-saatebi-c873",
    "subcategories": [
      {
        "subcategory_name": "Apple Watch",
        "subcategory_url": "/smart-saatebi-apple-watch-c622s",
        "keywords": ["სმარტ საათი", "ჭკვიანი საათი", "Apple Watch", "iWatch", "ეპლის საათი"]
      },
      {
        "subcategory_name": "Galaxy Watch",
        "subcategory_url": "/smart-saatebi-galaxy-watch-c621s",
        "keywords": ["სმარტ საათი", "ჭკვიანი საათი", "Samsung", "Galaxy Watch", "სამსუნგის საათი", "samsungis saati"]
      },
      {
        "subcategory_name": "Xiaomi Watch",
        "subcategory_url": "/smart-saatebi-xiaomi-watch-c620s",
        "keywords": ["სმარტ საათი", "ჭკვიანი საათი", "Xiaomi Watch", "Mi Band", "Amazfit", "შაომის საათი"]
      },
      {
        "subcategory_name": "Garmin Watch",
        "subcategory_url": "/smart-saatebi-garmin-watch-c1009s",
        "keywords": ["სმარტ საათი", "ჭკვიანი საათი", "სპორტული საათი", "Garmin", "გარმინი"]
      }
    ]
  },
  {
    "category_name": "ჭკვიანი სახლი",
    "category_url": "/chkviani-sakhli-c474",
    "subcategories": [
      {
        "subcategory_name": "ჭკვიანი სახლი",
        "subcategory_url": "/chkviani-sakhli-chkviani-sakhli-c1131s",
        "keywords": ["ჭკვიანი სახლი", "სმარტ სახლი", "Smart Home", "ავტომატიზაცია", "განათება", "სენსორები"]
      }
    ]
  }
]
"""
categories_data = json.loads(categories_json)


def find_category_with_gemini(user_query, full_categories_data):
    """
    იყენებს Gemini API-ს მომხმარებლის მოთხოვნის კატეგორიზაციისთვის სრული JSON მონაცემების გამოყენებით.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not set in environment variables."}

    full_category_json_string = json.dumps(full_categories_data, indent=2, ensure_ascii=False)

    prompt = f"""
    You are an intelligent product classification engine for a Georgian electronics store.
    Your main task is to analyze a user's request and match it to the most relevant product subcategory from the full JSON data structure provided below.

    Here is the FULL JSON structure of all available products and categories. You must use this data to make your decision. Analyze everything: `category_name`, `subcategory_name`, `keywords`, and even the `_url` fields for context.
    ```json
    {full_category_json_string}
    ```

    User's request in Georgian: "{user_query}"

    Your Instructions:
    1.  Thoroughly analyze the user's request to understand the intent, product type, brand, and any other specifications.
    2.  Find the SINGLE BEST matching subcategory from the JSON data provided above.
    3.  You MUST respond ONLY with a JSON object. Do not write any other text or explanations outside of the JSON structure.
    4.  The JSON object you return must have these exact keys: "category_name", "subcategory_name", "subcategory_url", "reason".
    5.  The "reason" field should be a brief, one-sentence explanation in English of why you chose that category based on the user's request.
    6.  If you cannot find any relevant category, you MUST respond ONLY with this specific JSON object:
        `{{"error": "No suitable category found."}}`

    Example of a perfect response for the query "აიფონის ქეისი მინდა":
    {{
      "category_name": "მობილურის აქსესუარები",
      "subcategory_name": "მობილურის ჩასადებები",
      "subcategory_url": "/mobiluris-aqsesuarebi-mobiluris-chasadebebi-c983s",
      "reason": "The user is asking for an 'iPhone case' ('აიფონის ქეისი'), which directly corresponds to the 'Mobile Accessories' -> 'Phone Cases' subcategory."
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "temperature": 0.1,
            "topK": 1,
            "topP": 1,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json"
        }
    }

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(f"{API_ENDPOINT}?key={GEMINI_API_KEY}", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


# --- ტესტირება ---
if __name__ == "__main__":
    queries = [
        "სამსუნგის საათი მინდა ვიყიდო",
        "ლეპტოპი მჭირდება, თან რომ თამაშებიც გამიქაჩოს",
        "აიფონის დამტენი ხომ არ გაქვთ?",
        "პოვერ ბანკი",
        "ველოსიპედი", 
    ]

    for query in queries:
        print(f"--- მომხმარებლის მოთხოვნა: '{query}' ---")
        result_container = find_category_with_gemini(query, categories_data)

        if result_container and 'candidates' in result_container:
            try:
                # Gemini-ს პასუხი მოდის როგორც stringified JSON
                response_text = result_container['candidates'][0]['content']['parts'][0]['text']
                final_result = json.loads(response_text)
                if "error" in final_result:
                    print(f"  შედეგი: {final_result['error']}\n")
                else:
                    base_url = "https://zoommer.ge"
                    subcategory_url = final_result.get('subcategory_url', '')
                    print(base_url + subcategory_url)
            except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
                print(f"  Gemini-ს პასუხის გარჩევისას მოხდა შეცდომა: {e}")
                print(f"  სრული პასუხი: {result_container}\n")
        else:
            print("  API-დან მიღებული პასუხი არასწორ ფორმატშია ან შეიცავს შეცდომას.")
            print(f"  სრული პასუხი: {result_container}\n")