import os
import csv
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, PollAnswerHandler

TOKEN = os.getenv("TOKEN")

# ADMIN USER ID
ADMIN_ID = 8225509195

questions = []
poll_answers = {}
score = 0


# MENU
menu_keyboard = [
    ["📂 Upload CSV"],
    ["📘 Start Test"],
]

menu = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized user.")
        return

    await update.message.reply_text(
        "🤖 MCQ Exam Bot\n\nUpload CSV or paste CSV text",
        reply_markup=menu
    )


# LOAD CSV TEXT
async def load_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions
    text = update.message.text

    if text.startswith("/"):
        return

    try:
        lines = text.split("\n")
        reader = csv.DictReader(lines)

        questions = []

        for row in reader:

            questions.append({
                "question": row["Question"],
                "options": [
                    row["Option A"],
                    row["Option B"],
                    row["Option C"],
                    row["Option D"]
                ],
                "answer": ["A","B","C","D"].index(row["Answer"])
            })

        questions = questions[:100]

        await update.message.reply_text(f"✅ {len(questions)} questions loaded.")

    except:
        await update.message.reply_text("❌ Invalid CSV format")


# LOAD CSV FILE
async def load_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions

    file = await update.message.document.get_file()
    path = "questions.csv"

    await file.download_to_drive(path)

    questions = []

    with open(path, newline='', encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            questions.append({
                "question": row["Question"],
                "options": [
                    row["Option A"],
                    row["Option B"],
                    row["Option C"],
                    row["Option D"]
                ],
                "answer": ["A","B","C","D"].index(row["Answer"])
            })

    questions = questions[:100]

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.")


# START TEST
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global score
    score = 0

    if len(questions) == 0:
        await update.message.reply_text("Upload CSV first.")
        return

    chat_id = update.effective_chat.id

    await update.message.reply_text(f"📘 Starting Test\nTotal Questions: {len(questions)}")

    for q in questions:

        poll = await context.bot.send_poll(
            chat_id,
            question=q["question"],
            options=q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            is_anonymous=False
        )

        poll_answers[poll.poll.id] = q["answer"]

        await asyncio.sleep(0.4)


# RECEIVE ANSWERS
async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global score

    poll_id = update.poll_answer.poll_id
    selected = update.poll_answer.option_ids[0]

    if poll_id in poll_answers:

        correct = poll_answers[poll_id]

        if selected == correct:
            score += 1


# MENU HANDLER
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "📂 Upload CSV":
        await update.message.reply_text("Send CSV file or paste CSV text")

    elif text == "📘 Start Test":
        await start_test(update, context)


# MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("starttest", start_test))

app.add_handler(MessageHandler(filters.Document.ALL, load_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, load_text))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

app.add_handler(PollAnswerHandler(receive_poll_answer))

app.run_polling()
