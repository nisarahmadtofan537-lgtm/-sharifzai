import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# د لاګنګ تنظیمات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔴 ستاسو د بوټ ټوکن او چینل تنظیمات په مستقیم ډول دلته اضافه شول
BOT_TOKEN = "8604114942:AAH5u6SD80a7WIHZmlb2wfe0edzQSUyaf30"
CHANNEL_ID = "@PRO_EDITORS_AFG"
CHANNEL_LINK = "https://t.me/PRO_EDITORS_AFG"

user_data_store = {}

# د چینل د غړیتوب چک کول
async def is_user_subscribed(app: Application, user_id: int) -> bool:
    try:
        member = await app.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        # د دې لپاره چې بوټ د ایډمین توب د تېروتنې له امله بند نشي، کارونکي ته اجازه ورکوي
        return True

# سټارټ کمانډ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_sub = await is_user_subscribed(context.application, user.id)
    if not is_sub:
        keyboard = [
            [InlineKeyboardButton("📢 زموږ چینل ته ننوځئ", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ ما چینل تعقیب کړ (تایید)", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"سلام {user.first_name} وروره! \n\nد ربات د کارولو لپاره لومړی باید زموږ په چینل کې غړی شئ:",
            reply_markup=reply_markup
        )
        return

    await update.message.reply_text(f"سلام {user.first_name}!\nد ویډیو لینک راولیږئ ترڅو په لوړ کیفیت کې یې درته ډانلوډ کړم. ⚡")

# د بټنو مدیریت
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if data == "check_sub":
        is_sub = await is_user_subscribed(context.application, user_id)
        if is_sub:
            await query.edit_message_text("تشکر! ستاسو غړیتوب تایید شو. اوس کولی شئ د ویډیو لینک راولېږئ. 🚀")
        else:
            keyboard = [
                [InlineKeyboardButton("📢 زموږ چینل ته ننوځئ", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ ما چینل تعقیب کړ (تایید)", callback_data="check_sub")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ تاسو لاهم په چینل کې غړي شوي نه یاست. هیله ده لومړی چینل جوین کړئ:", reply_markup=reply_markup)
            
    elif data.startswith("dl_"):
        _, user_id_str, download_type, format_id = data.split("_", 3)
        if str(user_id) != user_id_str:
            return
            
        stored = user_data_store.get(user_id)
        if not stored:
            await query.edit_message_text("تېروتنه: لینک زوړ شوی، مهرباني وکړئ بیا یې راولیږئ.")
            return

        url = stored['url']
        await query.edit_message_text("⏳ فایل په خورا تیز سرعت سره ډانلوډ کیږي، هیله ده لږ انتظار وکړئ...")

        if download_type == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': format_id,
                }],
                'quiet': True
            }
        else:
            ydl_opts = {
                'format': f'{format_id}+bestaudio/best',
                'outtmpl': f'downloads/{user_id}_%(id)s.%(ext)s',
                'max_filesize': 300 * 1024 * 1024,
                'quiet': True
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if download_type == "audio":
                    base, _ = os.path.splitext(filename)
                    filename = base + ".mp3"
                elif not os.path.exists(filename):
                    base, _ = os.path.splitext(filename)
                    for f in os.listdir('downloads'):
                        if f.startswith(os.path.basename(base)):
                            filename = os.path.join('downloads', f)
                            break

                if download_type == "audio":
                    await query.message.reply_chat_action("upload_document")
                    with open(filename, 'rb') as audio_file:
                        await query.message.reply_audio(audio=audio_file, caption="🎵 ستاسو آډیو فایل واخلئ!\n\n@PRO_EDITORS_AFG ربات 🇦🇫")
                else:
                    await query.message.reply_chat_action("upload_video")
                    with open(filename, 'rb') as video_file:
                        await query.message.reply_video(video=video_file, caption="🎬 ستاسو ویډیو واخلئ!\n\n@PRO_EDITORS_AFG ربات 🇦🇫")
                
                if os.path.exists(filename):
                    os.remove(filename)
                del user_data_store[user_id]
                await query.delete_message()
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            await query.message.reply_text("❌ بښنه غواړم، د فایل په ډانلوډ کولو کې ستونزه راغله یا فایل تر 300MB غټ دی.")

# د لینک پروسس کول
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text

    is_sub = await is_user_subscribed(context.application, user_id)
    if not is_sub:
        keyboard = [
            [InlineKeyboardButton("📢 زموږ چینل ته ننوځئ", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ ما چینل تعقیب کړ (تایید)", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⛔ د لینک پروسس کولو لپاره لومړی باید په چینل کې غړی شئ:", reply_markup=reply_markup)
        return

    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ هیله ده یو صحیح لینک راولېږئ.")
        return

    status_msg = await update.message.reply_text("🔍 د لینک چک کول او د کیفیتونو راویستل...")

    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            title = info.get('title', 'Video')
            duration_seconds = info.get('duration', 0)
            duration_minutes = duration_seconds // 60
            
            keyboard = []
            seen_resolutions = set()
            
            for f in formats:
                res = f.get('height')
                ext = f.get('ext')
                if res and res not in seen_resolutions and ext == 'mp4' and res in:
                    filesize = f.get('filesize') or f.get('filesize_approx')
                    if filesize:
                        size_mb = filesize / (1024 * 1024)
                        if size_mb > 300: continue
                        size_str = f"{size_mb:.1f}M" if size_mb >= 1 else f"{int(size_mb * 1024)}K"
                    else:
                        size_str = "؟"
                        
                    seen_resolutions.add(res)
                    button_text = f"🎥 {res}p - {size_str}"
                    callback_data = f"dl_{user_id}_video_{f['format_id']}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            keyboard.sort(key=lambda x: int(x.split().replace('p', '')), reverse=True)

            audio_buttons = []
            for kbps in ["128", "320"]:
                approx_audio_size_mb = (int(kbps) * 1000 * duration_seconds) / (8 * 1024 * 1024)
                if approx_audio_size_mb >= 1:
                    audio_size_str = f"{approx_audio_size_mb:.1f}M"
                else:
                    audio_size_str = f"{int(approx_audio_size_mb * 1024)}K"
                    
                audio_buttons.append(InlineKeyboardButton(f"🎵 {kbps}kbps - {audio_size_str}", callback_data=f"dl_{user_id}_audio_{kbps}"))
            
            if audio_buttons:
                keyboard.append(audio_buttons)
            
            if not keyboard:
                await status_msg.edit_text("❌ بښنه غواړم، د دې ویډیو مناسب کیفیتونه پیدا نشول.")
                return
                
            user_data_store[user_id] = {'url': url}
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            caption_text = f"📌 {title}\n\n⏱ زمان: {duration_minutes} دقیقه\n\n👇 کدوم کیفیت رو میخوای؟ روش کلیک کن"
            await status_msg.edit_text(caption_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error extracting formats: {e}")
        await status_msg.edit_text("❌ د لینک په لوستلو کې تېروتنه راغله. ډاډ ترلاسه کړئ چې لینک سم دی.")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    application.run_polling()

if __name__ == '__main__':
    main()
