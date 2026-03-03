import os
import pandas as pd
from io import StringIO
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, PollAnswerHandler

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8225509195

questions = []
poll_map = {}
user_score = 0
total_questions = 0


menu = ReplyKeyboardMarkup(
    [
        ["📤 Upload CSV"],
        ["🧠 Start Test"]
    ],
    resize_keyboard=True
)


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🤖 MCQ Exam Bot\n\nUpload CSV or paste CSV text.",
        reply_markup=menu
    )


# LOAD CSV FILE
async def load_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions

    if update.effective_user.id != ADMIN_ID:
        return

    file = await update.message.document.get_file()
    await file.download_to_drive("questions.csv")

    df = pd.read_csv("questions.csv")

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.")


# LOAD CSV TEXT
async def load_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text

    if "Question" not in text:
        return

    df = pd.read_csv(StringIO(text))

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.")


# START TEST
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global user_score, total_questions

    if update.effective_user.id != ADMIN_ID:
        return

    if not questions:
        await update.message.reply_text("Upload CSV first.")
        return

    user_score = 0

    selected = questions[:100]

    total_questions = len(selected)

    for q in selected:

        options = [
            q["Option A"],
            q["Option B"],
            q["Option C"],
            q["Option D"]
        ]

        correct = ["A", "B", "C", "D"].index(q["Answer"])

        poll = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=q["Question"],
            options=options,
            type="quiz",
            correct_option_id=correct,
            is_anonymous=False
        )

        poll_map[poll.poll.id] = correct

    await update.message.reply_text("✅ Test started.")


# RECEIVE ANSWERS
async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global user_score

    answer = update.poll_answer

    poll_id = answer.poll_id
    selected = answer.option_ids[0]

    correct = poll_map.get(poll_id)

    if selected == correct:
        user_score += 1


# RESULT
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        f"📊 Test Finished\n\nScore: {user_score} / {total_questions}"
    )


# MENU HANDLER
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "🧠 Start Test":
        await start_test(update, context)

    elif text == "📤 Upload CSV":
        await update.message.reply_text("Send CSV file or paste CSV text.")


# MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("starttest", start_test))

app.add_handler(MessageHandler(filters.Document.ALL, load_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, load_text))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

app.add_handler(PollAnswerHandler(receive_poll_answer))

app.run_polling()
