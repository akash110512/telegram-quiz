import os
import random
import pandas as pd
from io import StringIO

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

questions = []
user_data = {}
leaderboard = {}

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🤖 MCQ Practice Bot\n\n"
        "Commands:\n"
        "/practice - Start test\n"
        "/polltest - Poll based test\n"
        "/wrong - Retry wrong questions\n"
        "/leaderboard - Show leaderboard\n"
        "/result - Show score\n\n"
        "Send CSV file OR paste CSV text."
    )

    await update.message.reply_text(text)


# LOAD CSV FILE
async def load_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global questions

    file = await update.message.document.get_file()
    await file.download_to_drive("questions.csv")

    df = pd.read_csv("questions.csv")

    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.\nType /practice")


# LOAD CSV TEXT
async def load_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global questions

    text = update.message.text

    if "Question" not in text:
        return

    df = pd.read_csv(StringIO(text))

    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.\nType /practice")


# START PRACTICE TEST
async def practice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not questions:
        await update.message.reply_text("Please upload CSV first.")
        return

    user = update.effective_user.id
    name = update.effective_user.first_name

    user_data[user] = {
        "name": name,
        "remaining": questions.copy(),
        "score": 0,
        "wrong": [],
        "total": len(questions),
        "done": 0
    }

    await send_question(context, user)


# SEND QUESTION
async def send_question(context, user):

    data = user_data[user]

    if not data["remaining"]:

        total = data["total"]
        correct = data["score"]
        wrong = total - correct

        leaderboard[data["name"]] = correct

        text = (
            f"🏁 Test Finished\n\n"
            f"Total Questions: {total}\n"
            f"Correct: {correct}\n"
            f"Wrong: {wrong}\n"
            f"Score: {correct}\n\n"
            f"/wrong - retry wrong\n"
            f"/leaderboard - see leaderboard"
        )

        await context.bot.send_message(chat_id=user, text=text)

        return

    q = random.choice(data["remaining"])
    data["remaining"].remove(q)

    data["current"] = q
    data["done"] += 1

    number = data["done"]
    total = data["total"]

    keyboard = [
        [InlineKeyboardButton("A", callback_data="A"),
         InlineKeyboardButton("B", callback_data="B")],
        [InlineKeyboardButton("C", callback_data="C"),
         InlineKeyboardButton("D", callback_data="D")]
    ]

    text = (
        f"Question {number} / {total}\n\n"
        f"{q['Question']}\n\n"
        f"A. {q['Option A']}\n"
        f"B. {q['Option B']}\n"
        f"C. {q['Option C']}\n"
        f"D. {q['Option D']}"
    )

    await context.bot.send_message(
        chat_id=user,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ANSWER HANDLER
async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.id

    data = user_data[user]

    q = data["current"]

    choice = query.data
    correct = str(q["Answer"]).strip().upper()

    if choice == correct:

        data["score"] += 1
        msg = f"✅ Correct\nScore: {data['score']}"

    else:

        msg = f"❌ Wrong\nCorrect answer: {correct}\nScore: {data['score']}"
        data["wrong"].append(q)

    await context.bot.send_message(chat_id=user, text=msg)

    await send_question(context, user)


# WRONG QUESTIONS TEST
async def wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in user_data or not user_data[user]["wrong"]:
        await update.message.reply_text("No wrong questions.")
        return

    user_data[user]["remaining"] = user_data[user]["wrong"].copy()
    user_data[user]["wrong"] = []
    user_data[user]["done"] = 0
    user_data[user]["total"] = len(user_data[user]["remaining"])

    await send_question(context, user)


# RESULT
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in user_data:
        await update.message.reply_text("No test started.")
        return

    data = user_data[user]

    total = data["total"]
    correct = data["score"]
    wrong = total - correct

    text = (
        f"📊 Current Result\n\n"
        f"Total Questions: {total}\n"
        f"Correct: {correct}\n"
        f"Wrong: {wrong}\n"
        f"Score: {correct}"
    )

    await update.message.reply_text(text)


# LEADERBOARD
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not leaderboard:
        await update.message.reply_text("No scores yet.")
        return

    text = "🏆 Leaderboard\n\n"

    sorted_scores = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    for i, (name, score) in enumerate(sorted_scores[:10], start=1):
        text += f"{i}. {name} — {score}\n"

    await update.message.reply_text(text)


# MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("practice", practice))
app.add_handler(CommandHandler("wrong", wrong))
app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
app.add_handler(CommandHandler("result", result))

app.add_handler(MessageHandler(filters.Document.ALL, load_csv))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, load_text))

app.add_handler(CallbackQueryHandler(answer))

app.run_polling()
