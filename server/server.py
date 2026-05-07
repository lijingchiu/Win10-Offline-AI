"""
WinLLM Local File Processing Server
Runs on port 8765, serves the frontend and processes document uploads.
"""
import os
import io
import json
import mimetypes
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import tempfile

FRONTEND_DIR = Path(__file__).parent / "frontend"
PORT = 8765


def extract_pdf(data: bytes) -> str:
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        pages = [page.get_text() for page in doc]
        return "\n\n".join(pages)
    except ImportError:
        return "[錯誤：未安裝 pymupdf，請執行 pip install pymupdf]"
    except Exception as e:
        return f"[PDF 解析錯誤: {e}]"


def extract_docx(data: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        tables_text = []
        for table in doc.tables:
            for row in table.rows:
                tables_text.append(" | ".join(c.text for c in row.cells))
        return "\n".join(paragraphs + tables_text)
    except ImportError:
        return "[錯誤：未安裝 python-docx，請執行 pip install python-docx]"
    except Exception as e:
        return f"[DOCX 解析錯誤: {e}]"


def extract_xlsx(data: bytes) -> str:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        parts = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            parts.append(f"=== 工作表: {sheet_name} ===")
            for row in ws.iter_rows(values_only=True):
                row_vals = [str(v) if v is not None else "" for v in row]
                if any(v.strip() for v in row_vals):
                    parts.append(" | ".join(row_vals))
        return "\n".join(parts)
    except ImportError:
        return "[錯誤：未安裝 openpyxl，請執行 pip install openpyxl]"
    except Exception as e:
        return f"[XLSX 解析錯誤: {e}]"


def extract_pptx(data: bytes) -> str:
    try:
        from pptx import Presentation
        prs = Presentation(io.BytesIO(data))
        slides = []
        for i, slide in enumerate(prs.slides, 1):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    texts.append(shape.text)
            if texts:
                slides.append(f"--- 第 {i} 張投影片 ---\n" + "\n".join(texts))
        return "\n\n".join(slides)
    except ImportError:
        return "[錯誤：未安裝 python-pptx，請執行 pip install python-pptx]"
    except Exception as e:
        return f"[PPTX 解析錯誤: {e}]"


def parse_multipart(data: bytes, boundary: bytes) -> dict[str, tuple[str, bytes]]:
    """Return {field_name: (filename_or_None, content_bytes)}."""
    results = {}
    delimiter = b"--" + boundary
    parts = data.split(delimiter)
    for part in parts[1:]:
        if part in (b"--\r\n", b"--"):
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end < 0:
            continue
        headers_raw = part[:header_end].decode("utf-8", errors="replace")
        body = part[header_end + 4:]
        if body.endswith(b"\r\n"):
            body = body[:-2]
        name = filename = None
        for header_line in headers_raw.splitlines():
            if "Content-Disposition" in header_line:
                for seg in header_line.split(";"):
                    seg = seg.strip()
                    if seg.startswith("name="):
                        name = seg.split("=", 1)[1].strip('"')
                    elif seg.startswith("filename="):
                        filename = seg.split("=", 1)[1].strip('"')
        if name:
            results[name] = (filename, body)
    return results


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.lstrip("/") or "index.html"

        if path == "api/status":
            self._json({"status": "ok", "version": "1.0.0"})
            return

        # Serve static files
        fpath = FRONTEND_DIR / path
        if not fpath.exists() and path == "index.html":
            fpath = Path(__file__).parent / "frontend" / "index.html"

        if fpath.exists() and fpath.is_file():
            mime, _ = mimetypes.guess_type(str(fpath))
            mime = mime or "application/octet-stream"
            data = fpath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", len(data))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        else:
            self._not_found()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/extract":
            self._handle_extract()
        else:
            self._not_found()

    def _handle_extract(self):
        ct = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        filename = ""
        file_data = b""

        if "multipart/form-data" in ct:
            boundary = ct.split("boundary=")[-1].encode()
            parts = parse_multipart(body, boundary)
            if "file" in parts:
                filename, file_data = parts["file"]
        else:
            file_data = body

        if not file_data:
            self._json({"error": "no file data"}, 400)
            return

        ext = Path(filename or "").suffix.lower()
        if ext == ".pdf":
            text = extract_pdf(file_data)
        elif ext in (".docx",):
            text = extract_docx(file_data)
        elif ext in (".xlsx", ".xls"):
            text = extract_xlsx(file_data)
        elif ext in (".pptx", ".ppt"):
            text = extract_pptx(file_data)
        else:
            try:
                text = file_data.decode("utf-8", errors="replace")
            except Exception:
                text = "[無法解析此檔案格式]"

        self._json({
            "filename": filename,
            "text": text,
            "chars": len(text),
        })

    def _json(self, data: dict, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(payload))
        self._cors()
        self.end_headers()
        self.wfile.write(payload)

    def _not_found(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")


def main():
    print(f"[WinLLM] 服務啟動於 http://localhost:{PORT}")
    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
