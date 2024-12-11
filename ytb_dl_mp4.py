import os
import re
import yt_dlp

# Папка для сохранения скачанных файлов
download_folder = 'download'

# Создание папки, если она не существует
if not os.path.exists(download_folder):
    os.makedirs(download_folder)

# Путь к файлу со ссылками
links_file = 'links.txt'

# Указание желаемого разрешения (например, '720' или '480')
desired_resolution = '720'  # Измените это значение для выбора разрешения

# Проверка наличия файла со ссылками
if not os.path.exists(links_file):
    print(f"Файл {links_file} не найден.")
else:
    # Функция для скачивания видео по ссылке
    def download_video(url):
        # Формат для скачивания на основе желаемого разрешения
        format_string = f"bestvideo[height<={desired_resolution}]+bestaudio/best"
        
        ydl_opts = {
            'format': format_string,
            'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),  # Формат имени файла
            'noplaylist': False,  # Не скачивать плейлисты
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([url])
            except Exception as e:
                print(f"Произошла ошибка при загрузке видео: {url}. Ошибка: {e}")

    # Чтение ссылок из текстового файла
    with open(links_file, 'r') as file:
        urls = file.readlines()

    # Проверка наличия ссылок и их валидности
    valid_urls = []
    for url in urls:
        stripped_url = url.strip()
        if stripped_url:  # Проверяем, что строка не пустая
            if re.match(r'https?://(?:www\.)?(?:youtube\.com|youtu\.be)/', stripped_url) and 'music' not in stripped_url:
                valid_urls.append(stripped_url)
            else:
                print(f"Неверный формат ссылки: {stripped_url}")
        else:
            print("Пустая строка в файле. Пропускаем.")

    # Проверка, есть ли валидные ссылки для скачивания
    if not valid_urls:
        print("Нет валидных ссылок для скачивания.")
    else:
        # Скачивание видео для каждой валидной ссылки
        for url in valid_urls:
            download_video(url)
