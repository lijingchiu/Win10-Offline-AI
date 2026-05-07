"""
Win10 Offline AI Installer
One-click setup for local AI with Ollama + Web UI on Windows 10
"""
import os
import sys
import json
import shutil
import tarfile
import tempfile
import threading
import subprocess
import urllib.request
import urllib.error
import ctypes
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# ── Constants ───────────────────────────────────────────────────────────────
APP_NAME      = "Win10 离线 AI"
VERSION       = "1.1.0"
INSTALL_DIR   = Path("C:/WinLLM")
GITHUB_REPO   = "Win10-Offline-AI"   # filled by build
GITHUB_OWNER  = "OWNER_PLACEHOLDER"  # filled by build

OLLAMA_RELEASE_URL = (
    "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
)
PYTHON_RELEASE_URL = (
    "https://github.com/indygreg/python-build-standalone/releases/download/"
    "20240814/cpython-3.12.5+20240814-x86_64-pc-windows-msvc-install_only.tar.gz"
)

# Each model lists its GGUF chunks stored in GitHub Releases.
# chunks: list of filenames (must be downloaded in order and concatenated).
MODELS = [
    {
        "name":    "qwen3:8b",
        "display": "Qwen3 8B（推薦，最聰明）",
        "tag":     "qwen3:8b",
        "gguf_name": "Qwen3-8B-Q4_K_M.gguf",
        "chunks":  [
            "Qwen3-8B-Q4_K_M.gguf.part1",
            "Qwen3-8B-Q4_K_M.gguf.part2",
            "Qwen3-8B-Q4_K_M.gguf.part3",
        ],
        "size_gb": 4.7,
    },
    {
        "name":    "llama3.1:8b",
        "display": "Llama 3.1 8B（通用對話）",
        "tag":     "llama3.1:8b",
        "gguf_name": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "chunks":  [
            "Meta-Llama-3.1-8B-Q4_K_M.gguf.part1",
            "Meta-Llama-3.1-8B-Q4_K_M.gguf.part2",
            "Meta-Llama-3.1-8B-Q4_K_M.gguf.part3",
        ],
        "size_gb": 4.6,
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


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def github_release_url(filename: str) -> str:
    return (
        f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/"
        f"releases/download/latest-build/{filename}"
    )


def download_file(url: str, dest: Path, progress_cb=None) -> bool:
    """Stream-download url → dest, calling progress_cb(pct) with 0-100."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "WinLLM-Installer/1.1"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    buf = resp.read(65536)
                    if not buf:
                        break
                    f.write(buf)
                    downloaded += len(buf)
                    if progress_cb and total:
                        progress_cb(downloaded / total * 100)
        return True
    except Exception as e:
        print(f"[download] {url} → {e}")
        return False


def assemble_chunks(chunk_paths: list[Path], dest: Path) -> bool:
    """Concatenate ordered chunk files into dest."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as out:
            for cp in chunk_paths:
                with open(cp, "rb") as inp:
                    shutil.copyfileobj(inp, out)
        return True
    except Exception as e:
        print(f"[assemble] {e}")
        return False


def create_shortcut(target: Path, shortcut_path: Path, args: str = ""):
    ps = (
        f"$ws = New-Object -ComObject WScript.Shell;"
        f"$sc = $ws.CreateShortcut('{shortcut_path}');"
        f"$sc.TargetPath = '{target}';"
        f"$sc.Arguments = '{args}';"
        f"$sc.Save()"
    )
    subprocess.run(["powershell", "-Command", ps], capture_output=True)


# ── Main Installer UI ────────────────────────────────────────────────────────
class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — 安裝精靈 v{VERSION}")
        self.geometry("700x560")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self._center()
        self._build_ui()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"700x560+{(sw-700)//2}+{(sh-560)//2}")

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg="#16213e", height=80)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🤖  Win10 離線 AI 安裝精靈",
                 font=("Microsoft JhengHei UI", 18, "bold"),
                 fg="#e0e0ff", bg="#16213e").pack(side="left", padx=20, pady=20)
        tk.Label(hdr, text=f"v{VERSION}",
                 font=("Consolas", 10), fg="#888", bg="#16213e").pack(side="right", padx=20)

        # Step sidebar
        sf = tk.Frame(self, bg="#1a1a2e", width=195)
        sf.pack(side="left", fill="y", padx=(8, 0), pady=10)
        sf.pack_propagate(False)
        tk.Label(sf, text="安裝步驟", font=("Microsoft JhengHei UI", 10, "bold"),
                 fg="#888", bg="#1a1a2e").pack(anchor="w", padx=10, pady=(10, 5))
        self._step_lbls = []
        for s in ["① 環境檢查", "② 下載 Ollama", "③ 安裝 Ollama",
                  "④ Python 環境", "⑤ 網頁介面", "⑥ 下載模型", "⑦ 建立捷徑"]:
            lbl = tk.Label(sf, text=s, font=("Microsoft JhengHei UI", 9),
                           fg="#555", bg="#1a1a2e", anchor="w")
            lbl.pack(anchor="w", padx=10, pady=2, fill="x")
            self._step_lbls.append(lbl)

        # Content area
        ct = tk.Frame(self, bg="#1a1a2e")
        ct.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self._status = tk.StringVar(value="準備開始安裝...")
        tk.Label(ct, textvariable=self._status,
                 font=("Microsoft JhengHei UI", 11, "bold"),
                 fg="#e0e0ff", bg="#1a1a2e", anchor="w").pack(anchor="w")

        self._pbar = ttk.Progressbar(ct, length=460, mode="determinate")
        self._pbar.pack(fill="x", pady=(5, 8))

        # Sub-progress (for chunk downloads)
        self._sub_status = tk.StringVar(value="")
        tk.Label(ct, textvariable=self._sub_status,
                 font=("Consolas", 8), fg="#888",
                 bg="#1a1a2e", anchor="w").pack(anchor="w")
        self._sub_bar = ttk.Progressbar(ct, length=460, mode="determinate")
        self._sub_bar.pack(fill="x", pady=(2, 8))

        # Log
        lf = tk.Frame(ct, bg="#0d0d1a")
        lf.pack(fill="both", expand=True)
        self._log = tk.Text(lf, bg="#0d0d1a", fg="#aaffaa",
                            font=("Consolas", 9), relief="flat",
                            state="disabled", wrap="word")
        sb = ttk.Scrollbar(lf, command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(fill="both", expand=True, padx=5, pady=5)

        # Model selection
        mf = tk.LabelFrame(ct, text="  選擇安裝的模型  ",
                           bg="#1a1a2e", fg="#aaa",
                           font=("Microsoft JhengHei UI", 9))
        mf.pack(fill="x", pady=(6, 0))
        self._model_vars = {}
        for m in MODELS:
            var = tk.BooleanVar(value=True)
            self._model_vars[m["name"]] = var
            tk.Checkbutton(
                mf, text=f"{m['display']}  (~{m['size_gb']} GB 需下載)",
                variable=var, bg="#1a1a2e", fg="#ccc",
                selectcolor="#333", activebackground="#1a1a2e",
                font=("Microsoft JhengHei UI", 9)
            ).pack(anchor="w", padx=10, pady=2)

        # Buttons
        bf = tk.Frame(ct, bg="#1a1a2e")
        bf.pack(fill="x", pady=(8, 0))
        tk.Button(bf, text="取消", width=10, command=self.destroy,
                  bg="#333", fg="#ccc", relief="flat").pack(side="right", padx=5)
        self._install_btn = tk.Button(
            bf, text="▶  開始安裝", width=14,
            command=self._start,
            bg="#4361ee", fg="white", relief="flat",
            font=("Microsoft JhengHei UI", 10, "bold"),
        )
        self._install_btn.pack(side="right", padx=5)

    # ── UI helpers ────────────────────────────────────────────────────────────
    def log(self, msg: str, color: str = "#aaffaa"):
        self._log.configure(state="normal")
        tag = f"t{id(msg)}"
        self._log.insert("end", msg + "\n")
        self._log.tag_add(tag, f"end-{len(msg)+2}c", "end-1c")
        self._log.tag_config(tag, foreground=color)
        self._log.configure(state="disabled")
        self._log.see("end")

    def set_step(self, idx: int):
        for i, lbl in enumerate(self._step_lbls):
            if i < idx:
                lbl.config(fg="#4ade80")
            elif i == idx:
                lbl.config(fg="#fbbf24", font=("Microsoft JhengHei UI", 9, "bold"))
            else:
                lbl.config(fg="#555")

    def progress(self, pct: float, status: str = ""):
        self._pbar["value"] = pct
        if status:
            self._status.set(status)
        self.update_idletasks()

    def sub_progress(self, pct: float, label: str = ""):
        self._sub_bar["value"] = pct
        if label:
            self._sub_status.set(label)
        self.update_idletasks()

    # ── Install entry ─────────────────────────────────────────────────────────
    def _start(self):
        self._install_btn.config(state="disabled")
        selected = [m for m in MODELS if self._model_vars[m["name"]].get()]
        threading.Thread(target=self._run, args=(selected,), daemon=True).start()

    def _run(self, models):
        try:
            self._install(models)
        except Exception as e:
            self.after(0, lambda: self.log(f"❌ {e}", "#ff6b6b"))
            self.after(0, lambda: messagebox.showerror("安裝錯誤", str(e)))
            self.after(0, lambda: self._install_btn.config(state="normal"))

    # ── Installation logic ────────────────────────────────────────────────────
    def _install(self, models):
        tmp = Path(tempfile.mkdtemp(prefix="winllm_"))

        # Step 0 — check admin
        self.after(0, lambda: self.set_step(0))
        self.after(0, lambda: self.progress(2, "檢查系統環境..."))
        if not is_admin():
            self.after(0, lambda: self.log("⚠️  需要管理員權限，重新啟動中..."))
            self.after(1500, relaunch_as_admin)
            return
        self.after(0, lambda: self.log("✅ 管理員權限確認"))
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        (INSTALL_DIR / "models").mkdir(exist_ok=True)

        # Step 1 — download Ollama
        self.after(0, lambda: self.set_step(1))
        ollama_exe = self._find_ollama()
        if not ollama_exe:
            self.after(0, lambda: self.progress(5, "下載 Ollama..."))
            self.after(0, lambda: self.log("⬇️  下載 Ollama for Windows..."))
            setup = tmp / "OllamaSetup.exe"
            ok = download_file(OLLAMA_RELEASE_URL, setup,
                               lambda p: self.after(0, lambda pp=p:
                                   self.sub_progress(pp, f"OllamaSetup.exe  {pp:.0f}%")))
            if not ok:
                raise RuntimeError("Ollama 下載失敗")
            self.after(0, lambda: self.log("✅ Ollama 下載完成"))
        else:
            self.after(0, lambda: self.log("✅ Ollama 已安裝"))

        # Step 2 — install Ollama
        self.after(0, lambda: self.set_step(2))
        self.after(0, lambda: self.progress(20, "安裝 Ollama..."))
        if not self._find_ollama():
            r = run([str(tmp / "OllamaSetup.exe"), "/SILENT", "/NORESTART"])
            if r.returncode not in (0, 3010):
                raise RuntimeError(f"Ollama 安裝失敗 (code {r.returncode})")
            time.sleep(3)
        self.after(0, lambda: self.log("✅ Ollama 就緒"))

        # Start Ollama service
        ollama_exe = self._find_ollama()
        env = os.environ.copy()
        env["OLLAMA_ORIGINS"] = "*"
        subprocess.Popen([str(ollama_exe), "serve"], env=env,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(4)

        # Step 3 — Python portable
        self.after(0, lambda: self.set_step(3))
        python_exe = INSTALL_DIR / "python" / "python.exe"
        if not python_exe.exists():
            self.after(0, lambda: self.progress(25, "下載 Python 3.12..."))
            self.after(0, lambda: self.log("⬇️  下載 Python 3.12 可攜版..."))
            py_arc = tmp / "python.tar.gz"
            ok = download_file(PYTHON_RELEASE_URL, py_arc,
                               lambda p: self.after(0, lambda pp=p:
                                   self.sub_progress(pp, f"python.tar.gz  {pp:.0f}%")))
            if not ok:
                raise RuntimeError("Python 下載失敗")
            self.after(0, lambda: self.log("📦 解壓縮 Python..."))
            with tarfile.open(py_arc, "r:gz") as tar:
                tar.extractall(INSTALL_DIR)
            # Move extracted folder to expected path if needed
            if not python_exe.exists():
                for cand in INSTALL_DIR.glob("**/python.exe"):
                    src = cand.parent
                    if src != INSTALL_DIR / "python":
                        shutil.move(str(src), str(INSTALL_DIR / "python"))
                    break
            self.after(0, lambda: self.log("✅ Python 3.12 就緒"))
        else:
            self.after(0, lambda: self.log("✅ Python 3.12 已存在"))

        # Install pip packages
        self.after(0, lambda: self.progress(44, "安裝 Python 套件..."))
        self.after(0, lambda: self.log("📦 安裝 Flask / pymupdf / docx / pptx..."))
        r = run([str(python_exe), "-m", "pip", "install", "--quiet",
                 "flask", "flask-cors", "pymupdf", "python-docx",
                 "openpyxl", "python-pptx", "requests"],
                timeout=300)
        if r.returncode != 0:
            self.after(0, lambda: self.log(f"⚠️  套件安裝警告", "#fbbf24"))
        else:
            self.after(0, lambda: self.log("✅ Python 套件安裝完成"))

        # Step 4 — Deploy web interface
        self.after(0, lambda: self.set_step(4))
        self.after(0, lambda: self.progress(54, "部署網頁介面..."))
        self._deploy(python_exe)
        self.after(0, lambda: self.log("✅ 網頁介面已部署"))

        # Step 5 — Download models
        self.after(0, lambda: self.set_step(5))
        slot_size = 40 / max(len(models), 1)
        for i, model in enumerate(models):
            base = 56 + i * slot_size
            self.after(0, lambda m=model: self.log(
                f"\n⬇️  開始安裝模型：{m['display']}"))
            self._install_model(model, base, slot_size)

        # Step 6 — Shortcuts
        self.after(0, lambda: self.set_step(6))
        self.after(0, lambda: self.progress(97, "建立捷徑..."))
        self._shortcuts()
        self.after(0, lambda: self.log("✅ 桌面捷徑已建立"))

        self.after(0, lambda: self.progress(100, "✅ 安裝完成！"))
        self.after(0, self._done)

    # ── Model installation (chunk download + assemble + ollama create) ────────
    def _install_model(self, model: dict, base_pct: float, slot: float):
        ollama = self._find_ollama()
        if not ollama:
            self.after(0, lambda: self.log("⚠️  Ollama 未找到", "#fbbf24"))
            return

        # Already installed?
        r = run([str(ollama), "list"])
        if model["tag"] in r.stdout:
            self.after(0, lambda m=model: self.log(f"✅ {m['name']} 已存在，跳過"))
            return

        gguf_dest = INSTALL_DIR / "models" / model["gguf_name"]

        # 1. Check for pre-placed local GGUF
        if gguf_dest.exists() and gguf_dest.stat().st_size > 1_000_000_000:
            self.after(0, lambda: self.log("📂 找到本機 GGUF 檔案，直接匯入..."))
        else:
            # 2. Download chunks from GitHub Releases
            chunks = model.get("chunks", [])
            if not chunks:
                self.after(0, lambda: self.log("⚠️  無 chunk 定義，跳過", "#fbbf24"))
                return

            chunk_paths = []
            per_chunk = slot / (len(chunks) + 1)
            for ci, chunk_name in enumerate(chunks):
                url = github_release_url(chunk_name)
                dest = INSTALL_DIR / "models" / chunk_name
                self.after(0, lambda cn=chunk_name:
                    self.log(f"   ⬇️  {cn}"))
                ok = download_file(
                    url, dest,
                    lambda p, ci=ci, cn=chunk_name:
                        self.after(0, lambda pp=p, c=ci:
                            (self.progress(base_pct + c * per_chunk + pp * per_chunk / 100,
                                          f"下載模型分段 {c+1}/{len(chunks)}"),
                             self.sub_progress(pp, f"{cn}  {pp:.0f}%")))
                )
                if not ok:
                    self.after(0, lambda cn=chunk_name:
                        self.log(f"   ❌ 下載失敗：{cn}", "#ff6b6b"))
                    return
                chunk_paths.append(dest)

            # 3. Assemble chunks
            self.after(0, lambda m=model:
                self.log(f"🔧 合併分段為完整 GGUF..."))
            self.after(0, lambda: self.progress(
                base_pct + slot * 0.85, "合併模型分段..."))
            if not assemble_chunks(chunk_paths, gguf_dest):
                self.after(0, lambda: self.log("❌ 合併失敗", "#ff6b6b"))
                return

            # Clean up chunk files
            for cp in chunk_paths:
                cp.unlink(missing_ok=True)
            self.after(0, lambda m=model:
                self.log(f"✅ GGUF 合併完成：{gguf_dest.name}"))

        # 4. Import into Ollama via Modelfile
        self.after(0, lambda: self.log("🔧 匯入模型至 Ollama..."))
        mf_path = INSTALL_DIR / "models" / f"{model['name'].replace(':','_')}.Modelfile"
        mf_path.write_text(f"FROM {gguf_dest}\n", encoding="utf-8")
        r = run([str(ollama), "create", model["tag"], "-f", str(mf_path)],
                timeout=600)
        if r.returncode == 0:
            self.after(0, lambda m=model:
                self.log(f"✅ 模型 {m['name']} 匯入完成！"))
            gguf_dest.unlink(missing_ok=True)  # free disk space
            mf_path.unlink(missing_ok=True)
        else:
            self.after(0, lambda: self.log(f"⚠️  Ollama create 失敗:\n{r.stderr[:300]}", "#fbbf24"))

    # ── Deploy helper ─────────────────────────────────────────────────────────
    def _deploy(self, python_exe: Path):
        # Copy frontend and server from installer bundle
        for src_name, dst_name in [("frontend", "frontend"), ("server", None)]:
            src = Path(__file__).parent.parent / src_name
            if src.exists():
                dst = INSTALL_DIR / (dst_name or "")
                if dst_name:
                    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
                else:
                    for f in src.iterdir():
                        shutil.copy2(str(f), str(INSTALL_DIR / f.name))

        ollama_exe = self._find_ollama() or Path("ollama")

        (INSTALL_DIR / "start.bat").write_text(
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "title Win10 离线 AI\r\n"
            "set OLLAMA_ORIGINS=*\r\n"
            f'tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find "ollama.exe" >nul || '
            f'start "" /B "{ollama_exe}" serve\r\n'
            "timeout /t 4 /nobreak >nul\r\n"
            f'start "" /B "{python_exe}" "{INSTALL_DIR / "server.py"}"\r\n'
            "timeout /t 2 /nobreak >nul\r\n"
            'start "" "http://localhost:8765"\r\n',
            encoding="utf-8"
        )
        (INSTALL_DIR / "stop.bat").write_text(
            "@echo off\r\n"
            "taskkill /F /IM ollama.exe /T >nul 2>&1\r\n"
            "for /f \"tokens=5\" %%a in ('netstat -ano 2^>nul ^| find \":8765\"') "
            "do taskkill /F /PID %%a >nul 2>&1\r\n"
            "echo 已停止。\r\n",
            encoding="utf-8"
        )

    def _shortcuts(self):
        desk = Path(os.environ.get("PUBLIC", "C:/Users/Public")) / "Desktop"
        if not desk.exists():
            desk = Path(os.path.expanduser("~")) / "Desktop"
        create_shortcut(INSTALL_DIR / "start.bat", desk / "Win10 离线 AI.lnk")

    def _done(self):
        self.log("\n🎉 安裝完成！\n", "#4ade80")
        self.log("▶  雙擊桌面「Win10 离线 AI」捷徑即可啟動", "#e0e0ff")
        self._install_btn.config(
            text="🚀 立即啟動", state="normal",
            command=lambda: (
                subprocess.Popen([str(INSTALL_DIR / "start.bat")], shell=True),
                self.after(3000, self.destroy)
            ),
            bg="#4ade80", fg="#0d0d1a"
        )

    @staticmethod
    def _find_ollama() -> Path | None:
        for c in [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe",
            Path("C:/Program Files/Ollama/ollama.exe"),
            Path(shutil.which("ollama") or ""),
        ]:
            if c.exists():
                return c
        return None


# ── Entry ─────────────────────────────────────────────────────────────────────
def main():
    if not is_admin():
        relaunch_as_admin()
    InstallerApp().mainloop()


if __name__ == "__main__":
    main()
