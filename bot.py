import os
import pandas as pd
from io import StringIO
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8225509195

questions = []
target_chat = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot ready.\n\nUse command:\n/uploadcsv\n\nPaste CSV text after that."
    )


async def setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global target_chat

    if update.effective_user.id != ADMIN_ID:
        return

    target_chat = update.effective_chat.id

    await update.message.reply_text(
        f"Channel/Group set successfully.\nID: {target_chat}"
    )


async def uploadcsv(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "Paste your CSV text now."
    )


async def receive_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions

    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text

    if "," not in text:
        return

    lines = text.strip().split("\n")

    # detect header
    if not lines[0].lower().startswith("question"):
        lines.insert(0, "Question,Option A,Option B,Option C,Option D,Answer")

    df = pd.read_csv(StringIO("\n".join(lines)))

    questions = df.to_dict("records")

    questions = questions[:100]

    await update.message.reply_text(
        f"CSV uploaded successfully.\nMCQs loaded: {len(questions)}"
    )

    await send_polls(context)


async def send_polls(context: ContextTypes.DEFAULT_TYPE):

    if not questions:
        return

    if not target_chat:
        return

    for q in questions:

        options = [
            str(q["Option A"]),
            str(q["Option B"]),
            str(q["Option C"]),
            str(q["Option D"])
        ]

        answer = str(q["Answer"]).strip().upper()

        correct = ["A", "B", "C", "D"].index(answer)

        await context.bot.send_poll(
            chat_id=target_chat,
            question=q["Question"],
            options=options,
            type="quiz",
            correct_option_id=correct,
            is_anonymous=False
        )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("uploadcsv", uploadcsv))
app.add_handler(CommandHandler("setchannel", setchannel))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_csv))

app.run_polling()
