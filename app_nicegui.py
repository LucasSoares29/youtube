import pandas as pd
import unidecode
import sys
import re 
import ffmpeg
import os
import threading
import time
from yt_dlp import YoutubeDL
from nicegui import app, ui

"""
videos do youtube 1080p premium nao tem informação sobre tamanho do video
tamanho do video = duração * bitrate do video
como conseguir duração???
https://www.youtube.com/watch?v=yB1e4DEpu5o

não detecta lives
https://youtube.com/live/XXEEi31-l00

nao usar chamada de cmd para coletar informações do video. olhar teste-ytdlp.py

"""
# Expressão regular para validar URLs de vídeos do YouTube
YOUTUBE_REGEX = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([\w\-]+)([&\w=]*|youtu\.be/live/)([\w\-]+)([&\w=]*|youtube\.com/live/)([\w\-]+)([&\w=]*)?$'
)

chosen_resolution = ""
chosen_codec = ""
chosen_id_audio = -1
chosen_id_video = -1
nome_video = ""
chosen_audio_codec = ""

global download_button

def ensure_downloaded_folder():
    """
    Verifica se a pasta de download existe. Se não existir, cria a pasta.
    """
    current_directory = os.path.dirname(os.path.abspath(__file__))

    if not os.path.exists(os.path.join(current_directory, "downloaded")):
        os.makedirs(os.path.join(current_directory, "downloaded"))
        print(f"Pasta criada: {os.path.join(current_directory, 'downloaded')}")
    else:
        print(f"A pasta já existe: {os.path.join(current_directory, 'downloaded')}")

def carregarTabela(video_url):
    """
    Função para carregar a tabela com as informações do video
    Parâmetro de entrada: video_url (String)
    """
    global nome_video

    yt = YoutubeDL()
    video_info = yt.extract_info(url=video_url, download=False)
    formats = video_info['formats']

    # Extraindo o nome do video, retirando acentos e pontuações
    nome_video = video_info['title']
    nome_video = unidecode.unidecode(nome_video)
    nome_video = nome_video.rstrip(".")  # Remove o ponto final do final do nome
    nome_video = nome_video.replace(":", "") # Remove os dois pontos
    # nome_video = nome_video.lower().replace(' ', '_').replace('|', '').replace('#', '').replace('?', '').replace('-', '').replace('/', '-').replace('[', '').replace(']', '')
    nome_video = re.sub(r"[|#?\[\]/-]", "", nome_video)  # Remove os caracteres indesejados
    nome_video = re.sub(r"\s+", "_", nome_video)  # Substitui espaços por "_"
    nome_video = nome_video.lower()  # Converte para minúsculas
    ui.label(f"Nome do video: {nome_video}")

    # Exibindo a tabela completa (video/audio)
    tabela_formatos = pd.DataFrame(formats)
    colunas_filtro = ["format_id", "format_note", "ext", "fps", "acodec", "vcodec",  "resolution", "audio_ext", "video_ext", "dynamic_range", "vbr", "abr", "tbr"]
    
    # Nem todo video aparece
    if "audio_channels" in tabela_formatos.columns:
        colunas_filtro.append("audio_channels")
    if "filesize" in tabela_formatos.columns:
        colunas_filtro.append("filesize")
    
    tabela_formatos = tabela_formatos[colunas_filtro]
    return tabela_formatos

def convert_size(b):
    """
    Recebe um arquivo em KB de entrada (Ex: 1.345.198). 
    Retorna o valor em MB se for menor que 1GB.
    Retorna o valor em GB se for maior do que 1GB.

    Parâmetro de entrada: kb (Int ou Float)
    Parâmetro de Saída: String.
    """
    kb = b / 1024
    mb = b / (1024 * 1024)  # Convertendo para MB
    gb = mb / 1024  # Convertendo para GB
    if gb >= 1:
        return f"{gb:.2f} GB"
    elif mb >= 1:
        return f"{mb:.2f} MB"
    else:
        return f"{kb:.2f} KB"
    
def format_vbr(value):
    """
    Converte o valor para float e arredonda para duas casas decimais
    Parâmetro de entrada: value (Float)
    Parâmetro de saída: Float
    """
    return round(float(value), 2)   

def get_index(df, format_note, ext):
    """
    Função para encontrar o format_id pelo format_note e ext
    Parâmetros de entrada:
    df -> Dataframe
    format_note, ext -> String

    Parâmetro de saida: Int
    """
    result = df[(df["format_note"] == format_note) & (df["ext"] == ext)]
    return result.format_id.tolist()[0] if not result.empty else None

def get_audio_codec(df, format_id):
    """
    Função para encontrar o codec de audio pelo format_id
    Parâmetros de entrada:
    df -> Dataframe
    format_id -> String

    Parâmetro de saida: String
    """
    result = df[(df["format_id"] == format_id)]
    return result.audio_ext.tolist()[0] if not result.empty else None

def run_ffmpeg(video_input, audio_input, output_file):
    try:
        input_v = ffmpeg.input(video_input)
        input_a = ffmpeg.input(audio_input)
        output_file += ".mp4"
        ffmpeg.output(input_v, input_a, output_file, c="copy").run(overwrite_output=True)
        print("Processamento do video finalizado")

        path_video = f"./downloaded/video_{nome_video}.{chosen_codec}"
        path_audio = f"./downloaded/audio_{nome_video}.{chosen_audio_codec}"

        # apaga arquivos baixados
        if os.path.exists(path_video):
            os.remove(path_video)
        if os.path.exists(path_audio):
            os.remove(path_audio)
    except Exception as e:
        print(f"Erro ao processar vídeo: {e}")

def load_youtube_player(video_id):
    """
    Função para carregar o player do YouTube
    Parâmetro de entrada: video_id (String)
    """
    print(video_id)
    embed_url = f'https://www.youtube.com/embed/{video_id}'
    ui.html(f'<iframe width="640" height="360" src="{embed_url}" frameborder="0" allowfullscreen></iframe>')
    
def carregarTabelaVideo(df_tabela_info):
    
    """
    Esta função recebe um DataFrame com informações completas dos vídeos e
    retorna um DataFrame filtrado contendo apenas as colunas relacionadas a vídeos.

    Caso tenha a informação do tamanho do video, ele trata os dados originais e retorna
    em MB ou GB. (Ex: 2,014,329,118 kb = 1,92 GB)

    Para o bitrate de video (coluna vbr), ele arredonda para duas casas decimais.
    (Ex: 14593,452 kbps = 14593,45 kbps)

    Parâmetros:
    df_tabela_info (pd.DataFrame): DataFrame contendo as informações completas dos vídeos.
    Retorna:
    pd.DataFrame: DataFrame filtrado contendo apenas as colunas relacionadas a vídeos, 
                  incluindo "format_id", "resolution", "fps", "format_note", "ext", 
                  "video_ext", "vbr (kbps)" e, se disponível, "filesize(mb)".

    
    """
    
    tabela_formatos_video = df_tabela_info[df_tabela_info['video_ext'].isin(["mp4", "webm"])]
    tabela_formatos_video = tabela_formatos_video.loc[~(tabela_formatos_video.format_note.isnull())]
    colunas_filtro_video = ["format_id","resolution", "fps",  "format_note", "ext", 
                            "video_ext", "vbr"]
    
    # tratamento dos numeros na coluna vbr
    tabela_formatos_video['vbr (kbps)'] = tabela_formatos_video['vbr'].apply(format_vbr)
    colunas_filtro_video = [col for col in colunas_filtro_video if col != "vbr"]  # Remove "vbr"
    colunas_filtro_video.append("vbr (kbps)")  # Adiciona "vbr (kbps)"
    
    if "filesize" in df_tabela_info.columns:
        tabela_formatos_video['filesize(mb)'] = tabela_formatos_video['filesize'].apply(convert_size)
        tabela_formatos_video.drop('filesize', axis=1, inplace=True)
        colunas_filtro_video.append("filesize(mb)")

    return tabela_formatos_video[colunas_filtro_video]

def carregarTabelaAudio(df_tabela_info):
    """
    Esta função recebe um DataFrame com informações completas dos vídeos e
    retorna um DataFrame filtrado contendo apenas as colunas relacionadas a audio.
    
    Parâmetros:
    df_tabela_info (pd.DataFrame): DataFrame contendo as informações completas dos vídeos.
    Retorna:
    pd.DataFrame: DataFrame filtrado contendo apenas as colunas relacionadas a audio, 
                  incluindo "format_id", "ext", "abr", "acodec", "audio_ext", 
                  e, se disponível, "audio_channels".
    """
    tabela_formatos_audio = df_tabela_info.loc[df_tabela_info.audio_ext != "none"]
    tabela_formatos_audio = tabela_formatos_audio[tabela_formatos_audio['audio_ext'].isin(["m4a", "webm"])]
    tabela_formatos_audio = tabela_formatos_audio[~tabela_formatos_audio['format_id'].apply(lambda x: x.endswith('-drc'))]
    colunas_filtro_audio = ["format_id", "ext", "abr", "acodec", "audio_ext"]

    if "audio_channels" in df_tabela_info.columns:
        colunas_filtro_audio.append("audio_channels")

    tabela_formatos_audio = tabela_formatos_audio[colunas_filtro_audio]

    return tabela_formatos_audio[colunas_filtro_audio]

def my_hook(d):
    """
    Atualiza barra de progresso do download do video
    """
    try:
        if d['status'] == 'downloading':
            percent = float(d['downloaded_bytes'] / d['total_bytes'])
            if progress_bar:
                progress_bar.set_value(f"{percent}")
                label.set_text(f'Downloading video... {percent*100:.2f}%')
        else:
            label.set_text(f'Downloading video complete!')
    except KeyError:
        # No caso dos videos premium que nao tem o tamanho do video
        if d['status'] == 'downloading':
            label.set_text(f'Downloading video...')
        else:
            progress_bar.set_value(1.0)
            label.set_text(f'Downloading video complete!')

def my_hook_audio(d):
    """
    Atualiza barra de progresso do download do áudio
    """
    try:
        if d['status'] == 'downloading':
            label_audio.set_text(f'Downloading audio...')
            percent_audio = float(d['downloaded_bytes'] / d['total_bytes'])
            if progress_bar_2:
                progress_bar_2.set_value(f"{percent_audio}")
                label_audio.set_text(f'Downloading audio... {percent_audio*100:.2f}%')
        else:
            label_audio.set_text(f'Downloading audio complete!')
    except KeyError:
        # Caso não tenha tamanho do audio
        label_audio.set_text(f'Downloading audio...')
        if d['status'] != 'downloading':
            progress_bar.set_value(1)
            label.set_text(f'Downloading audio complete!')
    
def download_video(video_url, chosen_id_video, chosen_codec, chosen_id_audio, chosen_audio_codec):
    """
    Função para baixar o video com as configurações escolhidas
    Parâmetros de entrada:
    video_url -> String
    chosen_id_video -> int
    chosen_id_audio -> int
    """


    ui.notify("Começando o download...")
    global percent, label, spinner, progress_bar, spinner_audio, label_audio, progress_bar_2, percent_audio
    download_button.set_enabled(False)
    percent = 0
    percent_audio = 0

   
    def _download(stop_event):

        while not stop_event.is_set():
            print("Thread rodando...")

            def _download_audio():
                if stop_event.is_set():
                    return
                
                options = {
                    'format': f"{chosen_id_audio}",  # Define o formato desejado (apenas o vídeo)
                    'outtmpl': f"./downloaded/audio_{nome_video}.{chosen_audio_codec}",  # Define o nome do arquivo de saída
                    'quiet': True,  # Para suprimir a saída no console (opcional)
                    'progress_hooks': [my_hook_audio]
                }

                yt = YoutubeDL(options)
                yt.download(video_url)
                yt.close() # fecho o youtube-dl

                # Processa o video
                run_ffmpeg(video_input=f"./downloaded/video_{nome_video}.{chosen_codec}",
                           audio_input=f"./downloaded/audio_{nome_video}.{chosen_audio_codec}",
                           output_file=f"./downloaded/{nome_video}")

                stop_event.set()


            options = {
                'format': f"{chosen_id_video}",  # Define o formato desejado (apenas o vídeo)
                'outtmpl': f"./downloaded/video_{nome_video}.{chosen_codec}",  # Define o nome do arquivo de saída
                'quiet': True,  # Para suprimir a saída no console (opcional)
                'progress_hooks': [my_hook]
            }

            yt = YoutubeDL(options)
            yt.download(video_url)

            if stop_event.is_set():
                break

            _download_audio()

        print("Thread finalizada.")


        

    with ui.row() as row:
        row.set_visibility(True)
        spinner = ui.spinner(size='lg')
        label = ui.label(f'Downloading video...')

        # global progress_bar
        progress_bar = ui.linear_progress(value=0, show_value=False)

        spinner_audio = ui.spinner(size='lg')
        label_audio = ui.label(f'Aguardando término do download do video...')
        progress_bar_2 = ui.linear_progress(value=0, show_value=False)
        
        stop_event = threading.Event()

        # Criando uma nova thread para rodar o download
        thread = threading.Thread(target=_download, args=(stop_event,))
        thread.start()
        
    def check_download():
        if stop_event.is_set():
            ui.notify("Download concluido!")
            row.set_visibility(False)
            timer.deactivate()  # Desativa o timer após a primeira execução
            ui.button('restart app', on_click=lambda: os.utime('app_nicegui.py'))

    def check_exists_audio_video():
        path_video = f"./downloaded/video_{nome_video}.{chosen_codec}"
        path_audio = f"./downloaded/audio_{nome_video}.{chosen_audio_codec}"
        if os.path.exists(path_video) and os.path.exists(path_audio):
            ui.notify("Começando processamento do video")
            timer2.deactivate()  # Desativa o timer após a primeira execução

    

    timer = ui.timer(0.5, check_download)  # Verifica a cada 500ms 
    timer2 = ui.timer(0.5, check_exists_audio_video)  # Verifica a cada 500ms
    

def selecting_video_audio_settings_to_download_video():
    """
    Função para validar o link do vídeo e selecionar as configurações de vídeo e audio para download
    """
    options_codec = ["Selecione um codec"]

    def options_codec(df_video, event):
        """
        Função para gerar as opções de codec no select_2 e armazenar a resolucao escolhida"""
        global chosen_resolution

        chosen_resolution = event.value
        options_codec = df_video.loc[df_video['format_note'] == str(chosen_resolution), 'ext']\
                    .drop_duplicates().to_list()
        options_codec.insert(0, "Selecione um codec")  
        select_2.set_options(options_codec)
        select_2.set_value("Selecione um codec")

    def on_select_2_change(event, df_video):
        """
        Função para armazenar o codec escolhido na variável global chosen_codec
        """
        global chosen_codec
        global chosen_id_video
        global chosen_resolution

        chosen_codec = event.value
        # if chosen_codec:
        #     print(f"Codec escolhido: {chosen_codec}")

        chosen_id_video = get_index(df_video, chosen_resolution, chosen_codec)

        # if chosen_id_video:
        #     print(f"ID Video escolhido: {chosen_id_video}")

    def on_select_3_change(event):
        """
        Função para armazenar o id do audio escolhido na variável global chosen_id_audio    
        """
        global chosen_id_audio
        global chosen_audio_codec
        chosen_id_audio = event.value
        chosen_audio_codec = get_audio_codec(df_audio, chosen_id_audio)
        
        if chosen_id_audio:
            print(f"ID de audio escolhido: {chosen_id_audio}")
            print(f"Codec de audio escolhido: {chosen_audio_codec}")


    url = video_url.value.strip()

    match = YOUTUBE_REGEX.match(url)
    
    if match:
        ensure_downloaded_folder()
        video_id = match.group(4)
        resultado_label.set_text('✅ Link válido: é um vídeo do YouTube!')
        # Carrega o player do YouTube
        load_youtube_player(video_id)

        # Carrega as informações do video
        tabela_info = carregarTabela(url)
        ui.label("Tabela de informações do video")
        ui.table.from_pandas(carregarTabelaVideo(tabela_info))

        df_video = carregarTabelaVideo(tabela_info)

        # Gera dois selectboxes com resolução e bitrate
        resolucoes = df_video['format_note'].drop_duplicates().to_list()
        resolucoes.insert(0, "Selecione uma resolução")
        
        select_1 = ui.select(options=resolucoes, 
                             label="Selecione uma resolução",
                             value="Selecione uma resolução",
                             on_change=lambda event: options_codec(df_video, event)).classes('w-96')
        
        select_2 = ui.select(options=["Selecione uma resolução primeiro"],
                             label="Selecione um codec",
                             value="Selecione uma resolução primeiro",
                             on_change=lambda event2: on_select_2_change(event2, df_video)).classes('w-96')
        
        ui.label("Tabela de informações do audio")
        ui.table.from_pandas(carregarTabelaAudio(tabela_info))

        df_audio = carregarTabelaAudio(tabela_info)

        options_id_audio = df_audio['format_id'].drop_duplicates().to_list()
        options_id_audio.insert(0, "Escolha o ID da qualidade de audio desejada")

        select_3 = ui.select(options_id_audio, 
                             label="Escolha o ID da qualidade de audio desejada",
                             value="Escolha o ID da qualidade de audio desejada",
                             on_change=lambda event3: on_select_3_change(event3)).classes('w-96')   
        
        global download_button
        download_button = ui.button('Download video...', on_click=lambda: download_video(url, chosen_id_video, chosen_codec, chosen_id_audio, chosen_audio_codec))
    else:
        resultado_label.set_text('❌ Link inválido! Insira um link de vídeo do YouTube.')


 


# Create a title using nicegui for my page
ui.markdown('##App YouTube Video Extraction')

# Create a text input using nicegui for my page
video_url = ui.input(label='Insira o link do video', 
                     placeholder="Cole um link válido do YouTube",
                     on_change=selecting_video_audio_settings_to_download_video).props('rounded standout').classes('w-96') # Input para o link do video

resultado_label = ui.label('')


ui.run(native=True)