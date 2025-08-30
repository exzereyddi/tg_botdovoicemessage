import telebot
import os
import tempfile
import subprocess
from pathlib import Path
import mimetypes

# НАСТРОЙКИ
BOT_TOKEN = "nothing"
bot = telebot.TeleBot(BOT_TOKEN)

# тут укажи путь до ffmpeg.exe
# если ffmpeg в PATH — оставь просто "ffmpeg"
# FFMPEG_PATH = "ffmpeg"
FFMPEG_PATH = r"C:\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
# это пример моего патча. ( не фулл )
def download_to_temp(file_id: str, suggested_name: str = "") -> str:
    info = bot.get_file(file_id)
    data = bot.download_file(info.file_path)
    ext = Path(info.file_path).suffix or Path(suggested_name).suffix or ""
    fd, tmp = tempfile.mkstemp(suffix=ext if ext else "")
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(data)
    return tmp


def convert_to_voice(input_path: str) -> str:
    """Перекодируем в формат Telegram voice (ogg/opus 48kHz mono)"""
    out_path = tempfile.mktemp(suffix=".ogg")
    cmd = [
        FFMPEG_PATH, "-y",
        "-i", input_path,
        "-vn",
        "-ac", "1",           # моно
        "-ar", "48000",       # 48 kHz
        "-c:a", "libopus",
        "-b:a", "32k",
        "-vbr", "on",
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out_path):
        raise RuntimeError("Ошибка при конвертации через ffmpeg")
    return out_path


def handle_and_reply(chat_id: int, file_id: str, filename_hint: str = ""):
    src_path = download_to_temp(file_id, filename_hint)
    try:
        ogg_path = convert_to_voice(src_path)
        with open(ogg_path, "rb") as voice:
            bot.send_voice(chat_id, voice)
    finally:
        try: os.remove(src_path)
        except: pass
        try: os.remove(ogg_path)
        except: pass


# === ХЕНДЛЕРЫ ===
@bot.message_handler(content_types=['audio'])
def handle_audio(msg):
    handle_and_reply(msg.chat.id, msg.audio.file_id, msg.audio.file_name or "audio")


@bot.message_handler(content_types=['voice'])
def handle_voice(msg):
    bot.send_voice(msg.chat.id, msg.voice.file_id)


@bot.message_handler(content_types=['video'])
def handle_video(msg):
    handle_and_reply(msg.chat.id, msg.video.file_id, "video.mp4")


@bot.message_handler(content_types=['video_note'])
def handle_video_note(msg):
    handle_and_reply(msg.chat.id, msg.video_note.file_id, "circle.mp4")


@bot.message_handler(content_types=['document'])
def handle_document(msg):
    filename = msg.document.file_name or "file"
    mime = msg.document.mime_type or mimetypes.guess_type(filename)[0] or ""
    if mime.startswith("audio/") or mime.startswith("video/"):
        handle_and_reply(msg.chat.id, msg.document.file_id, filename)
    else:
        bot.reply_to(msg, "Это не аудио/видео файл")


# === СТАРТ ===
print("Бот запущен (использует ffmpeg)")
bot.infinity_polling()

