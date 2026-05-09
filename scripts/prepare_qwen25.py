#!/usr/bin/env python3
"""
Prepare Qwen2.5-7B-Instruct Q4_K_M model chunks for offline distribution.

Run this on a machine WITH internet access. It will:
  1. Download Qwen2.5-7B-Instruct-Q4_K_M.gguf (~4.4 GB) from HuggingFace
  2. Split into 90 MB chunks (compatible with GitHub's 100 MB single-file limit)
  3. Place chunks at setup/models/qwen25_7b/chunk.aa, chunk.ab, ...

Usage:
    python scripts/prepare_qwen25.py
    git add setup/models/qwen25_7b/
    git commit -m "add: Qwen2.5-7B model chunks"
    git push

Requires: requests (only stdlib + requests, no other deps)
"""
import sys
import os
from pathlib import Path

BASE_URL   = "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main"
MODEL_PARTS = [
    "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
    "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf",
]
MODEL_FILE = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"
CHUNK_SIZE = 90 * 1024 * 1024  # 90 MB

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR   = REPO_ROOT / "setup" / "models" / "qwen25_7b"


def download(url: str, dst: Path) -> None:
    import requests
    print(f"[download] {url} → {dst}")
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(dst, "wb") as f:
            for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded * 100 // total
                        print(f"\r[download] {downloaded//1024//1024} / {total//1024//1024} MB ({pct}%)",
                              end="", flush=True)
        print()


def merge_parts(parts: list, dst: Path) -> None:
    print(f"[merge] 合併 {len(parts)} 個分片 → {dst.name}")
    with open(dst, "wb") as out:
        for part in parts:
            print(f"[merge] 寫入 {part.name} ({part.stat().st_size//1024//1024} MB)")
            with open(part, "rb") as f:
                while True:
                    data = f.read(8 * 1024 * 1024)
                    if not data:
                        break
                    out.write(data)
    print(f"[merge] 完成，總大小: {dst.stat().st_size//1024//1024} MB")


def split_file(src: Path, out_dir: Path, chunk_size: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Clean old chunks
    for old in out_dir.glob("chunk.*"):
        old.unlink()

    count = 0
    with open(src, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            # Suffix: aa, ab, ..., az, ba, bb, ...
            first  = chr(ord("a") + count // 26)
            second = chr(ord("a") + count % 26)
            chunk_path = out_dir / f"chunk.{first}{second}"
            chunk_path.write_bytes(data)
            count += 1
            print(f"\r[split] 已產生 {count} 個分段", end="", flush=True)
    print()
    return count


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gguf_path = OUT_DIR / MODEL_FILE

    if gguf_path.exists() and gguf_path.stat().st_size > 4_000_000_000:
        print(f"[skip] {MODEL_FILE} 已存在（{gguf_path.stat().st_size//1024//1024} MB）")
    else:
        try:
            import requests  # noqa: F401
        except ImportError:
            print("錯誤: 請先安裝 requests: pip install requests", file=sys.stderr)
            sys.exit(1)
        part_paths = []
        for part_name in MODEL_PARTS:
            part_path = OUT_DIR / part_name
            if part_path.exists():
                print(f"[skip] {part_name} 已存在")
            else:
                download(f"{BASE_URL}/{part_name}", part_path)
            part_paths.append(part_path)
        merge_parts(part_paths, gguf_path)
        for p in part_paths:
            p.unlink()

    size_mb = gguf_path.stat().st_size // 1024 // 1024
    if size_mb < 4000:
        print(f"錯誤: 下載檔案大小異常 ({size_mb} MB)", file=sys.stderr)
        sys.exit(1)
    print(f"[ok] GGUF 大小: {size_mb} MB")

    print(f"[split] 切片中（每段 {CHUNK_SIZE//1024//1024} MB）...")
    n = split_file(gguf_path, OUT_DIR, CHUNK_SIZE)
    print(f"[ok] 共產生 {n} 個分段於 {OUT_DIR}")

    print("[clean] 刪除原始 GGUF 以節省空間")
    gguf_path.unlink()

    print("\n下一步:")
    print("  git add setup/models/qwen25_7b/")
    print('  git commit -m "add: Qwen2.5-7B model chunks"')
    print("  git push")


if __name__ == "__main__":
    main()
