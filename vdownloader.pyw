from __future__ import unicode_literals
from yt_dlp import YoutubeDL
import os
import pandas as pd
import unidecode

# Para imprimir toda a tabela
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

url_video = input("Insira a URL do video para baixar... ")

# Parte que imprime a tabela dos formatos
yt = YoutubeDL()
video_info = yt.extract_info(url=url_video, download=False)
formats = video_info['formats']

nome_video = video_info['title']
nome_video = unidecode.unidecode(nome_video)
nome_video = nome_video.lower().replace(' ', '_').replace('|', '').replace('#', '').replace('?', '').replace('/', '-')

tabela_formatos = pd.DataFrame(formats)
tabela_formatos = tabela_formatos[["format_id", "format_note", "ext", "fps", "acodec", "vcodec",  "resolution", "audio_ext", "video_ext", "audio_channels", "dynamic_range",
                                   "abr", "asr", "vbr"]]

# Preparando tabela de formato de videos
tabela_formatos_video = tabela_formatos.loc[tabela_formatos.video_ext != "none"]
tabela_formatos_video = tabela_formatos_video[["format_id", "format_note", "ext", "fps", "resolution",
                                                "video_ext", "vbr"]]
print("\nFORMATO DE VIDEO DISPONIVEIS:\n-------------------------------------------------------------------")
print(tabela_formatos_video)

# Perguntando formato de video
id_video = input("Insira o ID do formato de video: ")
info_video_selecionado = tabela_formatos_video.loc[tabela_formatos_video.format_id == id_video]
while info_video_selecionado.empty:
    print("ID de video não encontrado")
    id_video = input("Insira o ID do formato de video: ")
    info_video_selecionado = tabela_formatos_video.loc[tabela_formatos_video.format_id == id_video]

os.system("cls")
# Preparando tabela de formato de audio
tabela_formatos_audio = tabela_formatos.loc[tabela_formatos.audio_ext != "none"]
tabela_formatos_audio = tabela_formatos_audio[["format_id", "ext", "abr", "asr", "acodec", "audio_ext",
                                           "audio_channels"]]

print("\nFORMATO DE AUDIO DISPONIVEIS:\n-------------------------------------------------------------------")
print(tabela_formatos_audio)

# Perguntando formato de audio
id_audio = input("Insira o ID do formato de audio: ")
info_audio_selecionado = tabela_formatos_audio.loc[tabela_formatos_audio.format_id == id_audio]
while info_audio_selecionado.empty:
    print("ID de audio não encontrado")
    id_audio = input("Insira o ID do formato de audio: ")
    info_audio_selecionado = tabela_formatos_audio.loc[tabela_formatos_audio.format_id == id_audio]



os.system("cls")
print(f"BAIXANDO VIDEO....")
cmd = f"""yt-dlp -f {id_video} {url_video} -o video_{nome_video}.{info_video_selecionado['video_ext'].values[0]}"""
os.system(cmd)

os.system("cls")
print(f"BAIXANDO AUDIO....")
cmd = f"""yt-dlp -f {id_audio} {url_video} -o audio_{nome_video}.{info_audio_selecionado['audio_ext'].values[0]}"""
os.system(cmd)

os.system("cls")
print("JUNTANDO VIDEO COM AUDIO...")
cmd = f"""ffmpeg -i video_{nome_video}.{info_video_selecionado['video_ext'].values[0]} -i audio_{nome_video}.{info_audio_selecionado['audio_ext'].values[0]} -c copy {nome_video}.mp4"""
os.system(cmd)

# apagando arquivos temporários
cmd = f"del /f video_{nome_video}.{info_video_selecionado['video_ext'].values[0]} " \
      f" audio_{nome_video}.{info_audio_selecionado['audio_ext'].values[0]}"
os.system(cmd)


option = input("VIDEO BAIXANDO COM SUCESSO! Deseja converter o video para ser usado no premiere? [Y para sim].....")

if option.upper() == "Y":
    # verificar se o arquivo existe. Se existir, deleta o arquivo
    # inserir codigo pra isso


    os.system("cls")
    video_bitrate = info_video_selecionado['vbr'].values[0]
    video_resolution = info_video_selecionado['resolution'].values[0]
    audio_channels = info_audio_selecionado['audio_channels'].values[0]

    cmd = f"""NVEncC64.exe -c hevc --vbr {video_bitrate} --output-res {video_resolution} """

    if "HDR" in info_video_selecionado['format_note'].values[0]:
        cmd += "--output-depth 10 --colormatrix auto --colorprim auto --transfer auto --dhdr10-info copy "

    #print(audio_channels)
    if audio_channels == 2.0:
        cmd += "--audio-codec aac --audio-bitrate 192 "
    elif audio_channels == 6.0:
        cmd += "--audio-codec aac --audio-bitrate 384 --audio-stream 5.1 "

    cmd += f"--log-level output=error -i {nome_video}.mp4 -o converted_{nome_video}.mp4"

    print("COMEÇANDO CONVERSÃO DO VIDEO PARA ADOBE PREMIERE (HEVC).......")
    os.system(cmd)
    cmd = f"del /f {nome_video}.mp4"
    os.system(cmd)
    input("VIDEO CONVERTIDO COM SUCESSO. Aperte qualquer botão para encerrar o programa")
else:
    input("Aperte qualquer botão para encerrar o programa")



