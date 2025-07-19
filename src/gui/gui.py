import gradio as gr
import requests

API_URL = "http://localhost:8000/search"
history = []

def chatbot_response(message, history):
    try:
        # Send user query to FastAPI search endpoint
        payload = {"query": message, "max_results": 3}
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        # Format the result
        if data["total_results"] == 0:
            reply = "ვერაფერი მოიძებნა. სცადე სხვა შეკითხვა 🧐"
        else:
            reply = "აი, რამდენიმე ვარიანტი 👇:\n"
            for i, product in enumerate(data["products"], 1):
                title = product["title"]
                price = product["price"]
                url = product.get("url", "#")
                reply += f"{i}. [{title}]({url}) - {price}\n"

        return {"role": "assistant", "content": reply}

    except requests.exceptions.RequestException as e:
        return {"role": "assistant", "content": f"❌ შეცდომა სერვერთან კავშირისას: {str(e)}"}

chat_interface = gr.ChatInterface(
    fn=chatbot_response,
    title="🛍️ RAGinda",
    theme="soft",
    chatbot=gr.Chatbot(height=500, type="messages", show_copy_button=True),
    textbox=gr.Textbox(placeholder="Type your question here...", scale=7),
    examples=["სმარტფონი 1000 ლარამდე", "საუკეთესო ლეპტოპი პროგრამირებისთვის"],
    type="messages",
)

if __name__ == "__main__":
    chat_interface.launch()