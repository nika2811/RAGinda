import gradio as gr
import requests

API_URL = "http://localhost:8000/search"

def chatbot_response(message, history):
    payload = {"query": message, "max_results": 3}
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("total_results", 0) == 0:
            return {"role": "assistant", "content": "🙁 ვერაფერი ვიპოვე. სცადე სხვა სიტყვებით!"}

        reply = "🔎 აირჩიე საუკეთესო ვარიანტებიდან:\n\n"
        for i, product in enumerate(data["products"], 1):
            title = product.get("title", "Untitled")
            price = product.get("price", "ფასი უცნობია")
            url = product.get("url", "#")
            reply += f"**{i}. [{title}]({url})**\n💵 ფასი: {price}\n\n"

        return {"role": "assistant", "content": reply}

    except Exception as e:
        return {"role": "assistant", "content": "🚨 შეცდომა სერვერთან. სცადე მოგვიანებით."}

chat_interface = gr.ChatInterface(
    fn=chatbot_response,
    title="🛍️ RAGinda — ჭკვიანი პროდუქტის ასისტენტი",
    description="კითხე პროდუქტზე და დაგეხმარები საუკეთესო შეთავაზებების პოვნაში 🧠",
    theme=gr.themes.Soft(
        primary_hue="violet",
        secondary_hue="gray",
        radius_size="lg",
        font=[gr.themes.GoogleFont("Inter")],
    ),
    chatbot=gr.Chatbot(
        height=550,
        type="messages",
        show_copy_button=True,
        bubble_full_width=False,
        avatar_images=("https://img.icons8.com/emoji/48/user-emoji.png", "https://img.icons8.com/emoji/48/robot-emoji.png")
    ),
    textbox=gr.Textbox(
        placeholder="მაგ: ლეპტოპი თამაშებისთვის 1500 ლარამდე",
        label="შეიყვანე შენი მოთხოვნა",
        scale=8
    ),
    examples=[
        "სმარტფონი 1000 ლარამდე",
        "მუშაობისთვის კარგი მონიტორი",
        "აუდიო სისტემა მაღალი ხმით"
    ],
    type="messages"
)

if __name__ == "__main__":
    chat_interface.launch()