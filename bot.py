import os
import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai


# ============================================================
# VIDZORAAI CONFIG
# ============================================================

# DO NOT put real secrets into a public GitHub repository.
BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "PASTE_GEMINI_API_KEY_HERE")


# Put your Telegram channels here later.
# Example: "@VidzoraAI"
REQUIRED_CHANNELS = [
    "@vidzoraaivideoprompt",
    # "@YOUR_CHANNEL_2",
]


MODEL = "gemini-2.5-flash"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("VidzoraAI")

client = None


# ============================================================
# AI
# ============================================================

def generate_ai_text(prompt: str) -> str:
    global client

    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    return response.text


async def ai(prompt: str) -> str:
    return await asyncio.to_thread(generate_ai_text, prompt)


# ============================================================
# CHANNEL CHECK
# ============================================================

async def is_channel_member(
    bot,
    user_id: int,
    channel: str
) -> bool:

    try:
        member = await bot.get_chat_member(
            chat_id=channel,
            user_id=user_id
        )

        return member.status in [
            "creator",
            "administrator",
            "member",
        ]

    except Exception as e:
        logger.error(
            "Channel check failed for %s: %s",
            channel,
            e
        )

        return False


async def check_required_channels(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:

    if not REQUIRED_CHANNELS:
        return True

    user = update.effective_user

    for channel in REQUIRED_CHANNELS:

        joined = await is_channel_member(
            context.bot,
            user.id,
            channel
        )

        if not joined:

            buttons = []

            for ch in REQUIRED_CHANNELS:

                buttons.append([
                    InlineKeyboardButton(
                        f"📢 Join {ch}",
                        url=f"https://t.me/{ch.replace('@', '')}"
                    )
                ])

            buttons.append([
                InlineKeyboardButton(
                    "✅ I've Joined",
                    callback_data="check_join"
                )
            ])

            keyboard = InlineKeyboardMarkup(buttons)

            text = (
                "🔐 *VidzoraAI Access Required*\n\n"
                "Before using VidzoraAI, please join "
                "our Telegram channel(s).\n\n"
                "After joining, tap *I've Joined*."
            )

            if update.callback_query:

                await update.callback_query.message.edit_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )

            else:

                await update.message.reply_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )

            return False

    return True


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "🎬 Video Prompt",
                callback_data="video_prompt"
            ),
            InlineKeyboardButton(
                "🖼️ Image → Prompt",
                callback_data="image_prompt"
            ),
        ],
        [
            InlineKeyboardButton(
                "📖 Story Generator",
                callback_data="story"
            ),
            InlineKeyboardButton(
                "🎥 Scene Generator",
                callback_data="scene"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎙️ Voiceover Prompt",
                callback_data="voiceover"
            ),
            InlineKeyboardButton(
                "💡 Video Ideas",
                callback_data="ideas"
            ),
        ],
        [
            InlineKeyboardButton(
                "✨ Prompt Enhancer",
                callback_data="enhancer"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await check_required_channels(
        update,
        context
    ):
        return

    user = update.effective_user

    text = (
        f"🚀 *Welcome to VidzoraAI, {user.first_name}!*\n\n"
        "Your AI assistant for creating viral video content.\n\n"
        "Choose what you want to create:"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


# ============================================================
# BUTTON HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    if query.data == "check_join":

        if not await check_required_channels(
            update,
            context
        ):
            return

        await query.message.edit_text(
            "✅ *Access Granted!*\n\n"
            "Welcome to VidzoraAI 🤖\n\n"
            "Choose a tool below:",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

        return

    # Every feature checks membership.
    if not await check_required_channels(
        update,
        context
    ):
        return

    feature = query.data

    prompts = {

        "video_prompt":
            "🎬 *Video Prompt Creator*\n\n"
            "Send me your video idea.\n\n"
            "Example:\n"
            "`A futuristic city in Lagos at night`",

        "image_prompt":
            "🖼️ *Image → Video Prompt*\n\n"
            "Send me an image and I will create "
            "a detailed AI video prompt from it.",

        "story":
            "📖 *Story Generator*\n\n"
            "Tell me your story idea.\n\n"
            "Example:\n"
            "`A scary story about a mysterious house`",

        "scene":
            "🎥 *Scene Generator*\n\n"
            "Send me your story or video idea and "
            "I will break it into cinematic scenes.",

        "voiceover":
            "🎙️ *Voiceover Prompt*\n\n"
            "Send me your video topic or story and "
            "I will create a professional voiceover script.",

        "ideas":
            "💡 *Viral Video Ideas*\n\n"
            "Tell me your niche.\n\n"
            "Example:\n"
            "`faceless horror`",

        "enhancer":
            "✨ *Prompt Enhancer*\n\n"
            "Send me any basic AI video prompt and "
            "I will make it more detailed and cinematic.",
    }

    if feature in prompts:

        context.user_data["feature"] = feature

        await query.message.edit_text(
            prompts[feature],
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Main Menu",
                        callback_data="home"
                    )
                ]
            ])
        )


# ============================================================
# TEXT MESSAGE HANDLER
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await check_required_channels(
        update,
        context
    ):
        return

    feature = context.user_data.get("feature")

    if not feature:
        await update.message.reply_text(
            "Please choose a tool from the menu 👇",
            reply_markup=main_menu()
        )
        return

    user_text = update.message.text

    await update.message.reply_text(
        "⏳ *VidzoraAI is creating your result...*",
        parse_mode="Markdown"
    )

    prompts = {

        "video_prompt": f"""
You are VidzoraAI, a professional AI video prompt creator.

Create a highly detailed cinematic AI video generation prompt
from this idea:

{user_text}

Include:
- Subject
- Environment
- Action
- Camera movement
- Camera angle
- Lighting
- Atmosphere
- Visual style
- Motion
- Details
- Quality

Make it suitable for modern AI video generators.
Return ONLY the final prompt.
""",

        "story": f"""
You are VidzoraAI Story Generator.

Create an engaging short-form video story based on:

{user_text}

Include:
- Strong hook
- Characters
- Story development
- Conflict
- Emotional moment
- Twist or satisfying ending

Make it suitable for TikTok, Reels and YouTube Shorts.
""",

        "scene": f"""
You are VidzoraAI Scene Generator.

Turn this idea into a cinematic sequence:

{user_text}

Create 5 scenes.

For each scene include:
1. Scene description
2. AI video prompt
3. Camera movement
4. Lighting
5. Character action
6. Sound/environment
7. Transition

Keep visual consistency between scenes.
""",

        "voiceover": f"""
You are VidzoraAI Voiceover Generator.

Create a powerful voiceover script for:

{user_text}

Include:
- Hook
- Narration
- Emotional delivery
- Pauses
- Ending CTA

Make it natural and suitable for short-form video.
""",

        "ideas": f"""
You are VidzoraAI Viral Video Idea Generator.

Generate 10 original viral faceless video ideas for:

{user_text}

For each idea include:
- Title
- Hook
- Concept
- Why viewers may watch
- Suggested visual style
""",

        "enhancer": f"""
You are VidzoraAI Prompt Enhancer.

Improve this basic prompt:

{user_text}

Make it highly detailed and cinematic.

Add:
- Subject details
- Environment
- Camera
- Lens
- Movement
- Lighting
- Atmosphere
- Composition
- Realism
- Visual effects

Return the enhanced prompt only.
""",
    }

    if feature == "image_prompt":

        await update.message.reply_text(
            "🖼️ Please send an image to continue."
        )
        return

    prompt = prompts.get(feature)

    if not prompt:

        await update.message.reply_text(
            "Please choose a feature first.",
            reply_markup=main_menu()
        )
        return

    try:

        result = await ai(prompt)

        await update.message.reply_text(
            f"✨ *VidzoraAI Result*\n\n{result}",
            parse_mode="Markdown"
        )

    except Exception as e:

        logger.error(
            "AI error: %s",
            e
        )

        await update.message.reply_text(
            "❌ Something went wrong while connecting "
            "to the AI.\n\n"
            "Please try again."
        )


# ============================================================
# IMAGE HANDLER
# ============================================================

async def image_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await check_required_channels(
        update,
        context
    ):
        return

    feature = context.user_data.get("feature")

    if feature != "image_prompt":

        await update.message.reply_text(
            "Choose 🖼️ Image → Prompt from the menu first."
        )

        return

    await update.message.reply_text(
        "🖼️ Image received!\n\n"
        "⏳ Analyzing the image..."
    )

    try:

        photo = update.message.photo[-1]

        telegram_file = await context.bot.get_file(
            photo.file_id
        )

        file_path = f"/tmp/{photo.file_id}.jpg"

        await telegram_file.download_to_drive(
            file_path
        )

        def analyze_image():

            global client

            if client is None:
                client = genai.Client(
                    api_key=GEMINI_API_KEY
                )

            uploaded = client.files.upload(
                file=file_path
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=[
                    uploaded,
                    """
Analyze this image and create a detailed AI video
generation prompt.

Describe:
- Main subject
- Appearance
- Environment
- Action possibilities
- Camera angle
- Camera movement
- Lighting
- Atmosphere
- Cinematic style
- Motion
- Visual details

Return a professional video-generation prompt.
"""
                ]
            )

            return response.text

        result = await asyncio.to_thread(
            analyze_image
        )

        await update.message.reply_text(
            f"🎬 *Image → Video Prompt*\n\n{result}",
            parse_mode="Markdown"
        )

    except Exception as e:

        logger.error(
            "Image error: %s",
            e
        )

        await update.message.reply_text(
            "❌ I couldn't analyze that image.\n\n"
            "Please try another image."
        )


# ============================================================
# HOME BUTTON
# ============================================================

async def home_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    context.user_data.pop(
        "feature",
        None
    )

    await query.message.edit_text(
        "🏠 *VidzoraAI Main Menu*\n\n"
        "Choose a tool:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Unhandled error:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if BOT_TOKEN == "PASTE_BOT_TOKEN_HERE":

        print(
            "ERROR: BOT_TOKEN has not been configured."
        )

        return

    if GEMINI_API_KEY == "PASTE_GEMINI_API_KEY_HERE":

        print(
            "ERROR: GEMINI_API_KEY has not been configured."
        )

        return

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            home_handler,
            pattern="^home$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            image_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    application.add_error_handler(
        error_handler
    )

    print("VidzoraAI is running...")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
