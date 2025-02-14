from yt_dlp import YoutubeDL
import json
import pandas as pd

# def my_hook(d):
#     if d['status'] == 'downloading':
#         print(f"Baixando: { round(100 * float( d['downloaded_bytes'] / d['total_bytes'] ), 2) } %")

# options = {
#             'format': '303',  # Define o formato desejado (apenas o vídeo)
#             'outtmpl': 'video_teste.mp4',  # Define o nome do arquivo de saída
#             'progress_hooks': [my_hook],
#             'quiet': True 
# }

video_url = "https://www.youtube.com/watch?v=FcXOxbKlcHA"
ydl_opts = {
    'quiet': True,
    'skip_download': True,

}

with YoutubeDL(ydl_opts) as ydl:
    values = ydl.extract_info (video_url, download=False)


print(values.keys())

print(values['webpage_url'])

with open("teste.json", "w") as f:
    json.dump(values, f)