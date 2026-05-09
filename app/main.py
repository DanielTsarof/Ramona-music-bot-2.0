import yt_dlp

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    # Для отладки лучше временно не скрывать вывод
    "quiet": False,
    "no_warnings": False,
    "logtostderr": True,
    # Если ffmpeg не в PATH, укажи путь явно:
    # 'ffmpeg_location': '/usr/bin',
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",  # или '128', '256', '320'
        }
    ],
}

with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
    ydl.download(["https://www.youtube.com/watch?v=GpxFUo7oxWM"])
