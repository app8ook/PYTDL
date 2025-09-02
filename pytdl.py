from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QIcon
import yt_dlp
import re
import os
import sys
import threading
from queue import Queue

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

class YouTubeDownloader(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PYTDL_0.2")
        self.resize(600, 400)

        icon_path = resource_path("Kosou.ico")
        self.setWindowIcon(QIcon(icon_path))

        self.queue = Queue()
        self.stop_requested = False
        self.downloading = False
        self.current_process = None
        self.mode_var = "video"

        self.audio_qual = ""
        self.video_qual = ""

        # Основной layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Кнопки переключения режимов
        self.video_btn = QtWidgets.QPushButton("Видео")
        self.audio_btn = QtWidgets.QPushButton("Аудио")
        self.video_btn.setCheckable(True)
        self.audio_btn.setCheckable(True)
        self.video_btn.setChecked(True)  # Начальный режим — Видео

        self.mode_group = QtWidgets.QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.video_btn)
        self.mode_group.addButton(self.audio_btn)

        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(self.video_btn)
        mode_layout.addWidget(self.audio_btn)

        # Поле для ссылки и выбор качества
        self.url_label = QtWidgets.QLabel("Ссылка:")
        self.url_text = QtWidgets.QTextEdit()
        self.url_text.setFixedHeight(60)

        self.quality_label = QtWidgets.QLabel("Качество:")
        self.quality_combo = QtWidgets.QComboBox()

        # Размещаем элементы
        self.main_layout.addLayout(mode_layout)
        self.main_layout.addWidget(self.url_label)
        self.main_layout.addWidget(self.url_text)

        quality_layout = QtWidgets.QHBoxLayout()
        quality_layout.addWidget(self.quality_label)
        quality_layout.addWidget(self.quality_combo)
        self.main_layout.addLayout(quality_layout)

        self.quality_combo.currentTextChanged.connect(self.on_quality_changed)

        self.download_btn = QtWidgets.QPushButton("Скачать")
        self.download_btn.clicked.connect(self.start_download)
        self.stop_btn = QtWidgets.QPushButton("Стоп")
        self.stop_btn.clicked.connect(self.stop_download)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.download_btn)
        btn_layout.addWidget(self.stop_btn)
        self.main_layout.addLayout(btn_layout)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.main_layout.addWidget(self.log_text)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.process_queue)
        self.timer.start(100)

        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        self.update_quality()

        # Настройка пути к ffmpeg
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.ffmpeg_path = os.path.join(self.base_dir, "ffmpeg")

        if not os.path.exists(self.ffmpeg_path):
            raise FileNotFoundError(f"Папка ffmpeg не найдена: {self.ffmpeg_path}")

        self.ffmpeg_exe = os.path.join(self.ffmpeg_path, "ffmpeg.exe")

        if not os.path.exists(self.ffmpeg_exe):
            raise FileNotFoundError(f"ffmpeg.exe не найден: {self.ffmpeg_exe}")

    def on_mode_changed(self, button):
        if button == self.video_btn:
            self.mode_var = "video"
        else:
            self.mode_var = "audio"
            
        self.update_quality()

    def update_quality(self):
        if self.video_btn.isChecked():
            self.quality_combo.clear()
            self.quality_combo.addItems(["480", "720", "1080"])
        else:
            self.quality_combo.clear()
            self.quality_combo.addItems(["128", "192", "320"])

    def on_quality_changed(self, text):
        if self.mode_var == "video":
            self.video_qual = text
        else:
            self.audio_qual = text

    def start_download(self):
        if self.downloading:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Скачивание уже в процессе!")
            return

        self.downloading = True
        self.stop_requested = False

        threading.Thread(target=self.download_process, daemon=True).start()

    def stop_download(self):
        if self.downloading == False:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Ничего не скачивается")
            return

        self.stop_requested = True
        self.append_log("[ИНФО] Остановка скачивания...")

    def clean_ansi(self, text):
        ansi_escape = re.compile(r'\x1b\[([0-9;]*m)')
        return ansi_escape.sub('', text)

    def append_log(self, message, replace_last=False):
        message = self.clean_ansi(message)
        if replace_last:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            cursor.select(QtGui.QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deletePreviousChar()
        self.log_text.append(message)

    def process_queue(self):
        while not self.queue.empty():
            item = self.queue.get()
            if isinstance(item, tuple) and len(item) == 2:
                msg_type, msg = item
                if msg_type == "progress_value":
                    self.progress_bar.setValue(int(msg))
                elif msg_type == "progress_text":
                    self.append_log(msg, replace_last=True)
                else:
                    self.append_log(msg)
            else:
                self.append_log(str(item))

    def validate_url(self, url):
        return re.match(r'https?://(?:www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/', url)

    def download_process(self):
        try:
            mode = self.mode_var
            url = self.url_text.toPlainText().strip()

            if not self.validate_url(url):
                self.queue.put(("error", "[ОШИБКА] Неверный формат ссылки!"))
                self.downloading = False
                return

            download_path = os.path.join(os.getcwd(), 'download')
            os.makedirs(download_path, exist_ok=True)

            ydl_opts = {
                'ffmpeg_location': self.ffmpeg_path,
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'logger': self.YTDLPLogger(self.queue),
                'noplaylist': True,
            }

            if mode == "video":
                ydl_opts.update({
                    'format': f"bestvideo[height<={self.video_qual}]+bestaudio/best",
                    'postprocessors': [{
                        'key': 'FFmpegVideoRemuxer',
                        'preferedformat': 'mp4',
                    }],
                })
            else:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': self.audio_qual
                    }]
                })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.current_process = ydl
                ydl.download([url])

        except Exception as e:
            self.queue.put(("error", f"[ОШИБКА] {str(e)}"))
        finally:
            self.downloading = False
            self.queue.put(("info", "[ИНФО] Скачивание завершено!"))
            self.progress_bar.setValue(100)

    def progress_hook(self, d):
        if self.stop_requested:
            raise Exception("Скачивание остановлено пользователем!")

        if d['status'] == 'downloading':
            # Попробуем получить название из info_dict
            info = d.get('info_dict', {})
            title = info.get('title') if info else None
            if title is None:
                title = "N/A"

            percent_str = d.get('_percent_str', '0.0%').strip()
            percent_clean = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
            try:
                percent_val = float(percent_clean.replace('%', ''))
            except:
                percent_val = 0
            speed_clean = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_speed_str', '?').strip())

            progress_msg = f"[ЗАГРУЗКА] {title} | {percent_clean} | {speed_clean}/s"

            self.queue.put(("progress_value", percent_val))
            self.queue.put(("progress_text", progress_msg))

        elif d['status'] == 'finished':
            fname = os.path.basename(d['filename'])
            self.queue.put(("info", f"[УСПЕХ] Файл сохранен: {fname}"))

    class YTDLPLogger:
        def __init__(self, queue):
            self.queue = queue

        def debug(self, msg):
            if msg.startswith('[download] Destination:'):
                fname = msg.split('Destination:')[-1].strip()
                fname = os.path.basename(fname).split('.')[0]
                self.queue.put(("info", f"[СКАЧИВАНИЕ] {fname}"))

        def warning(self, msg):
            msg = re.sub(r'\x1b\[[0-9;]*[mK]', '', msg)
            self.queue.put(("warning", msg))

        def error(self, msg):
            msg = re.sub(r'\x1b\[[0-9;]*[mK]', '', msg)
            self.queue.put(("error", msg))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Загрузка стилей из style.qss
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as style_file:
            app.setStyleSheet(style_file.read())

    downloader = YouTubeDownloader()
    downloader.show()
    sys.exit(app.exec_())
    
#pyinstaller --onefile -w --icon=Kosou.ico --name=PYTDL --add-data "style.qss;." --add-data "Kosou.ico;." pytdl.py