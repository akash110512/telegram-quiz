import os
import pandas as pd
from io import StringIO

from telegram import (
    Update,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    PollAnswerHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8225509195

questions = []
poll_map = {}

scores = {}
wrong_questions = {}
leaderboard = {}


menu = ReplyKeyboardMarkup(
    [
        ["📘 Start Test"],
        ["❌ Wrong Questions"],
        ["🏆 Leaderboard", "📊 Result"],
        ["📂 Upload CSV", "❓ Help"]
    ],
    resize_keyboard=True
)


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 MCQ Exam Bot\n\nUse the menu below.",
        reply_markup=menu
    )


# HELP
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
📘 Start Test → Begin quiz
❌ Wrong Questions → Retry wrong
🏆 Leaderboard → Top scores
📊 Result → Show your result
📂 Upload CSV → Admin only
"""
    )


# LOAD CSV FILE
async def load_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    file = await update.message.document.get_file()
    await file.download_to_drive("questions.csv")

    load_questions("questions.csv")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.")


# LOAD CSV TEXT
async def load_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text

    if "Question" not in text:
        return

    df = pd.read_csv(StringIO(text))

    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    global questions
    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.")


def load_questions(file):

    df = pd.read_csv(file)

    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    global questions
    questions = df.to_dict("records")


# START TEST
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not questions:
        await update.message.reply_text("Upload questions first.")
        return

    user = update.effective_user.id
    name = update.effective_user.first_name

    scores[user] = 0
    wrong_questions[user] = []

    for i, q in enumerate(questions):

        options = [
            q["Option A"],
            q["Option B"],
            q["Option C"],
            q["Option D"]
        ]

        correct = q["Answer"]
        correct_index = ["A", "B", "C", "D"].index(correct)

        poll = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"Question {i+1}/{len(questions)}\n{q['Question']}",
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )

        poll_map[poll.poll.id] = {
            "user": user,
            "correct": correct_index,
            "question": q,
            "name": name
        }


# RECEIVE ANSWERS
async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    answer = update.poll_answer

    poll_id = answer.poll_id
    option = answer.option_ids[0]

    data = poll_map.get(poll_id)

    if not data:
        return

    user = data["user"]

    if option == data["correct"]:
        scores[user] += 1
    else:
        wrong_questions[user].append(data["question"])


# RESULT
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id
    name = update.effective_user.first_name

    total = len(questions)
    correct = scores.get(user, 0)
    wrong = total - correct

    leaderboard[name] = correct

    text = f"""
📊 Test Finished

Total Questions: {total}
Correct: {correct}
Wrong: {wrong}

Score: {correct}
"""

    await update.message.reply_text(text)


# WRONG PRACTICE
async def wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in wrong_questions or not wrong_questions[user]:
        await update.message.reply_text("No wrong questions.")
        return

    qs = wrong_questions[user]

    for i, q in enumerate(qs):

        options = [
            q["Option A"],
            q["Option B"],
            q["Option C"],
            q["Option D"]
        ]

        correct = q["Answer"]
        correct_index = ["A", "B", "C", "D"].index(correct)

        poll = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"Retry {i+1}/{len(qs)}\n{q['Question']}",
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )

        poll_map[poll.poll.id] = {
            "user": user,
            "correct": correct_index,
            "question": q
        }


# LEADERBOARD
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not leaderboard:
        await update.message.reply_text("No scores yet.")
        return

    sorted_scores = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    text = "🏆 Leaderboard\n\n"

    for i, (name, score) in enumerate(sorted_scores[:10], start=1):
        text += f"{i}. {name} — {score}\n"

    await update.message.reply_text(text)


# MENU HANDLER
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "📘 Start Test":
        await start_test(update, context)

    elif text == "❌ Wrong Questions":
        await wrong(update, context)

    elif text == "🏆 Leaderboard":
        await leaderboard_cmd(update, context)

    elif text == "📊 Result":
        await result(update, context)

    elif text == "📂 Upload CSV":
        await update.message.reply_text("Send CSV file or paste CSV text.")

    elif text == "❓ Help":
        await help_cmd(update, context)


# MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
app.add_handler(CommandHandler("result", result))

app.add_handler(MessageHandler(filters.Document.ALL, load_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, load_text))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

app.add_handler(PollAnswerHandler(receive_poll_answer))

app.run_polling()
