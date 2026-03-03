import os
import pandas as pd
from io import StringIO
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton
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

questions = []
poll_map = {}
user_scores = {}
leaderboard = {}

ADMIN_ID = 8225509195


# MENU
menu = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📚 Start Test")],
        [KeyboardButton("📂 Upload CSV")],
        [KeyboardButton("📊 Result"), KeyboardButton("🏆 Leaderboard")],
    ],
    resize_keyboard=True
)


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 MCQ Exam Bot\n\nUpload CSV or paste CSV text.",
        reply_markup=menu
    )


# LOAD CSV FILE
async def load_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global questions

    file = await update.message.document.get_file()
    await file.download_to_drive("questions.csv")

    df = pd.read_csv("questions.csv")
    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.")


# LOAD CSV TEXT
async def load_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global questions

    text = update.message.text

    if "Question" not in text:
        return

    df = pd.read_csv(StringIO(text))
    df["Answer"] = df["Answer"].astype(str).str.strip().str.upper()

    questions = df.to_dict("records")

    await update.message.reply_text(f"✅ {len(questions)} questions loaded.")


# START TEST
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if not questions:
        await update.message.reply_text("Upload CSV first.")
        return

    user_scores[user] = {
        "score": 0,
        "answered": 0,
        "total": len(questions)
    }

    poll_map.clear()

    for i, q in enumerate(questions):

        options = [
            q["Option A"],
            q["Option B"],
            q["Option C"],
            q["Option D"]
        ]

        correct_index = ["A","B","C","D"].index(q["Answer"])

        msg = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"Q{i+1}/{len(questions)}\n{q['Question']}",
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )

        poll_map[msg.poll.id] = correct_index


# POLL ANSWER
async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):

    answer = update.poll_answer

    user = answer.user.id
    poll_id = answer.poll_id
    choice = answer.option_ids[0]

    correct = poll_map.get(poll_id)

    if user not in user_scores:
        return

    user_scores[user]["answered"] += 1

    if choice == correct:
        user_scores[user]["score"] += 1

    data = user_scores[user]

    if data["answered"] == data["total"]:

        score = data["score"]
        total = data["total"]

        leaderboard[user] = score

        await context.bot.send_message(
            chat_id=user,
            text=(
                "📊 TEST FINISHED\n\n"
                f"Total Questions: {total}\n"
                f"Correct: {score}\n"
                f"Wrong: {total-score}\n\n"
                f"Score: {score}"
            )
        )


# RESULT
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user.id

    if user not in user_scores:
        await update.message.reply_text("No test taken.")
        return

    data = user_scores[user]

    await update.message.reply_text(
        f"📊 Result\n\n"
        f"Score: {data['score']} / {data['total']}"
    )


# LEADERBOARD
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not leaderboard:
        await update.message.reply_text("No scores yet.")
        return

    text = "🏆 Leaderboard\n\n"

    sorted_scores = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

    for i,(user,score) in enumerate(sorted_scores[:10],start=1):
        text += f"{i}. {score}\n"

    await update.message.reply_text(text)


# MENU BUTTONS
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "📚 Start Test":
        await start_test(update, context)

    elif text == "📂 Upload CSV":
        await update.message.reply_text("Send CSV file.")

    elif text == "📊 Result":
        await result(update, context)

    elif text == "🏆 Leaderboard":
        await leaderboard_cmd(update, context)


# MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("starttest", start_test))
app.add_handler(CommandHandler("result", result))
app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))

app.add_handler(MessageHandler(filters.Document.ALL, load_file))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, load_text))
app.add_handler(MessageHandler(filters.TEXT, menu_handler))

app.add_handler(PollAnswerHandler(receive_poll))

app.run_polling()
