import yt_dlp
video_url = "https://youtu.be/IKR73dnTFWs?si=TJEZfgcFpbsqirQe"

ydl_opts = { 
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
    'outtmpl': '%(title)s.%(ext)s',}
print("Началась загрузка..")

with yt_dlp.YoutubeDL(ydl_opts) as ydl: 
    ydl.download([video_url])
print("скачано")
