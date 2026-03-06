import csv
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8750507900:AAGWt_dmXam1S6wAhqdfBlQ5HS8-9nR0wLA"

questions = []
target_chat = None
waiting_csv = False


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot ready.\n\nUse command:\n/uploadcsv\n\nThen paste CSV text."
    )


# UPLOAD CSV
async def upload_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_csv
    waiting_csv = True
    await update.message.reply_text("Paste CSV text now.")


# RECEIVE CSV
async def receive_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global questions, waiting_csv

    if not waiting_csv:
        return

    text = update.message.text.strip()
    lines = text.splitlines()

    reader = csv.reader(lines)

    data = list(reader)

    # Auto header detection
    if data[0][0].lower() != "question":
        data.insert(0, ["Question","Option A","Option B","Option C","Option D","Answer"])

    questions = []

    for row in data[1:]:

        if len(row) < 6:
            continue

        questions.append({
            "question": row[0],
            "options": [row[1],row[2],row[3],row[4]],
            "answer": row[5].strip().upper()
        })

    waiting_csv = False

    await update.message.reply_text(
        f"CSV uploaded successfully.\nMCQs loaded: {len(questions)}"
    )


# SET CHANNEL / GROUP
async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global target_chat

    target_chat = update.effective_chat.id

    await update.message.reply_text(
        f"Channel/Group set successfully.\nID: {target_chat}"
    )


# START TEST
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global questions, target_chat

    if not questions:
        await update.message.reply_text("No questions uploaded.")
        return

    if not target_chat:
        await update.message.reply_text("Run /setchannel in your group first.")
        return

    count = 0

    for q in questions:

        if count >= 100:
            break

        correct_index = ["A","B","C","D"].index(q["answer"])

        await context.bot.send_poll(
            chat_id=target_chat,
            question=q["question"],
            options=q["options"],
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )

        count += 1
        await asyncio.sleep(1)
        if count % 20 == 0:
            await asyncio.sleep(10)

    await update.message.reply_text(f"{count} polls sent.")


# MAIN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("uploadcsv", upload_csv))
app.add_handler(CommandHandler("setchannel", set_channel))
app.add_handler(CommandHandler("starttest", start_test))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_csv))

app.run_polling()




