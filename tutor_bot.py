import os
from threading import Thread
from flask import Flask
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---- Gemini setup ----
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="""You are a patient, step-by-step homework tutor.
When a student asks a question:
- Break the problem into simple, logical steps.
- Explain each step clearly in plain language.
- Don’t just give the final answer — guide the student to understand.
- For math, show formulas, intermediate results, and reasoning.
- For writing, help with brainstorming and structure.
- Keep a friendly, conversational tone.
- Split long answers naturally; each part must be under 4000 characters."""
)

# Store chat sessions per user
chat_sessions = {}

# Flask app to keep the service alive
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running"

def run_web():
    flask_app.run(host='0.0.0.0', port=8080)

# ---- Telegram handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_sessions[user_id] = model.start_chat()
    await update.message.reply_text(
        "👋 Hi! I'm your free step-by-step homework tutor.\nSend me any question."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat()

    chat = chat_sessions[user_id]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = chat.send_message(user_text)
        answer = response.text

        # Splitting long answers for Telegram
        while len(answer) > 4000:
            await update.message.reply_text(answer[:4000])
            answer = answer[4000:]
        if answer:
            await update.message.reply_text(answer)

    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("❌ Something went wrong. Try again.")

# ---- Main ----
def main():
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start Flask in a separate thread
    Thread(target=run_web).start()

    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
