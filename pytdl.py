import tkinter as tk
from tkinter import ttk, messagebox
import yt_dlp
import re
import os
import sys
import threading
from queue import Queue

class YouTubeDownloader:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("PYTDL_0.1")
        self.window.configure(bg="#2b2b2b")
        self.window.geometry("600x400")
        self.window.minsize(600, 400)
        self.queue = Queue()
        self.stop_requested = False
        self.downloading = False
        self.current_process = None

        self.mode_var = tk.StringVar(value="video")
        
        self.create_mode_selector()
        self.create_video_frame()
        self.create_audio_frame()
        self.create_log_section()

        self.last_progress = ""
        self.current_file = ""

        self.window.after(100, self.process_queue)

        if getattr(sys, 'frozen', False):
            # Если программа скомпилирована
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # Если запущена из исходного кода
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.ffmpeg_path = os.path.join(self.base_dir, "ffmpeg")

        if not os.path.exists(self.ffmpeg_path):
            raise FileNotFoundError(f"Папка ffmpeg не найдена: {self.ffmpeg_path}")
        
        self.ffmpeg_exe = os.path.join(self.ffmpeg_path, "ffmpeg.exe")
        
        if not os.path.exists(self.ffmpeg_exe):
            raise FileNotFoundError(f"ffmpeg.exe не найден: {self.ffmpeg_exe}")

        self.window.bind_all("<Control-Key>", self.CopyPaste)

    def CopyPaste(self, event):
        """Обработчик клавиатуры для Ctrl+комбинаций"""
        if event.keycode == 86 and event.keysym != 'v':
            event.widget.event_generate('<<Paste>>')
            return "break"
        elif event.keycode == 67 and event.keysym != 'c':
            event.widget.event_generate('<<Copy>>')
            return "break"
        elif event.keycode == 88 and event.keysym != 'x':
            event.widget.event_generate('<<Cut>>')
            return "break"
        elif event.keycode == 65 and event.keysym != 'a':
            event.widget.tag_add('sel', '1.0', 'end')
            return "break"

    def create_log_section(self):
        self.log_frame = tk.Frame(self.window, bg="#2b2b2b", padx=5, pady=5)
        self.log_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, state='disabled',
                               bg="#1a1a1a", fg="#ffffff", insertbackground="white", height=5)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def stop_download(self):
        self.stop_requested = True
        self.append_log("[ИНФО] Остановка скачивания...")
        self.video_stop_btn.configure(state='disabled')
        self.audio_stop_btn.configure(state='disabled')
        

    def append_log(self, message, replace_last=False):
        self.log_text.configure(state='normal')
        if replace_last and self.last_progress:
            self.log_text.delete("end-2l", "end-1c")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        if replace_last:
            self.last_progress = message
        else:
            self.last_progress = ""

    def process_queue(self):
        while not self.queue.empty():
            item = self.queue.get()

            if isinstance(item, tuple) and len(item) == 2:
                msg_type, msg = item
                if msg_type == "progress":
                    self.append_log(msg, replace_last=True)
                else:
                    self.append_log(msg)
            else:
                self.append_log(str(item))
        
        self.window.after(100, self.process_queue)

    def validate_url(self, url):
        return re.match(r'https?://(?:www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/', url)

    def create_mode_selector(self):
        mode_frame = tk.Frame(self.window, bg="#2b2b2b")
        mode_frame.pack(pady=10)
        
        tk.Radiobutton(
            mode_frame, text="Видео", variable=self.mode_var, value="video",
            command=self.switch_mode, bg="#2b2b2b", fg="white", selectcolor="#2b2b2b"
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Radiobutton(
            mode_frame, text="Аудио", variable=self.mode_var, value="audio",
            command=self.switch_mode, bg="#2b2b2b", fg="white", selectcolor="#2b2b2b"
        ).pack(side=tk.LEFT, padx=10)

    def create_video_frame(self):
        self.video_frame = tk.Frame(self.window, bg="#2b2b2b")
        
        tk.Label(self.video_frame, text="Ссылка на видео/плейлист:", bg="#2b2b2b", fg="white").pack(pady=5)
        self.video_entry = tk.Text(self.video_frame, height=3, width=50, bg="#4b4b4b", fg="white")
        self.video_entry.pack(pady=5)
        
        quality_frame = tk.Frame(self.video_frame, bg="#2b2b2b")
        quality_frame.pack(pady=5)
        tk.Label(quality_frame, text="Качество:", bg="#2b2b2b", fg="white").pack(side=tk.LEFT)

        self.video_quality = ttk.Combobox(quality_frame, values=["480", "720", "1080"], state="readonly")
        self.video_quality.current(1)
        self.video_quality.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            self.video_frame, text="Скачать", command=self.start_download,
            bg="#4b4b4b", fg="white"
        ).pack(side=tk.LEFT, padx=120)

        self.video_stop_btn = tk.Button(
            self.video_frame, text="Стоп", command=self.stop_download,
            bg="#4b4b4b", fg="white", state='disabled'
        )
        self.video_stop_btn.pack(side=tk.RIGHT, padx=120)

    def create_audio_frame(self):
        self.audio_frame = tk.Frame(self.window, bg="#2b2b2b")
        
        tk.Label(self.audio_frame, text="Ссылка на аудио/плейлист:", bg="#2b2b2b", fg="white").pack(pady=5)
        self.audio_entry = tk.Text(self.audio_frame, height=3, width=50, bg="#4b4b4b", fg="white")
        self.audio_entry.pack(pady=5)
        
        quality_frame = tk.Frame(self.audio_frame, bg="#2b2b2b")
        quality_frame.pack(pady=5)
        tk.Label(quality_frame, text="Качество:", bg="#2b2b2b", fg="white").pack(side=tk.LEFT)

        self.audio_quality = ttk.Combobox(quality_frame, values=["128", "192", "320"], state="readonly")
        self.audio_quality.current(2)
        self.audio_quality.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            self.audio_frame, text="Скачать", command=self.start_download,
            bg="#4b4b4b", fg="white"
        ).pack(side=tk.LEFT, padx=120)

        self.audio_stop_btn = tk.Button(
            self.audio_frame, text="Стоп", command=self.stop_download,
            bg="#4b4b4b", fg="white", state='disabled'
        )
        self.audio_stop_btn.pack(side=tk.RIGHT, padx=120)

    def switch_mode(self):
        if self.mode_var.get() == "video":
            self.audio_frame.pack_forget()
            self.video_frame.pack()
        else:
            self.video_frame.pack_forget()
            self.audio_frame.pack()

    def start_download(self):
        if self.downloading:
            messagebox.showwarning("Ошибка", "Скачивание уже в процессе!")
            return

        self.downloading = True
        self.stop_requested = False
        self.video_stop_btn.configure(state='normal')
        self.audio_stop_btn.configure(state='normal')
        threading.Thread(target=self.download_process, daemon=True).start()

    def download_process(self):
        try:
            mode = self.mode_var.get()
            url = self.video_entry.get("1.0", tk.END).strip() if mode == "video" else self.audio_entry.get("1.0", tk.END).strip()
            
            if not self.validate_url(url):
                self.queue.put("[ОШИБКА] Неверный формат ссылки!")
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
                    'format': f"bestvideo[height<={self.video_quality.get()}]+bestaudio/best",
                    'postprocessors': [{
                        'key': 'FFmpegVideoRemuxer',
                        'preferedformat': 'mp4',
                        }],
                })
            else:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(download_path, '%(artist)s - %(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': self.audio_quality.get(),
                    }]
                })

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.current_process = ydl
                ydl.download([url])

        except Exception as e:
            self.queue.put(f"[ОШИБКА] {str(e)}")
        finally:
            self.downloading = False
            self.video_stop_btn.configure(state='disabled')
            self.audio_stop_btn.configure(state='disabled')
            self.queue.put("[ИНФО] Скачивание завершено!")

    def progress_hook(self, d):
        if self.stop_requested:
            raise Exception("Скачивание остановлено пользователем!")

        if d['status'] == 'downloading':
            if 'filename' in d:
                fname = os.path.basename(d['filename'])
                self.current_file = fname.split('.')[0]
            
            percent = d.get('_percent_str', '0.0%').strip()
            total = d.get('_total_bytes_str', '?').strip()
            speed = d.get('_speed_str', '?').strip()
            
            percent = re.sub(r'\x1b\[[0-9;]*[mK]', '', percent)
            total = re.sub(r'\x1b\[[0-9;]*[mK]', '', total)
            speed = re.sub(r'\x1b\[[0-9;]*[mK]', '', speed)
            
            progress_msg = f"[ЗАГРУЗКА] {percent} | {total} | {speed}/s"
            
            self.queue.put(("progress", progress_msg))
        
        elif d['status'] == 'finished':
            fname = os.path.basename(d['filename'])
            self.queue.put(("info", f"[УСПЕХ] Файл сохранен"))
            self.current_file = ""

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

    def run(self):
        self.switch_mode()
        self.window.mainloop()

if __name__ == "__main__":
    app = YouTubeDownloader()
    app.run()