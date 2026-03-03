import os
import pandas as pd
from io import StringIO
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    PollAnswerHandler
)

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8225509195

questions = []
poll_ids = {}
user_scores = {}
leaderboard = {}

menu = ReplyKeyboardMarkup(
[
["📘 Start Test","📊 Result"],
["🏆 Leaderboard","❓ Help"]
],
resize_keyboard=True
)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 MCQ Exam Bot\n\nUpload CSV or paste CSV text.\nThen press *Start Test*.",
        reply_markup=menu
    )

# HELP
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
📖 HOW TO USE

1️⃣ Upload CSV file  
or paste CSV text

2️⃣ Click *Start Test*

3️⃣ Answer poll questions

4️⃣ Use *Result* to see score
"""
    await update.message.reply_text(text)


# LOAD CSV FILE
async def load_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions

    file = await update.message.document.get_file()
    await file.download_to_drive("questions.csv")

    df = pd.read_csv("questions.csv")

    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded")


# LOAD CSV TEXT
async def load_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions

    text = update.message.text

    if "Question" not in text:
        return

    df = pd.read_csv(StringIO(text))

    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded")


# START TEST
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can start the test")
        return

    if not questions:
        await update.message.reply_text("❌ Upload CSV first")
        return

    poll_ids.clear()
    user_scores.clear()

    for i,q in enumerate(questions):

        options = [
            q["Option A"],
            q["Option B"],
            q["Option C"],
            q["Option D"]
        ]

        correct_index = ["A","B","C","D"].index(q["Answer"])

        poll = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"Question {i+1}/{len(questions)}\n{q['Question']}",
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )

        poll_ids[poll.poll.id] = correct_index


# RECEIVE POLL ANSWERS
async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    answer = update.poll_answer

    user = answer.user.id
    poll_id = answer.poll_id
    selected = answer.option_ids[0]

    correct = poll_ids.get(poll_id)

    if user not in user_scores:
        user_scores[user] = 0

    if selected == correct:
        user_scores[user] += 1


# RESULT
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id
    name = update.effective_user.first_name

    score = user_scores.get(user,0)

    total = len(questions)

    wrong = total - score

    leaderboard[name] = score

    text = f"""
📊 Test Finished

Total Questions: {total}
Correct: {score}
Wrong: {wrong}

Score: {score}
"""

    await update.message.reply_text(text)


# LEADERBOARD
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not leaderboard:
        await update.message.reply_text("No scores yet")
        return

    text = "🏆 Leaderboard\n\n"

    sorted_scores = sorted(
        leaderboard.items(),
        key=lambda x:x[1],
        reverse=True
    )

    for i,(name,score) in enumerate(sorted_scores[:10],start=1):

        text += f"{i}. {name} — {score}\n"

    await update.message.reply_text(text)


# MENU BUTTON HANDLER
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "📘 Start Test":
        await start_test(update,context)

    elif text == "📊 Result":
        await result(update,context)

    elif text == "🏆 Leaderboard":
        await leaderboard_cmd(update,context)

    elif text == "❓ Help":
        await help_cmd(update,context)


# MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("result",result))
app.add_handler(CommandHandler("leaderboard",leaderboard_cmd))
app.add_handler(CommandHandler("help",help_cmd))

app.add_handler(MessageHandler(filters.Document.ALL,load_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,load_text))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,menu_handler))

app.add_handler(PollAnswerHandler(receive_poll_answer))

app.run_polling()
