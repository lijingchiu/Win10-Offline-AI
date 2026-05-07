"""
Win10 Offline AI Installer
One-click setup for local AI with Ollama + Web UI on Windows 10
"""
import os
import sys
import json
import shutil
import zipfile
import tarfile
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
import winreg
import ctypes
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ── Constants ───────────────────────────────────────────────────────────────
APP_NAME      = "Win10 离线 AI"
VERSION       = "1.0.0"
INSTALL_DIR   = Path("C:/WinLLM")
OLLAMA_DIR    = Path("C:/Program Files/Ollama")
GITHUB_REPO   = "Win10-Offline-AI"  # filled by build
GITHUB_OWNER  = "OWNER_PLACEHOLDER"  # filled by build

OLLAMA_RELEASE_URL = (
    "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
)
PYTHON_RELEASE_URL = (
    "https://github.com/indygreg/python-build-standalone/releases/download/"
    "20240814/cpython-3.12.5+20240814-x86_64-pc-windows-msvc-install_only.tar.gz"
)

MODELS = [
    {
        "name": "qwen3:8b",
        "display": "Qwen3 8B（推薦，最聰明）",
        "tag": "qwen3:8b",
        "gguf_name": "qwen3-8b-q4_k_m.gguf",
        "size_gb": 5.2,
    },
    {
        "name": "llama3.1:8b",
        "display": "Llama 3.1 8B（通用對話）",
        "tag": "llama3.1:8b",
        "gguf_name": "llama3.1-8b-q4_k_m.gguf",
        "size_gb": 4.7,
    },
]

# ── Helpers ──────────────────────────────────────────────────────────────────
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)


def which(name: str) -> str | None:
    return shutil.which(name)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def download_file(url: str, dest: Path, progress_cb=None) -> bool:
    """Download url → dest, call progress_cb(pct) while downloading."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WinLLM-Installer/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            chunk = 65536
            with open(dest, "wb") as f:
                while True:
                    buf = resp.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    downloaded += len(buf)
                    if progress_cb and total:
                        progress_cb(downloaded / total * 100)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def create_shortcut(target: Path, shortcut_path: Path, args: str = "", icon: Path | None = None):
    """Create a Windows .lnk shortcut using PowerShell."""
    icon_part = f'$sc.IconLocation = "{icon}";' if icon else ""
    ps = f"""
    $ws = New-Object -ComObject WScript.Shell;
    $sc = $ws.CreateShortcut('{shortcut_path}');
    $sc.TargetPath = '{target}';
    $sc.Arguments = '{args}';
    {icon_part}
    $sc.Save()
    """
    subprocess.run(["powershell", "-Command", ps], capture_output=True)


# ── Main Installer UI ────────────────────────────────────────────────────────
class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — 安裝精靈 v{VERSION}")
        self.geometry("680x520")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self._center()
        self._build_ui()
        self._current_step = 0
        self._cancelled = False

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (sw - 680) // 2
        y = (sh - 520) // 2
        self.geometry(f"680x520+{x}+{y}")

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#16213e", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🤖  Win10 離線 AI 安裝精靈",
                 font=("Microsoft JhengHei UI", 18, "bold"),
                 fg="#e0e0ff", bg="#16213e").pack(side="left", padx=20, pady=20)
        tk.Label(header, text=f"v{VERSION}",
                 font=("Consolas", 10), fg="#888", bg="#16213e").pack(side="right", padx=20)

        # Step list
        steps_frame = tk.Frame(self, bg="#1a1a2e", width=200)
        steps_frame.pack(side="left", fill="y", padx=(10, 0), pady=10)
        steps_frame.pack_propagate(False)

        tk.Label(steps_frame, text="安裝步驟", font=("Microsoft JhengHei UI", 10, "bold"),
                 fg="#888", bg="#1a1a2e").pack(anchor="w", padx=10, pady=(10, 5))

        self.step_labels = []
        steps = ["① 環境檢查", "② 下載 Ollama", "③ 安裝 Ollama",
                 "④ 下載 Python", "⑤ 部署介面", "⑥ 安裝模型", "⑦ 建立捷徑"]
        for i, s in enumerate(steps):
            lbl = tk.Label(steps_frame, text=s, font=("Microsoft JhengHei UI", 9),
                           fg="#555", bg="#1a1a2e", anchor="w")
            lbl.pack(anchor="w", padx=10, pady=2, fill="x")
            self.step_labels.append(lbl)

        # Main content
        content = tk.Frame(self, bg="#1a1a2e")
        content.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.status_var = tk.StringVar(value="準備開始安裝...")
        tk.Label(content, textvariable=self.status_var,
                 font=("Microsoft JhengHei UI", 11, "bold"),
                 fg="#e0e0ff", bg="#1a1a2e", anchor="w").pack(anchor="w")

        self.progress = ttk.Progressbar(content, length=430, mode="determinate")
        self.progress.pack(fill="x", pady=(5, 10))

        # Log area
        log_frame = tk.Frame(content, bg="#0d0d1a")
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, bg="#0d0d1a", fg="#aaffaa",
                                font=("Consolas", 9), relief="flat",
                                state="disabled", wrap="word")
        sb = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Model selection
        model_frame = tk.LabelFrame(content, text="  選擇要安裝的模型  ",
                                    bg="#1a1a2e", fg="#aaa",
                                    font=("Microsoft JhengHei UI", 9))
        model_frame.pack(fill="x", pady=(8, 0))

        self.model_vars = {}
        for m in MODELS:
            var = tk.BooleanVar(value=True)
            self.model_vars[m["name"]] = var
            cb = tk.Checkbutton(model_frame, text=f"{m['display']}  (~{m['size_gb']} GB)",
                                variable=var, bg="#1a1a2e", fg="#ccc",
                                selectcolor="#333", activebackground="#1a1a2e",
                                font=("Microsoft JhengHei UI", 9))
            cb.pack(anchor="w", padx=10, pady=2)

        # Buttons
        btn_frame = tk.Frame(content, bg="#1a1a2e")
        btn_frame.pack(fill="x", pady=(8, 0))

        self.cancel_btn = tk.Button(btn_frame, text="取消", width=10,
                                    command=self._cancel,
                                    bg="#333", fg="#ccc", relief="flat",
                                    activebackground="#444")
        self.cancel_btn.pack(side="right", padx=5)

        self.install_btn = tk.Button(btn_frame, text="▶  開始安裝", width=14,
                                     command=self._start_install,
                                     bg="#4361ee", fg="white", relief="flat",
                                     font=("Microsoft JhengHei UI", 10, "bold"),
                                     activebackground="#3a0ca3")
        self.install_btn.pack(side="right", padx=5)

    def log(self, msg: str, color: str = "#aaffaa"):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.tag_add(f"c{id(msg)}", f"end-{len(msg)+2}c", "end-1c")
        self.log_text.tag_config(f"c{id(msg)}", foreground=color)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def set_step(self, idx: int):
        for i, lbl in enumerate(self.step_labels):
            if i < idx:
                lbl.config(fg="#4ade80")  # done
            elif i == idx:
                lbl.config(fg="#fbbf24", font=("Microsoft JhengHei UI", 9, "bold"))
            else:
                lbl.config(fg="#555")
        self._current_step = idx

    def set_progress(self, pct: float, status: str = ""):
        self.progress["value"] = pct
        if status:
            self.status_var.set(status)
        self.update_idletasks()

    def _cancel(self):
        if messagebox.askyesno("取消安裝", "確定要取消安裝嗎？"):
            self._cancelled = True
            self.destroy()

    def _start_install(self):
        self.install_btn.config(state="disabled")
        selected = [m for m in MODELS if self.model_vars[m["name"]].get()]
        threading.Thread(target=self._install_thread, args=(selected,), daemon=True).start()

    def _install_thread(self, selected_models):
        try:
            self._do_install(selected_models)
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _on_error(self, msg: str):
        self.log(f"❌ 錯誤: {msg}", "#ff6b6b")
        self.status_var.set("安裝過程中發生錯誤")
        messagebox.showerror("安裝錯誤", f"發生錯誤：\n{msg}\n\n請查看記錄了解詳情。")
        self.install_btn.config(state="normal", text="重試")

    # ── Installation Steps ────────────────────────────────────────────────────
    def _do_install(self, selected_models):
        tmp = Path(tempfile.mkdtemp(prefix="winllm_"))

        # Step 0: Check environment
        self.after(0, lambda: self.set_step(0))
        self.after(0, lambda: self.set_progress(2, "正在檢查系統環境..."))
        self.after(0, lambda: self.log("🔍 檢查 Windows 版本..."))
        if not is_admin():
            self.after(0, lambda: self.log("⚠️  需要管理員權限，正在重新啟動...", "#fbbf24"))
            self.after(1000, relaunch_as_admin)
            return

        self.after(0, lambda: self.log("✅ 管理員權限確認"))
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)

        # Step 1: Download Ollama
        self.after(0, lambda: self.set_step(1))
        ollama_setup = tmp / "OllamaSetup.exe"
        if not self._check_ollama_installed():
            self.after(0, lambda: self.set_progress(5, "正在下載 Ollama..."))
            self.after(0, lambda: self.log("⬇️  下載 Ollama for Windows..."))
            ok = download_file(OLLAMA_RELEASE_URL, ollama_setup,
                               lambda p: self.after(0, lambda pp=p: self.set_progress(5 + pp * 0.15)))
            if not ok or self._cancelled:
                raise RuntimeError("Ollama 下載失敗，請檢查網路連線")
            self.after(0, lambda: self.log("✅ Ollama 下載完成"))
        else:
            self.after(0, lambda: self.log("✅ Ollama 已安裝，跳過下載"))

        # Step 2: Install Ollama
        self.after(0, lambda: self.set_step(2))
        self.after(0, lambda: self.set_progress(20, "正在安裝 Ollama..."))
        if not self._check_ollama_installed():
            self.after(0, lambda: self.log("🔧 安裝 Ollama..."))
            r = run([str(ollama_setup), "/SILENT", "/NORESTART"])
            if r.returncode not in (0, 3010):
                raise RuntimeError(f"Ollama 安裝失敗 (code {r.returncode})\n{r.stderr}")
            self.after(0, lambda: self.log("✅ Ollama 安裝完成"))
            time.sleep(3)
        else:
            self.after(0, lambda: self.log("✅ Ollama 已就緒"))

        # Start Ollama service
        self.after(0, lambda: self.log("🚀 啟動 Ollama 服務..."))
        ollama_exe = self._find_ollama()
        if ollama_exe:
            subprocess.Popen([str(ollama_exe), "serve"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(4)
            self.after(0, lambda: self.log("✅ Ollama 服務已啟動"))

        # Step 3: Download Python portable
        self.after(0, lambda: self.set_step(3))
        python_dir = INSTALL_DIR / "python"
        python_exe = python_dir / "python.exe"

        if not python_exe.exists():
            self.after(0, lambda: self.set_progress(25, "正在下載 Python 3.12..."))
            self.after(0, lambda: self.log("⬇️  下載 Python 3.12 (可攜版)..."))
            py_archive = tmp / "python.tar.gz"
            ok = download_file(PYTHON_RELEASE_URL, py_archive,
                               lambda p: self.after(0, lambda pp=p: self.set_progress(25 + pp * 0.20)))
            if not ok or self._cancelled:
                raise RuntimeError("Python 下載失敗")
            self.after(0, lambda: self.log("📦 解壓縮 Python..."))
            with tarfile.open(py_archive, "r:gz") as tar:
                tar.extractall(INSTALL_DIR)
            # The archive extracts to 'python/' subfolder
            extracted = INSTALL_DIR / "python"
            if not python_exe.exists():
                # try to find it
                candidates = list(INSTALL_DIR.glob("**/python.exe"))
                if candidates:
                    extracted = candidates[0].parent
                    if extracted != python_dir:
                        shutil.move(str(extracted), str(python_dir))
            self.after(0, lambda: self.log("✅ Python 3.12 就緒"))
        else:
            self.after(0, lambda: self.log("✅ Python 3.12 已存在"))

        # Install pip packages for file processing
        self.after(0, lambda: self.set_progress(46, "安裝 Python 套件..."))
        self.after(0, lambda: self.log("📦 安裝 Flask / pymupdf / docx 等套件..."))
        pip_packages = [
            "flask", "flask-cors", "pymupdf", "python-docx",
            "openpyxl", "python-pptx", "requests"
        ]
        r = run([str(python_exe), "-m", "pip", "install", "--quiet",
                 "--no-warn-script-location"] + pip_packages,
                timeout=300)
        if r.returncode != 0:
            self.after(0, lambda: self.log(f"⚠️  套件安裝警告: {r.stderr[:200]}", "#fbbf24"))
        else:
            self.after(0, lambda: self.log("✅ Python 套件已安裝"))

        # Step 4: Deploy web interface
        self.after(0, lambda: self.set_step(4))
        self.after(0, lambda: self.set_progress(55, "部署網頁介面..."))
        self.after(0, lambda: self.log("📂 複製介面檔案..."))
        self._deploy_frontend()
        self._deploy_server()
        self.after(0, lambda: self.log("✅ 網頁介面已部署"))

        # Step 5: Install models
        self.after(0, lambda: self.set_step(5))
        self.after(0, lambda: self.set_progress(60, "準備安裝模型..."))
        for i, model in enumerate(selected_models):
            if self._cancelled:
                break
            base = 60 + i * (35 // max(len(selected_models), 1))
            self.after(0, lambda m=model: self.log(f"⬇️  下載模型: {m['display']}"))
            self.after(0, lambda m=model, b=base: self.set_progress(b, f"安裝模型: {m['display']}"))
            self._install_model(model, base)

        # Step 6: Create shortcuts
        self.after(0, lambda: self.set_step(6))
        self.after(0, lambda: self.set_progress(96, "建立捷徑..."))
        self._create_shortcuts()
        self.after(0, lambda: self.log("✅ 桌面捷徑已建立"))

        self.after(0, lambda: self.set_progress(100, "✅ 安裝完成！"))
        self.after(0, self._on_complete)

    def _check_ollama_installed(self) -> bool:
        return bool(self._find_ollama())

    def _find_ollama(self) -> Path | None:
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe",
            Path("C:/Program Files/Ollama/ollama.exe"),
            Path(shutil.which("ollama") or ""),
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def _install_model(self, model: dict, base_pct: float):
        ollama = self._find_ollama()
        if not ollama:
            self.after(0, lambda m=model: self.log(f"⚠️  找不到 Ollama，跳過模型 {m['name']}", "#fbbf24"))
            return

        # Check if model already exists
        r = run([str(ollama), "list"])
        if model["tag"] in r.stdout:
            self.after(0, lambda m=model: self.log(f"✅ 模型 {m['name']} 已存在"))
            return

        # Check for local GGUF file
        local_gguf = INSTALL_DIR / "models" / model["gguf_name"]
        if local_gguf.exists():
            self.after(0, lambda: self.log(f"📂 使用本機 GGUF 檔案匯入..."))
            modelfile = INSTALL_DIR / "models" / f"{model['name'].replace(':', '_')}.Modelfile"
            modelfile.write_text(f"FROM {local_gguf}\n")
            r = run([str(ollama), "create", model["tag"], "-f", str(modelfile)], timeout=600)
            if r.returncode == 0:
                self.after(0, lambda m=model: self.log(f"✅ 模型 {m['name']} 匯入完成"))
            else:
                self.after(0, lambda m=model: self.log(f"⚠️  模型匯入失敗: {r.stderr[:200]}", "#fbbf24"))
            return

        # Try GitHub releases download
        guf_url = (f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/"
                   f"releases/latest/download/{model['gguf_name']}")
        self.after(0, lambda: self.log(f"⬇️  嘗試從 GitHub Releases 下載 GGUF..."))
        dest = INSTALL_DIR / "models" / model["gguf_name"]
        dest.parent.mkdir(parents=True, exist_ok=True)

        ok = download_file(guf_url, dest,
                           lambda p: self.after(0, lambda pp=p, b=base_pct:
                               self.set_progress(b + pp * 0.3)))
        if ok and dest.exists() and dest.stat().st_size > 10_000_000:
            modelfile = INSTALL_DIR / "models" / f"{model['name'].replace(':', '_')}.Modelfile"
            modelfile.write_text(f"FROM {dest}\n")
            r = run([str(ollama), "create", model["tag"], "-f", str(modelfile)], timeout=600)
            if r.returncode == 0:
                self.after(0, lambda m=model: self.log(f"✅ 模型 {m['name']} 下載並匯入完成"))
                dest.unlink(missing_ok=True)
                return

        # Try ollama pull as last resort
        self.after(0, lambda: self.log(f"⬇️  嘗試 ollama pull (需要網路)..."))
        try:
            proc = subprocess.Popen(
                [str(ollama), "pull", model["tag"]],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in proc.stdout:
                line = line.strip()
                if line:
                    self.after(0, lambda l=line: self.log(f"  {l}"))
            proc.wait(timeout=3600)
            if proc.returncode == 0:
                self.after(0, lambda m=model: self.log(f"✅ 模型 {m['name']} 下載完成"))
                return
        except Exception as e:
            pass

        self.after(0, lambda m=model: self.log(
            f"⚠️  模型 {m['name']} 無法自動安裝。\n"
            f"   請手動下載 GGUF 檔案並放置到：\n"
            f"   {INSTALL_DIR / 'models' / model['gguf_name']}\n"
            f"   然後執行桌面的「匯入模型」捷徑。",
            "#fbbf24"
        ))

    def _deploy_frontend(self):
        frontend_src = Path(__file__).parent.parent / "frontend"
        frontend_dst = INSTALL_DIR / "frontend"
        if frontend_src.exists():
            shutil.copytree(str(frontend_src), str(frontend_dst), dirs_exist_ok=True)
        else:
            frontend_dst.mkdir(parents=True, exist_ok=True)

    def _deploy_server(self):
        server_src = Path(__file__).parent.parent / "server" / "server.py"
        server_dst = INSTALL_DIR / "server.py"
        if server_src.exists():
            shutil.copy2(str(server_src), str(server_dst))
        # Write start/stop scripts
        start_bat = INSTALL_DIR / "start.bat"
        start_bat.write_text(
            "@echo off\n"
            "title Win10 离线 AI\n"
            "echo 启动 Ollama 服务...\n"
            f'start "" /B "{self._find_ollama() or "ollama"}" serve\n'
            "timeout /t 3 /nobreak >nul\n"
            "echo 启动文件处理服务...\n"
            f'start "" /B "{INSTALL_DIR / "python/python.exe"}" "{INSTALL_DIR / "server.py"}"\n'
            "timeout /t 2 /nobreak >nul\n"
            "echo 打开浏览器...\n"
            'start "" "http://localhost:8765"\n'
            "echo 完成！AI 界面已在浏览器打开。\n",
            encoding="utf-8"
        )
        stop_bat = INSTALL_DIR / "stop.bat"
        stop_bat.write_text(
            "@echo off\n"
            "echo 正在停止服务...\n"
            "taskkill /F /IM ollama.exe /T >nul 2>&1\n"
            "taskkill /F /IM python.exe /T >nul 2>&1\n"
            "echo 已停止所有服务。\n",
            encoding="utf-8"
        )
        import_bat = INSTALL_DIR / "import_model.bat"
        import_bat.write_text(
            "@echo off\n"
            "echo == 手动导入 GGUF 模型 ==\n"
            "echo 请将 .gguf 文件拖放到此窗口:\n"
            "set /p GGUF_PATH=GGUF 文件路径: \n"
            "set /p MODEL_NAME=模型名称 (例如 qwen3:8b): \n"
            f'echo FROM %GGUF_PATH% > "{INSTALL_DIR / "models/custom.Modelfile"}"\n'
            f'"{self._find_ollama() or "ollama"}" create %MODEL_NAME% '
            f'-f "{INSTALL_DIR / "models/custom.Modelfile"}"\n'
            "echo 导入完成！\n"
            "pause\n",
            encoding="utf-8"
        )

    def _create_shortcuts(self):
        desktop = Path(os.environ.get("PUBLIC", "C:/Users/Public")) / "Desktop"
        if not desktop.exists():
            desktop = Path(os.path.expanduser("~")) / "Desktop"

        start_bat = INSTALL_DIR / "start.bat"
        create_shortcut(
            target=start_bat,
            shortcut_path=desktop / "Win10 离线 AI.lnk",
        )
        import_bat = INSTALL_DIR / "import_model.bat"
        create_shortcut(
            target=import_bat,
            shortcut_path=desktop / "匯入 AI 模型.lnk",
        )

    def _on_complete(self):
        self.status_var.set("✅ 安裝完成！")
        self.log("\n🎉 安裝成功完成！\n", "#4ade80")
        self.log("── 使用方式 ──────────────────────────────────", "#888")
        self.log("1. 雙擊桌面的「Win10 离线 AI」捷徑啟動", "#e0e0ff")
        self.log("2. 瀏覽器自動開啟 http://localhost:8765", "#e0e0ff")
        self.log("3. 上傳 PDF / Excel / PPT 文件並開始對話", "#e0e0ff")
        self.log("─────────────────────────────────────────────", "#888")

        self.install_btn.config(
            text="🚀 立即啟動", state="normal",
            command=self._launch_app,
            bg="#4ade80", fg="#0d0d1a"
        )

    def _launch_app(self):
        subprocess.Popen([str(INSTALL_DIR / "start.bat")],
                         shell=True, cwd=str(INSTALL_DIR))
        self.after(3000, self.destroy)


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    if not is_admin():
        relaunch_as_admin()
    app = InstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
