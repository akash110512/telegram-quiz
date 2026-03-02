import os
import asyncio
import pandas as pd
from io import StringIO
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    PollAnswerHandler,
)

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8225509195

questions = []
poll_answers = {}
leaderboard = {}
poll_correct = {}

# MENU UI
menu = ReplyKeyboardMarkup(
    [
        ["📘 Start Test"],
        ["📊 Result", "🏆 Leaderboard"],
        ["❓ Help"]
    ],
    resize_keyboard=True
)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🤖 MCQ Exam Bot\n\nUse the menu below."
    await update.message.reply_text(text, reply_markup=menu)

# HELP
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Admin uploads questions using /uploadcsv\n\n"
        "CSV format:\n"
        "Question,Option A,Option B,Option C,Option D,Answer\n\n"
        "Answer must be A/B/C/D"
    )

# MENU BUTTON HANDLER
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📘 Start Test":
        await test(update, context)

    elif text == "📊 Result":
        await result(update, context)

    elif text == "🏆 Leaderboard":
        await leaderboard_cmd(update, context)

    elif text == "❓ Help":
        await help_cmd(update, context)

# ADMIN COMMAND
async def uploadcsv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can upload questions.")
        return

    await update.message.reply_text("Send CSV file or paste CSV text.")

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
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not questions:
        await update.message.reply_text("No questions loaded.")
        return

    user = update.effective_user.id

    poll_answers[user] = {
        "correct": 0,
        "total": min(len(questions), 100)
    }

    for i, q in enumerate(questions[:100], start=1):

        options = [
            q["Option A"],
            q["Option B"],
            q["Option C"],
            q["Option D"]
        ]

        correct_index = ["A", "B", "C", "D"].index(q["Answer"].strip().upper())

        poll = await context.bot.send_poll(
            chat_id=user,
            question=f"Question {i} / {len(questions[:100])}\n\n{q['Question']}",
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )

        poll_correct[poll.poll.id] = correct_index

        await asyncio.sleep(0.3)

# RECEIVE ANSWERS
async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    answer = update.poll_answer
    user = answer.user.id
    poll_id = answer.poll_id

    if user not in poll_answers:
        return

    if poll_id not in poll_correct:
        return

    selected = answer.option_ids[0]
    correct = poll_correct[poll_id]

    if selected == correct:
        poll_answers[user]["correct"] += 1

# RESULT
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in poll_answers:
        await update.message.reply_text("No test taken.")
        return

    correct = poll_answers[user]["correct"]
    total = poll_answers[user]["total"]
    wrong = total - correct

    name = update.effective_user.first_name
    leaderboard[name] = correct

    accuracy = round((correct / total) * 100, 2)

    text = f"""
📊 Test Result

Total Questions: {total}
Correct: {correct}
Wrong: {wrong}
Score: {correct}
Accuracy: {accuracy}%
"""

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
app.add_handler(CommandHandler("starttest", start_test))
app.add_handler(CommandHandler("uploadcsv", uploadcsv))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
app.add_handler(CommandHandler("help", help_cmd))

app.add_handler(MessageHandler(filters.Document.ALL, load_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, load_text))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

app.add_handler(PollAnswerHandler(receive_poll_answer))

app.run_polling()

