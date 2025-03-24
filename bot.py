import json
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
)
import random

# Define conversation states
ENGLISH, ARABIC, PRACTICE = range(3)

# You can use it for any language!

TOKEN = "your token #######"

def save_to_json(english_word, arabic_word):
    
    try:
        with open("words.json", "r", encoding="utf-8") as file:
            words_dict = json.load(file)  # Load existing words
    except (FileNotFoundError, json.JSONDecodeError):
        words_dict = {}  # If file doesn't exist, start fresh

    words_dict[english_word] = arabic_word  # Add new word

    with open("words.json", "w", encoding="utf-8") as file:
        json.dump(words_dict, file, ensure_ascii=False, indent=4)

    #print(f"✅ Word added: {english_word} → {arabic_word}")

def load_words():
    
    try:
        with open("words.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
            return {}  # Return empty if file not found or invalid


async def start(update: Update, context: CallbackContext) -> int:
    
    reply_keyboard = [['ADD NEW WORD', 'END', 'PRACTICE']]
    await update.message.reply_text(
        "Welcome! Choose an option:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return ENGLISH

async def get_english_word(update: Update, context: CallbackContext) -> int:
    
    text = update.message.text.strip()

    # Check if user just clicked ADD NEW WORD
    if text == "ADD NEW WORD":
        context.user_data["awaiting_english"] = True
        await update.message.reply_text("Please enter an English word:")
        return ENGLISH

    # Only accept English input if flagged
    if context.user_data.get("awaiting_english"):
        context.user_data["english_word"] = text
        context.user_data["awaiting_english"] = False  # Reset the flag
        await update.message.reply_text("Now send me the Arabic translation:")
        return ARABIC

    # Unrecognized input
    await update.message.reply_text("Please select a valid option from the menu.")
    return ENGLISH

async def get_arabic_word(update: Update, context: CallbackContext) -> int:
    
    english_word = context.user_data.get("english_word")  # Retrieve stored English word
    arabic_word = update.message.text.strip()  # Get Arabic input

    if english_word:
        save_to_json(english_word, arabic_word)
        await update.message.reply_text(f"✅ Saved: {english_word} → {arabic_word}")
    else:
        await update.message.reply_text("Something went wrong. Please start again.")

   
        #await start(update, context)  # Return to main menu
    return ENGLISH

async def practice(update: Update, context: CallbackContext) -> int:
    words = load_words()
    if len(words) < 4:
        await update.message.reply_text("Not enough words to practice. Add more words first.")
        return ENGLISH

    english_word = random.choice(list(words.keys()))
    correct_arabic = words[english_word]

    # Get 3 wrong options
    wrong_options = [words[k] for k in random.sample(list(words.keys() - {english_word}), 3)]
    options = wrong_options + [correct_arabic]
    random.shuffle(options)

    context.user_data['correct_arabic'] = correct_arabic
    context.user_data['current_english'] = english_word

    #keyboard = [[opt] for opt in options] + [['END']]
    keyboard = [
        [InlineKeyboardButton(text=opt, callback_data=opt)] for opt in options
            ]
    keyboard.append([InlineKeyboardButton("❌ END", callback_data="END")])  # optional

    reply_markup = InlineKeyboardMarkup(keyboard)

    target_message = update.message or update.callback_query.message

    await target_message.reply_text(
        f"What is the Arabic translation of '{english_word}'?",
        #reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        reply_markup=reply_markup
    )
    return PRACTICE


async def check_practice_answer(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    selected = query.data
    correct = context.user_data.get('correct_arabic')

    if selected == "END":
        await query.edit_message_text("Practice ended. See you next time!")
        return ConversationHandler.END

    if selected == correct:
        await query.edit_message_text(f"✅ Correct! '{selected}' is the right answer.")
    else:
        await query.edit_message_text(f"❌ Incorrect. The correct answer was: {correct}")

    return await practice(update, context)  # Ask next question




async def cancel(update: Update, context: CallbackContext) -> int:
    
    await update.message.reply_text("Practice ended. See you next time!")
    return ConversationHandler.END

def main():
    
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ENGLISH: [
                    MessageHandler(filters.Regex("^END$"), cancel),  # ✅ First, check if user wants to end
                    MessageHandler(filters.Regex("^ADD NEW WORD$"), get_english_word),
                    MessageHandler(filters.Regex("^PRACTICE$"), practice),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_english_word)
                    ],
            ARABIC: [
                    MessageHandler(filters.Regex("^END$"), cancel),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, get_arabic_word),
                    ], 
            PRACTICE: [
                    MessageHandler(filters.Regex("^ADD NEW WORD$"), get_english_word),
                    CallbackQueryHandler(check_practice_answer)
                    ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()