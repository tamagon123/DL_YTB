import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import os
import sys
import urllib.request
import subprocess

# --- あなたのGitHubの最新exe配布用URLを設定してください ---
# 例: "https://github.com/YourName/YourRepo/releases/latest/download/YoutubeDownloader.exe"
GITHUB_EXE_URL = "https://ここにGitHubの直リンクを貼る"


# --- ヘルプ画面のクラス ---
class HelpWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("ヘルプ・使い方")
        self.geometry("600x450")
        self.attributes("-topmost", True)
        
        text_area = tk.Text(self, padx=15, pady=15, font=("MS Gothic", 10), wrap="word")
        text_area.pack(fill="both", expand=True)
        
        help_text = """【YouTube Pro Downloader 使い方マニュアル】

1. 基本操作
・URL欄に動画リンクを貼り付けるか、一番右の「🔍検索」ボタンで動画を探してください。
・URLを入力してEnterを押すと、自動で動画タイトルを取得し保存名にセットします。

2. 保存名のリネーム
・「保存名」の欄に入力すると、その名前で保存されます。
・空欄（グレーの文字の状態）の場合は、YouTubeのタイトルがそのまま使われます。

3. 画質・モード選択
・動画：最高画質、1080p、720p、および音声(MP3)が選択可能です。
※1080p以上の保存には、プログラムと同じフォルダに「ffmpeg.exe」が必要です。

4. キーボードショートカット
・Tabキー：次の項目へ移動
・Enterキー：入力の確定、または次の入力欄へ移動
・ボタンが選択された状態でEnter：クリックと同じ動作

5. トラブルシューティング
・「HTTP Error 403: Forbidden」が出る場合：
  YouTubeの仕様変更が原因です。コマンドプロンプトで 
  pip install -U yt-dlp 
  を実行して最新版に更新してください。
・ダウンロードが始まらない：
  インターネット接続と、ffmpeg.exeが同フォルダにあるか確認してください。
"""
        text_area.insert("1.0", help_text)
        text_area.config(state="disabled") # 編集不可にする
        
        close_btn = tk.Button(self, text="閉じる", command=self.destroy, width=15)
        close_btn.pack(pady=10)


class SearchWindow(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("YouTube 検索")
        self.callback = callback
        self.attributes("-topmost", True)
        self.focus_set()

        frame = tk.Frame(self, padx=15, pady=15)
        frame.pack(fill="x")
        tk.Label(frame, text="キーワード:").pack(side="left")
        self.search_query = tk.Entry(frame, width=50)
        self.search_query.pack(side="left", padx=10)
        self.search_query.focus_set()
        
        self.search_btn = tk.Button(frame, text="検索実行", command=self.execute_search)
        self.search_btn.pack(side="left")

        self.results_frame = tk.Frame(self, padx=15, pady=10)
        self.results_frame.pack(fill="both", expand=True)

        self.search_query.bind("<Return>", lambda e: self.execute_search())
        self.search_btn.bind("<Return>", lambda e: self.execute_search())

    def execute_search(self):
        query = self.search_query.get().strip()
        if not query: return
        for w in self.results_frame.winfo_children(): w.destroy()
        self.search_btn.config(state="disabled", text="検索中...")
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query):
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                result = ydl.extract_info(f"ytsearch10:{query}", download=False)
                if 'entries' in result:
                    self.after(0, self._display_results, result['entries'])
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.after(0, lambda: self.search_btn.config(state="normal", text="検索実行"))

    def _display_results(self, entries):
        for entry in entries:
            title = entry.get('title', 'Unknown')
            url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
            btn = tk.Button(self.results_frame, text=title, anchor="w", wraplength=550, pady=3,
                            command=lambda u=url: self.select_result(u))
            btn.pack(fill="x", pady=2)
            btn.bind("<Return>", lambda e, u=url: self.select_result(u))

    def select_result(self, url):
        self.callback(url)
        self.destroy()

class DownloadRow:
    def __init__(self, master, row_idx):
        self.frame = tk.Frame(master, pady=3)
        self.frame.grid(row=row_idx, column=0, sticky="ew")

        # 各部品の幅を広めに設定
        tk.Label(self.frame, text=f"{row_idx+1:02}: URL:", width=8).grid(row=0, column=0)
        self.url_entry = tk.Entry(self.frame, width=45) # URL欄を拡張
        self.url_entry.grid(row=0, column=1, padx=5)

        self.placeholder = "保存名(空でタイトル)"
        self.name_entry = tk.Entry(self.frame, width=35, fg='grey') # 名前欄を拡張
        self.name_entry.insert(0, self.placeholder)
        self.name_entry.grid(row=0, column=2, padx=5)

        self.mode_combo = ttk.Combobox(self.frame, width=15, state="readonly")
        self.mode_combo['values'] = ("動画:最高画質", "動画:1080p", "動画:720p", "音源:MP3")
        self.mode_combo.current(0)
        self.mode_combo.grid(row=0, column=3, padx=5)

        self.search_btn = tk.Button(self.frame, text="🔍 YouTube検索", command=self.open_search, padx=10)
        self.search_btn.grid(row=0, column=4, padx=5)

        # キーボードバインド
        for w in (self.url_entry, self.name_entry, self.mode_combo):
            w.bind("<Return>", self._focus_next)
        self.search_btn.bind("<Return>", lambda e: self.open_search())
        
        self.url_entry.bind("<FocusOut>", lambda e: self.trigger_title_fetch())
        self.name_entry.bind("<FocusIn>", self._clear_placeholder)
        self.name_entry.bind("<FocusOut>", self._add_placeholder)

    def _focus_next(self, event):
        event.widget.tk_focusNext().focus_set()
        return "break"

    def trigger_title_fetch(self):
        url = self.url_entry.get().strip()
        if url.startswith("http"):
            threading.Thread(target=self.fetch_title, args=(url,), daemon=True).start()

    def fetch_title(self, url):
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', '')
                if title: self.after_fetch(title)
        except: pass

    def after_fetch(self, title):
        if self.name_entry.get() == self.placeholder or not self.name_entry.get():
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, title)
            self.name_entry.config(fg='grey')
            self.placeholder = title

    def _clear_placeholder(self, event):
        if self.name_entry.get() == self.placeholder:
            self.name_entry.delete(0, tk.END)
            self.name_entry.config(fg='black')

    def _add_placeholder(self, event):
        if not self.name_entry.get():
            self.name_entry.insert(0, self.placeholder)
            self.name_entry.config(fg='grey')

    def open_search(self):
        SearchWindow(self.frame, self.set_url)

    def set_url(self, url):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
        self.trigger_title_fetch()

    def reset(self):
        self.url_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.placeholder = "保存名(空でタイトル)"
        self.name_entry.insert(0, self.placeholder)
        self.name_entry.config(fg='grey')

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Pro Downloader v6")
        
        # --- 1. 上部パネル (保存先 & アップデートボタン) ---
        top_frame = tk.Frame(root, padx=20, pady=15)
        top_frame.pack(fill="x")
        self.save_dir = tk.StringVar(value=os.getcwd())
        tk.Label(top_frame, text="保存フォルダ:").pack(side="left")
        self.path_entry = tk.Entry(top_frame, textvariable=self.save_dir, width=80)
        self.path_entry.pack(side="left", padx=10)
        
        self.ref_btn = tk.Button(top_frame, text="参照", command=self.select_folder, width=8)
        self.ref_btn.pack(side="left", padx=2)
        self.open_btn = tk.Button(top_frame, text="開く", command=self.open_folder, width=8)
        self.open_btn.pack(side="left", padx=2)

        # 【GitHubからのアップデートボタン】
        self.update_btn = tk.Button(top_frame, text="アプリ更新", command=self.check_update, 
                                    bg="#4CAF50", fg="white", font=("MS Gothic", 9, "bold"))
        self.update_btn.pack(side="left", padx=10)
        
        # --- ヘルプボタンを追加 ---
        self.help_btn = tk.Button(top_frame, text="ヘルプ", command=self.open_help, bg="#f0f0f0", width=6)
        self.help_btn.pack(side="left", padx=10)

        # 2. スクロールエリア (10行分をぴったり表示)
        canvas_container = tk.Frame(root, padx=20)
        canvas_container.pack(fill="both", expand=True)
        
        # 高さを400に抑え、中身とボタンを密接させる
        self.canvas = tk.Canvas(canvas_container, height=380, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # 10行の作成
        self.rows = [DownloadRow(self.scroll_frame, i) for i in range(10)]

        # 3. 実行ボタンエリア (余白を詰める)
        bottom_frame = tk.Frame(root, pady=10)
        bottom_frame.pack(fill="x")
        self.dl_btn = tk.Button(bottom_frame, text="一括ダウンロード開始", command=self.start_thread,
                               bg="#0078D7", fg="white", font=("MS Gothic", 12, "bold"), pady=12)
        self.dl_btn.pack(fill="x", padx=20)

        # ボタンのエンターキーバインド
        for btn in (self.ref_btn, self.open_btn, self.dl_btn):
            btn.bind("<Return>", lambda e, b=btn: b.invoke())
        self.path_entry.bind("<Return>", lambda e: self.path_entry.tk_focusNext().focus_set())

        # ウィンドウの最小サイズを設定 (切れないように)
        self.root.update_idletasks()
        self.root.minsize(1050, 550)
        
        
    # --- 自己アップデートのロジック ---
    def check_update(self):
        if not messagebox.askyesno("確認", "GitHubから最新版のアプリをダウンロードして更新しますか？\n(現在のアプリは一度終了します)"):
            return
        self.update_btn.config(state="disabled", text="更新中...")
        threading.Thread(target=self._perform_update, daemon=True).start()

    def _perform_update(self):
        try:
            current_exe = sys.executable  # 現在のexeのフルパス
            new_exe = current_exe + ".new"
            bat_file = "updater.bat"

            # 1. 新しいexeをGitHubからダウンロード
            urllib.request.urlretrieve(GITHUB_EXE_URL, new_exe)

            # 2. 入れ替え用のバッチファイルを作成
            # 自分を消して、新しいのを自分にリネームして、自分を起動する
            with open(bat_file, "w", encoding="shift-jis") as f:
                f.write(f'@echo off\n')
                f.write(f'timeout /t 2 > nul\n') # アプリが完全に閉じるのを待つ
                f.write(f'del "{current_exe}"\n')
                f.write(f'ren "{new_exe}" "{os.path.basename(current_exe)}"\n')
                f.write(f'start "" "{current_exe}"\n')
                f.write(f'del "{bat_file}"\n')

            # 3. バッチファイルを起動して、自分は即終了する
            subprocess.Popen([bat_file], shell=True)
            self.root.after(0, self.root.quit)

        except Exception as e:
            messagebox.showerror("更新失敗", f"GitHubからの更新に失敗しました:\n{e}")
            self.after(0, lambda: self.update_btn.config(state="normal", text="アプリ更新"))

    def select_folder(self):
        p = filedialog.askdirectory()
        if p: self.save_dir.set(p)

    def open_folder(self):
        if os.path.exists(self.save_dir.get()):
            os.startfile(self.save_dir.get())

    def start_thread(self):
        tasks = [r.url_entry.get().strip() for r in self.rows if r.url_entry.get().strip()]
        if not tasks: return messagebox.showwarning("入力なし", "URLを1つ以上入力してください")

        self.p_win = tk.Toplevel(self.root)
        self.p_win.title("ダウンロード中")
        self.p_win.attributes("-topmost", True)
        self.p_label = tk.Label(self.p_win, text="準備中...", pady=15, padx=30)
        self.p_label.pack()
        self.p_bar = ttk.Progressbar(self.p_win, length=350, mode='determinate')
        self.p_bar.pack(pady=15, padx=30)

        self.dl_btn.config(state="disabled")
        threading.Thread(target=self.execute, daemon=True).start()

    def execute(self):
        save_path = self.save_dir.get()
        for r in self.rows:
            url = r.url_entry.get().strip()
            if not url: continue
            name = r.name_entry.get().strip()
            if name == r.placeholder: name = ""
            mode = r.mode_combo.get()
            
            opts = {
                'progress_hooks': [self._hook],
                'outtmpl': os.path.join(save_path, f"{name if name else '%(title)s'}.%(ext)s"),
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
                'nocheckcertificate': True, 'quiet': True
            }
            if "音源" in mode:
                opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]})
            else:
                f = "bestvideo[height<=1080]+bestaudio/best" if "1080p" in mode else "bestvideo[height<=720]+bestaudio/best" if "720p" in mode else "bestvideo+bestaudio/best"
                opts.update({'format': f, 'merge_output_format': 'mp4'})
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
            except: pass
        self.after_all()

    def _hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%')
            self.p_label.config(text=f"処理中...\n進捗: {p}")
            try: self.p_bar['value'] = float(p.replace('%', ''))
            except: pass
            
    def open_help(self):
        HelpWindow(self.root)

    def after_all(self):
        self.p_win.destroy()
        finish = tk.Toplevel(self.root)
        finish.attributes("-topmost", True)
        finish.withdraw()
        messagebox.showinfo("完了", "すべてのダウンロードが正常に終了しました！", parent=finish)
        finish.destroy()
        for r in self.rows: r.reset()
        self.dl_btn.config(state="normal")
        self.canvas.yview_moveto(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()