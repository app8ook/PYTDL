import os
import yt_dlp
import re

# Папка для сохранения скачанных файлов
download_folder = 'download'

# Создание папки, если она не существует
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

# Путь к файлу со ссылками
links_file = 'links.txt'

# Проверка наличия файла со ссылками
if not os.path.exists(links_file):
    print(f"Файл {links_file} не найден.")
else:
    # Функция для скачивания аудио по ссылке
    def download_audio(url):
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),  # Путь к файлу
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    # Чтение ссылок из текстового файла
    with open(links_file, 'r') as file:
        urls = file.readlines()

    # Проверка наличия ссылок и их валидности
    valid_urls = []
    for url in urls:
        stripped_url = url.strip()
        if stripped_url:  # Проверяем, что строка не пустая
            # Проверка на соответствие формату URL
            if re.match(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be|music\.youtube\.com)/', stripped_url):
                valid_urls.append(stripped_url)
            else:
                print(f"Неверный формат ссылки: {stripped_url}")
        else:
            print("Пустая строка в файле. Пропускаем.")

    # Проверка, есть ли валидные ссылки для скачивания
    if not valid_urls:
        print("Нет валидных ссылок для скачивания.")
    else:
        # Скачивание аудио для каждой валидной ссылки
        for url in valid_urls:
            download_audio(url)
