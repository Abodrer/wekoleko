import os, re, glob, time, logging, requests
from io import BytesIO
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

logging.basicConfig(filename='bot_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', '', title)

def download_thumbnail(url):
    try:
        r = requests.get(url, timeout=10)
        return BytesIO(r.content) if r.status_code == 200 else None
    except Exception as e:
        logging.error(f"فشل تحميل الصورة المصغرة: {e}")
        return None

def get_cookie_file(url):
    domains = {
        'youtube': 'cookies_youtube.txt',
        'youtu': 'cookies_youtube.txt',
        'instagram': 'cookies_instagram.txt',
        'facebook': 'cookies_facebook.txt',
        'fb': 'cookies_facebook.txt',
        'tiktok': 'cookies_tiktok.txt'
    }
    for key, file in domains.items():
        if key in url:
            path = os.path.join(os.path.dirname(__file__), file)
            return path if os.path.isfile(path) else None
    return None

class MediaBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.download_path = os.path.expanduser("~/downloads")
        self.temp_path = os.path.expanduser("~/tmp")
        os.makedirs(self.download_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)
        os.environ["TMPDIR"] = self.temp_path
        self.messages = ["جارٍ تحميل الميديا... ⏳", "يتم معالجة الرابط... ⏳", "جارٍ إرسال الملف... ⏳"]
        self.register_handlers()

    def extract_info(self, url):
        try:
            with yt_dlp.YoutubeDL({'noplaylist': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'غير معروف'),
                    'views': info.get('view_count', 0),
                    'author': info.get('artist') or info.get('uploader', 'غير معروف'),
                    'thumbnail': info.get('thumbnail')
                }
        except Exception as e:
            logging.error(f"فشل استخراج معلومات الفيديو: {e}")
            return None

    def get_ydl_opts(self, file_type, chat_id, info, url):
        base = {
            'outtmpl': os.path.join(self.download_path, f"{chat_id}_%(title)s.%(ext)s"),
            'noplaylist': True,
            'write_thumbnail': file_type in ['mp4', 'mp3']
        }
        cookie_file = get_cookie_file(url)
        if cookie_file:
            base['cookiefile'] = cookie_file

        if file_type == 'mp4':
            base.update({
                'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][filesize<48M]',
                'merge_output_format': 'mp4'
            })
        elif file_type == 'mp3':
            base.update({
                'format': 'bestaudio',
                'outtmpl': os.path.join(self.download_path, f"{chat_id}_%(title)s.mp3"),
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'},
                    {'key': 'FFmpegMetadata', 'add_metadata': True},
                    {'key': 'EmbedThumbnail'}
                ],
                'postprocessor_args': ['-metadata', f'title={info["title"]}', '-metadata', f'artist={info["author"]}']
            })
        elif file_type == 'voice':
            base.update({
                'format': 'bestaudio',
                'outtmpl': os.path.join(self.download_path, f"{chat_id}_%(title)s.ogg"),
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'opus'},
                    {'key': 'FFmpegMetadata', 'add_metadata': True}
                ],
                'postprocessor_args': ['-metadata', f'title={info["title"]}', '-metadata', f'artist={info["author"]}']
            })
        return base

    def create_keyboard(self):
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("📹 فيديو MP4", callback_data="mp4"),
            InlineKeyboardButton("🎶 صوت MP3", callback_data="mp3"),
            InlineKeyboardButton("🎙️ بصمة صوتية", callback_data="voice"),
            InlineKeyboardButton("🖼️ صورة مصغرة", callback_data="thumbnail")
        )
        kb.add(InlineKeyboardButton("📞 الدعم والمطور", url="https://t.me/oli17"))
        kb.add(InlineKeyboardButton("📱 واتساب: 07874557280", url="https://wa.me/9647874557280"))
        return kb

    def cleanup(self, chat_id, title):
        for file in glob.glob(os.path.join(self.download_path, f"{chat_id}_*{sanitize_filename(title)}*.*")):
            os.remove(file)

    def send_file(self, chat_id, path, file_type, info, thumb):
        with open(path, 'rb') as f:
            send_funcs = {
                'mp4': lambda: self.bot.send_video(chat_id, f, caption=f"فيديو: {info['title']}", supports_streaming=True, thumb=thumb),
                'mp3': lambda: self.bot.send_audio(chat_id, f, title=info['title'], performer=info['author'], caption=f"صوت: {info['title']}", thumb=thumb),
                'voice': lambda: self.bot.send_voice(chat_id, f, caption=f"🎙️ بصمة: {info['title']}")
            }
            send_funcs.get(file_type, lambda: None)()

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def welcome(msg):
            self.bot.reply_to(msg, "مرحبًا! أرسل رابط الميديا لتحميله بصيغ متعددة.")

        @self.bot.message_handler(func=lambda m: m.text and m.text.startswith(('http://', 'https://')))
        def handle_url(msg):
            info = self.extract_info(msg.text)
            if not info:
                return self.bot.reply_to(msg, "⚠️ لم أستطع استخراج المعلومات.")

            chat_id = msg.chat.id
            data = {'url': msg.text, 'info': info, 'url_msg': msg.message_id}
            caption = f"📺 العنوان: {info['title']}\n👁️‍🗨️ المشاهدات: {info['views']:,}\n🎤 المؤلف: {info['author']}"
            thumb = download_thumbnail(info['thumbnail']) if info['thumbnail'] else None
            msg_func = self.bot.send_photo if thumb else self.bot.send_message
            sent_msg = msg_func(chat_id, thumb or caption, caption=caption if thumb else None, reply_markup=self.create_keyboard())
            self.bot.set_state(msg.from_user.id, "waiting", chat_id)
            with self.bot.retrieve_data(msg.from_user.id, chat_id) as d:
                d.update(data, choice_msg=sent_msg.message_id)

        @self.bot.callback_query_handler(func=lambda c: True)
        def handle_choice(call):
            user, chat = call.from_user.id, call.message.chat.id
            with self.bot.retrieve_data(user, chat) as data:
                url, info = data.get('url'), data.get('info')
                file_type = call.data
                if file_type == "thumbnail":
                    thumb = download_thumbnail(info['thumbnail'])
                    if thumb: self.bot.send_photo(chat, thumb, caption=info['title'])
                    else: self.bot.answer_callback_query(call.id, "⚠️ لا يمكن تحميل الصورة")
                    return self.cleanup(chat, info['title'])

                msg = self.bot.send_message(chat, self.messages[0])
                try:
                    ydl_opts = self.get_ydl_opts(file_type, chat, info, url)
                    file_path = ""
                    sanitized = sanitize_filename(info['title'])

                    for _ in range(3):
                        pattern = os.path.join(self.download_path, f"{chat}_*{sanitized}*.*")
                        paths = glob.glob(pattern)
                        if not paths:
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([url])
                            paths = glob.glob(pattern)
                        if paths:
                            file_path = paths[0]
                            break
                        time.sleep(2)

                    if not file_path: raise FileNotFoundError("⚠️ لم يتم العثور على الملف.")
                    if os.path.getsize(file_path) > 48 * 1024 * 1024:
                        return self.bot.edit_message_text("⚠️ الملف أكبر من 48MB", chat, msg.message_id)

                    for m in self.messages[1:]:
                        self.bot.edit_message_text(m, chat, msg.message_id)
                        time.sleep(1)

                    self.send_file(chat, file_path, file_type, info, download_thumbnail(info['thumbnail']))
                    self.cleanup(chat, info['title'])
                    self.bot.delete_message(chat, msg.message_id)
                    self.bot.send_message(chat, f"✅ تم التحميل: {file_type.upper()}")
                except Exception as e:
                    self.bot.edit_message_text(f"❌ فشل التحميل: {e}", chat, msg.message_id)
                    logging.error(f"فشل التحميل: {e}")
                finally:
                    self.bot.delete_state(user, chat)

    def run(self):
        print("🤖 البوت يعمل الآن...")
        self.bot.infinity_polling(timeout=10, long_polling_timeout=5, interval=0, none_stop=True)

if __name__ == "__main__":
    TOKEN = "7385925406:AAEQ9G4NjjHWpATuA7jur7HiRE0fmaF2tgk"
    MediaBot(TOKEN).run()
