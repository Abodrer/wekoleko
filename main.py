import os
import re
import time
import glob
import logging
import requests
from io import BytesIO
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# إعداد تسجيل الأخطاء
logging.basicConfig(filename='bot_errors.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def sanitize_filename(title):
    """إزالة الأحرف غير الصالحة من أسماء الملفات."""
    return re.sub(r'[\\/*?:"<>|]', "", title)


class MediaBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.download_path = os.path.expanduser("~/downloads")
        self.temp_path = os.path.expanduser("~/tmp")
        os.makedirs(self.download_path, exist_ok=True)
        os.makedirs(self.temp_path, exist_ok=True)
        os.environ["TMPDIR"] = self.temp_path

        # تعيين مسار ملف الكوكيز في جذر مشروع Replit
        self.cookie_file = os.path.join(os.getcwd(), "cookies.txt")
        print(f"مسار ملف الكوكيز: {self.cookie_file}")
        print("هل ملف الكوكيز موجود؟", os.path.isfile(self.cookie_file))

        self.loading_msgs = [
            "جارٍ تحميل الميديا... ⏳",
            "يتم معالجة الرابط... ⏳",
            "جارٍ إرسال الملف... ⏳"
        ]

        self.register_handlers()

    def download_thumbnail(self, url):
        try:
            response = requests.get(url, timeout=10)
            return BytesIO(response.content) if response.status_code == 200 else None
        except Exception as e:
            logging.error(f"فشل تحميل الصورة المصغرة: {str(e)}")
            return None

    def cleanup_files(self, chat_id, title):
        try:
            pattern = os.path.join(self.download_path, f"{chat_id}_*{sanitize_filename(title)}*.*")
            for file_path in glob.glob(pattern):
                os.remove(file_path)
        except Exception as e:
            logging.error(f"فشل تنظيف الملفات: {str(e)}")

    def get_ydl_opts(self, file_type, chat_id, info_dict):
        base_opts = {
            'outtmpl': os.path.join(self.download_path, f'{chat_id}_%(title)s.%(ext)s'),
            'noplaylist': True,
            'write_thumbnail': file_type in ['mp3', 'mp4'],
        }
        # إضافة ملف الكوكيز لو موجود
        if os.path.isfile(self.cookie_file):
            base_opts['cookiefile'] = self.cookie_file

        if file_type == 'mp4':
            base_opts.update({
                'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][filesize<48M]',
                'merge_output_format': 'mp4',
            })
        elif file_type == 'mp3':
            base_opts.update({
                'format': 'bestaudio',
                'outtmpl': os.path.join(self.download_path, f'{chat_id}_%(title)s.mp3'),
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
                    {'key': 'FFmpegMetadata', 'add_metadata': True},
                    {'key': 'EmbedThumbnail'}
                ],
                'postprocessor_args': [
                    '-metadata', f'title={info_dict.get("title", "")}',
                    '-metadata', f'artist={info_dict.get("artist", info_dict.get("uploader", "Unknown Artist"))}',
                ]
            })
        elif file_type == 'voice':
            base_opts.update({
                'format': 'bestaudio',
                'outtmpl': os.path.join(self.download_path, f'{chat_id}_%(title)s.ogg'),
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'opus', 'preferredquality': '64'},
                    {'key': 'FFmpegMetadata', 'add_metadata': True}
                ],
                'postprocessor_args': [
                    '-metadata', f'title={info_dict.get("title", "")}',
                    '-metadata', f'artist={info_dict.get("artist", info_dict.get("uploader", "Unknown Artist"))}',
                ]
            })

        return base_opts

    def create_format_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📹 فيديو MP4", callback_data="mp4"),
            InlineKeyboardButton("🎶 صوت MP3", callback_data="mp3"),
            InlineKeyboardButton("🎙️ بصمة صوتية", callback_data="voice"),
            InlineKeyboardButton("🖼️ صورة مصغرة", callback_data="thumbnail"),
        )
        return keyboard

    def extract_video_info(self, url):
        ydl_opts = {'noplaylist': True}
        if os.path.isfile(self.cookie_file):
            ydl_opts['cookiefile'] = self.cookie_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'غير معروف'),
                    'views': info.get('view_count', 0),
                    'author': info.get('artist', info.get('uploader', 'غير معروف')),
                    'thumbnail': info.get('thumbnail')
                }
        except Exception as e:
            logging.error(f"فشل استخراج معلومات الفيديو: {str(e)}")
            return None

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            self.bot.reply_to(message, (
                "مرحبًا! أرسل رابط الميديا (يوتيوب، إنستغرام، تويتر، إلخ) وسأساعدك في تحميله "
                "بصيغة MP4، MP3، بصمة صوتية، أو الصورة المصغرة."
            ))

        @self.bot.message_handler(content_types=['text'])
        def handle_url(message):
            url = message.text.strip()
            chat_id = message.chat.id

            if not url.startswith(('http://', 'https://')):
                self.bot.reply_to(message, "⚠️ الرابط غير صالح. أرسل رابطًا يبدأ بـ http:// أو https://")
                return

            info = self.extract_video_info(url)
            if not info:
                self.bot.reply_to(message, "⚠️ لا يمكن استخراج معلومات الفيديو. حاول مرة أخرى.")
                return

            self.bot.set_state(message.from_user.id, 'waiting_for_format', chat_id)
            with self.bot.retrieve_data(message.from_user.id, chat_id) as data:
                data['url'] = url
                data['url_message_id'] = message.message_id
                data['info'] = info

            caption = (
                f"📺 العنوان: {info['title']}\n"
                f"👀 المشاهدات: {info['views']:,}\n"
                f"🎤 المؤلف: {info['author']}"
            )
            thumbnail = self.download_thumbnail(info['thumbnail']) if info['thumbnail'] else None

            if thumbnail:
                choice_msg = self.bot.send_photo(
                    chat_id, thumbnail, caption=caption,
                    reply_markup=self.create_format_keyboard()
                )
            else:
                choice_msg = self.bot.reply_to(
                    message, caption, reply_markup=self.create_format_keyboard()
                )

            with self.bot.retrieve_data(message.from_user.id, chat_id) as data:
                data['choice_message_id'] = choice_msg.message_id

        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_format_selection(call):
            chat_id = call.message.chat.id
            user_id = call.from_user.id
            file_type = call.data

            with self.bot.retrieve_data(user_id, chat_id) as data:
                url = data.get('url')
                url_message_id = data.get('url_message_id')
                choice_message_id = data.get('choice_message_id')
                info = data.get('info')

            if not url:
                self.bot.answer_callback_query(call.id, "⚠️ أرسل رابط الميديا مرة أخرى.")
                self.bot.delete_state(user_id, chat_id)
                return

            if file_type == 'thumbnail':
                thumbnail = self.download_thumbnail(info['thumbnail']) if info['thumbnail'] else None
                if thumbnail:
                    self.bot.send_photo(chat_id, thumbnail, caption=f"🖼️ الصورة المصغرة: {info['title']}")
                else:
                    self.bot.answer_callback_query(call.id, "⚠️ لا يمكن تحميل الصورة المصغرة.")
                self.bot.delete_message(chat_id, choice_message_id)
                self.bot.delete_message(chat_id, url_message_id)
                self.bot.delete_state(user_id, chat_id)
                return

            self.bot.answer_callback_query(call.id, f"جارٍ تحميل {file_type.upper()}...")
            loading_msg = self.bot.send_message(chat_id, self.loading_msgs[0])

            max_retries = 3
            sanitized_title = sanitize_filename(info['title'])

            for attempt in range(max_retries):
                try:
                    ydl_opts = self.get_ydl_opts(file_type, chat_id, info)

                    # تحقق إذا الملف موجود لتجنب التكرار
                    file_pattern = os.path.join(self.download_path, f"{chat_id}_*{sanitized_title}*.*")
                    file_paths = glob.glob(file_pattern)

                    if not file_paths:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info_dict = ydl.extract_info(url, download=True)
                        sanitized_title = sanitize_filename(info_dict['title'])
                        file_pattern = os.path.join(self.download_path, f"{chat_id}_*{sanitized_title}*.*")
                        file_paths = glob.glob(file_pattern)

                    if not file_paths:
                        raise FileNotFoundError("لم يتم العثور على الملف الناتج")

                    file_path = file_paths[0]
                    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    if file_size_mb > 48:
                        self.bot.edit_message_text(
                            chat_id=chat_id, message_id=loading_msg.message_id,
                            text="⚠️ الملف أكبر من 48 ميجابايت. اختر صيغة أخرى أو رابطًا مختلفًا."
                        )
                        self.cleanup_files(chat_id, sanitized_title)
                        time.sleep(5)
                        self.bot.delete_message(chat_id, loading_msg.message_id)
                        return

                    # تحديث رسائل التحميل
                    for msg in self.loading_msgs[1:]:
                        self.bot.edit_message_text(chat_id=chat_id, message_id=loading_msg.message_id, text=msg)
                        time.sleep(1)

                    # إرسال الملف حسب الصيغة
                    with open(file_path, 'rb') as file:
                        thumb = self.download_thumbnail(info['thumbnail']) if info['thumbnail'] else None
                        if file_type == 'mp4':
                            self.bot.send_video(chat_id, file, supports_streaming=True,
                                                caption=f"فيديو: {info['title']}", thumb=thumb)
                        elif file_type == 'mp3':
                            self.bot.send_audio(chat_id, file, title=info['title'], performer=info['author'],
                                                caption=f"صوت: {info['title']}", thumb=thumb)
                        elif file_type == 'voice':
                            self.bot.send_voice(chat_id, file, caption=f"بصمة صوتية: {info['title']}")

                    self.cleanup_files(chat_id, sanitized_title)
                    self.bot.delete_message(chat_id, loading_msg.message_id)
                    self.bot.delete_message(chat_id, choice_message_id)
                    self.bot.delete_message(chat_id, url_message_id)

                    success_msg = self.bot.send_message(chat_id, f"✅ تم تحميل {file_type.upper()} بنجاح.")
                    time.sleep(5)
                    self.bot.delete_message(chat_id, success_msg.message_id)
                    self.bot.delete_state(user_id, chat_id)
                    break

                except Exception as e:
                    logging.error(f"محاولة التحميل {attempt + 1} فشلت: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    self.bot.edit_message_text(
                        chat_id=chat_id, message_id=loading_msg.message_id,
                        text=f"⚠️ خطأ: {str(e)}. حاول مرة أخرى."
                    )
                    self.cleanup_files(chat_id, sanitized_title)
                    time.sleep(5)
                    self.bot.delete_message(chat_id, loading_msg.message_id)
                    self.bot.delete_state(user_id, chat_id)

    def run(self):
        print("بوت يعمل...")
        self.bot.infinity_polling(timeout=10, long_polling_timeout=5, interval=0, none_stop=True)


if __name__ == "__main__":
    TOKEN = "7385925406:AAEQ9G4NjjHWpATuA7jur7HiRE0fmaF2tgk"
    bot = MediaBot(TOKEN)
    bot.run()