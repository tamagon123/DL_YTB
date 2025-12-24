import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import os

import platform

# --- ローカルPCのダウンロードフォルダを取得する関数 ---
def get_default_download_folder():
    if platform.system() == "Windows":
        import ctypes.wintypes
        CSIDL_PERSONAL = 0x0005       # My Documents
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x000C, None, 0, buf) == 0:
            # 0x000C = CSIDL_MYDOCUMENTS (actually Downloads is 0x000C for Vista+)
            download = buf.value
        else:
            # fallback: get from user profile
            download = os.path.join(os.environ.get("USERPROFILE", os.getcwd()), "Downloads")
        # Confirm the folder exists, otherwise fallback
        if os.path.exists(download):
            return download
        # fallback
        return os.path.join(os.environ.get("USERPROFILE", os.getcwd()), "Downloads")
    elif platform.system() == "Darwin":
        return os.path.join(os.path.expanduser('~'), 'Downloads')
    else:
        # Linux and others
        xdg = os.path.expanduser('~/Downloads')
        return xdg

# --- ヘルプ画面のクラス ---
class HelpWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("ヘルプ・使い方")
        self.geometry("600x540")
        self.attributes("-topmost", True)
        
        text_area = tk.Text(self, padx=15, pady=15, font=("MS Gothic", 10), wrap="word")
        text_area.pack(fill="both", expand=True)
        
        help_text = """【YouTube Pro Downloader 使い方マニュアル】

■ 1. 保存フォルダの指定
・上部「保存フォルダ」に直接パスを入力するか、「参照」で選択できます。
・「開く」ボタンで現在の保存先をエクスプローラーで開きます。

■ 2. URL入力と検索
・各行のURL欄に動画URLを貼り付けるか、「🔍 YouTube検索」で検索して選択するとURLが自動入力されます。

■ 3. 保存名の設定
・「保存名(空でタイトル)」に任意の名前を入力するとその名前で保存されます。
・空のまま（グレー表示）の場合は動画タイトルがファイル名になります。URL入力後にフォーカスを外すとタイトルを自動取得します。

■ 4. ダウンロード形式の選択
・「動画:最高画質」「動画:1080p」「動画:720p」「音源:MP3」から選べます（初期値は最高画質）。
・1080p以上や音声抽出(MP3)では同じフォルダにffmpeg.exeが必要です。

■ 5. 複数動画のバッチダウンロード
・最大10件まで入力できます。設定後「一括ダウンロード開始」を押してください。
・進捗ウィンドウで全体の平均進捗が表示され、完了後は自動で各行がリセットされます。

■ 6. キーボードショートカット
・Tabキー：次の項目へ移動
・Enterキー：入力確定、次の入力欄へ移動
・ボタンが選択された状態でEnter：クリックと同じ動作

※アプリの自動更新機能はありません。最新版は必要に応じて手動で入手してください。
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
        
        # --- 1. 上部パネル (保存先) ---
        top_frame = tk.Frame(root, padx=20, pady=15)
        top_frame.pack(fill="x")
        self.save_dir = tk.StringVar(value=get_default_download_folder())
        tk.Label(top_frame, text="保存フォルダ:").pack(side="left")
        self.path_entry = tk.Entry(top_frame, textvariable=self.save_dir, width=80)
        self.path_entry.pack(side="left", padx=10)
        
        self.ref_btn = tk.Button(top_frame, text="参照", command=self.select_folder, width=8)
        self.ref_btn.pack(side="left", padx=2)
        self.open_btn = tk.Button(top_frame, text="開く", command=self.open_folder, width=8)
        self.open_btn.pack(side="left", padx=2)

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
        
        
    def select_folder(self):
        p = filedialog.askdirectory()
        if p: self.save_dir.set(p)

    def open_folder(self):
        if os.path.exists(self.save_dir.get()):
            os.startfile(self.save_dir.get())

    def start_thread(self):
        tasks = [r.url_entry.get().strip() for r in self.rows if r.url_entry.get().strip()]
        if not tasks: 
            return messagebox.showwarning("入力なし", "URLを1つ以上入力してください")

        self.p_win = tk.Toplevel(self.root)
        self.p_win.title("ダウンロード中")
        self.p_win.attributes("-topmost", True)
        self.p_label = tk.Label(self.p_win, text="準備中...", pady=15, padx=30)
        self.p_label.pack()
        self.p_bar = ttk.Progressbar(self.p_win, length=350, mode='determinate', maximum=100)
        self.p_bar.pack(pady=15, padx=30)

        self.dl_btn.config(state="disabled")
        self._current_task_index = 0
        self._num_tasks = len([r for r in self.rows if r.url_entry.get().strip()])
        self._progress_values = [0] * self._num_tasks  # 進捗を保持する
        threading.Thread(target=self.execute, daemon=True).start()

    def execute(self):
        save_path = self.save_dir.get()
        all_success = True  # 1件でも失敗したらFalseにする

        # 保存先フォルダを保証
        if not os.path.isdir(save_path):
            try:
                os.makedirs(save_path, exist_ok=True)
            except Exception as e:
                messagebox.showerror("エラー", f"保存先フォルダの作成に失敗しました:\n{save_path}\n{e}")
                self.after_all()
                return

        # 有効なURL行だけ抽出しつつindex番号も付加
        valid_rows = [(i, r) for i, r in enumerate(self.rows) if r.url_entry.get().strip()]
        task_count = len(valid_rows)
        for idx, (row_idx, r) in enumerate(valid_rows):
            self._current_task_index = idx
            url = r.url_entry.get().strip()
            if not url:
                continue
            name = r.name_entry.get().strip()
            if name == r.placeholder: name = ""

            mode = r.mode_combo.get()
            outtmpl = os.path.join(save_path, f"{name if name else '%(title)s'}.%(ext)s")

            opts = {
                'progress_hooks': [lambda d, idx=idx: self._hook(d, idx, task_count)],
                'outtmpl': outtmpl,
                'nocheckcertificate': True,
                # 'quiet': True,  # 進捗が取れない場合があるためコメントアウトまたはFalseを推奨
                'no_warnings': True,
            }
            if "音源" in mode:
                opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }]
                })
            else:
                if "1080p" in mode:
                    fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/bestvideo[height<=1080]+bestaudio/best[height<=1080]"
                elif "720p" in mode:
                    fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/bestvideo[height<=720]+bestaudio/best[height<=720]"
                else:
                    fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best"
                opts.update({'format': fmt, 'merge_output_format': 'mp4'})

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                all_success = False
                # メインスレッドでエラーを表示
                self.root.after(0, lambda msg=str(e): self.update_progress_label(f"エラー: {msg}"))

        self.root.after(0, lambda success=all_success: self.after_all(success))

    def _hook(self, d, task_idx, total_tasks):
        # d: yt-dlpが進捗報告する辞書
        if d['status'] == 'downloading':
            # 文字列解析ではなく数値から計算する
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            
            if total:
                percent = (downloaded / total) * 100
            else:
                # 合計サイズが不明な場合は、文字列から抽出を試みる（フォールバック）
                p_str = d.get('_percent_str', '0%')
                # ANSIエスケープコードを除去して数値化
                import re
                clean_p_str = re.sub(r'\x1b\[[0-9;]*m', '', p_str).replace('%', '').strip()
                try:
                    percent = float(clean_p_str)
                except:
                    percent = 0            # 各ダウンロードのタスクごとに進捗を保存
            self._progress_values[task_idx] = percent
            # 全体の進捗を求める
            average_progress = sum(self._progress_values) / total_tasks

            label_text = f"処理中...\n[{task_idx+1}/{total_tasks}] 動画進捗: {percent:.1f}%"
            # メインスレッドでUI更新を予約
            self.root.after(0, self.update_progress_bar_and_label, average_progress, label_text)

        elif d['status'] == 'finished':
            # そのタスクを100%に
            self._progress_values[task_idx] = 100
            average_progress = sum(self._progress_values) / total_tasks
            label_text = f"完了直前 (変換中...)\n[{task_idx+1}/{total_tasks}]"
            self.root.after(0, self.update_progress_bar_and_label, average_progress, label_text)

    def update_progress_bar_and_label(self, percent, label_text):
        if hasattr(self, 'p_bar') and self.p_bar.winfo_exists():
            self.p_bar['value'] = percent
        if hasattr(self, 'p_label') and self.p_label.winfo_exists():
            self.p_label.config(text=label_text)
            
    def update_progress_label(self, txt):
        if hasattr(self, 'p_label'):
            self.p_label.config(text=txt)
            self.root.update_idletasks()

    def open_help(self):
        HelpWindow(self.root)

    def after_all(self, all_success=True):
        try:
            self.p_win.destroy()
        except Exception:
            pass
        finish = tk.Toplevel(self.root)
        finish.attributes("-topmost", True)
        finish.withdraw()
        if all_success:
            messagebox.showinfo("完了", "すべてのダウンロードが正常に終了しました！", parent=finish)
        else:
            messagebox.showwarning("一部失敗", "一部ダウンロードに失敗しました。詳しくは進捗表示をご確認ください。", parent=finish)
        finish.destroy()
        for r in self.rows: r.reset()
        self.dl_btn.config(state="normal")
        self.canvas.yview_moveto(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()