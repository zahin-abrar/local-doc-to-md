# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.responses import HTMLResponse, FileResponse
import shutil
import re
from pathlib import Path
from app.converter import convert_to_markdown

app = FastAPI(title="Local Document to Markdown Converter")

# Limit uploads to local/self-hosted safety standards
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Define uploads and outputs directories relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"

# Ensure directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes the uploaded filename to prevent directory traversal
    and ensure local filesystem safety.
    """
    # Extract only the base name
    base = Path(filename).name
    # Retain only alphanumeric characters, dots, dashes, and underscores
    base = re.sub(r'[^a-zA-Z0-9._-]', '_', base)
    # Fallback if filename becomes empty
    if not base or base.strip('.') == '':
        base = "uploaded_document.pdf"
    return base

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/convert")
async def convert_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file does not have a filename.")

    # Sanitize name & prevent directory traversal
    safe_filename = sanitize_filename(file.filename)

    # Validate allowed file extensions (.pdf only for now)
    if not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are allowed.")

    # Check Content-Length header as a quick pre-validation
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File is too large. Maximum size is 50MB.")

    upload_path = UPLOADS_DIR / safe_filename

    # Save the uploaded file to uploads directory while enforcing maximum size limit
    size = 0
    try:
        with open(upload_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="File size exceeds the 50MB limit.")
                buffer.write(chunk)
    except HTTPException:
        if upload_path.exists():
            upload_path.unlink()
        raise
    except Exception as e:
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
    finally:
        await file.close()

    # Convert the saved file to Markdown
    try:
        markdown_text = convert_to_markdown(str(upload_path))
    except Exception as e:
        # Clean up temporary uploaded file if conversion fails
        if upload_path.exists():
            upload_path.unlink()
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

    # Save the Markdown result into outputs directory with the same base name and .md extension
    output_filename = Path(safe_filename).stem + ".md"
    output_path = OUTPUTS_DIR / output_filename

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save output file: {str(e)}")

    return {
        "original_filename": safe_filename,
        "markdown_text": markdown_text,
        "download_url": f"/download/{output_filename}"
    }

@app.get("/download/{filename}")
async def download_file(filename: str):
    # Prevent directory traversal
    safe_filename = Path(filename).name
    file_path = OUTPUTS_DIR / safe_filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="text/markdown",
        filename=safe_filename
    )

@app.post("/cleanup")
def cleanup_files():
    """Purges all user-uploaded and converted files from local storage."""
    deleted_uploads = 0
    deleted_outputs = 0

    # Clean uploads
    for item in UPLOADS_DIR.iterdir():
        if item.is_file() and item.name != ".keep":
            try:
                item.unlink()
                deleted_uploads += 1
            except Exception:
                pass

    # Clean outputs
    for item in OUTPUTS_DIR.iterdir():
        if item.is_file() and item.name != ".keep":
            try:
                item.unlink()
                deleted_outputs += 1
            except Exception:
                pass

    return {
        "status": "success",
        "message": f"Successfully deleted {deleted_uploads} uploads and {deleted_outputs} outputs from local storage."
    }


@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Doc to MD | Local Converter</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-color: #0b0f19;
                --card-bg: rgba(17, 24, 39, 0.6);
                --border-color: rgba(255, 255, 255, 0.08);
                --text-primary: #f8fafc;
                --text-secondary: #94a3b8;
                --accent-blue: #38bdf8;
                --accent-indigo: #818cf8;
                --accent-purple: #a855f7;
                --accent-pink: #ec4899;
                --error-red: #ef4444;
                --success-green: #10b981;
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg-color);
                color: var(--text-primary);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow-x: hidden;
                position: relative;
                padding: 2rem 1rem;
            }

            /* Glowing background blobs */
            .blob {
                position: absolute;
                border-radius: 50%;
                filter: blur(120px);
                opacity: 0.15;
                z-index: 0;
                pointer-events: none;
            }
            .blob-1 {
                top: 10%;
                left: 15%;
                width: 400px;
                height: 400px;
                background: var(--accent-blue);
            }
            .blob-2 {
                bottom: 10%;
                right: 15%;
                width: 450px;
                height: 450px;
                background: var(--accent-purple);
            }

            .app-container {
                width: 100%;
                max-width: 900px;
                z-index: 1;
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
                animation: fadeIn 0.8s ease-out;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .card {
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 24px;
                backdrop-filter: blur(24px);
                -webkit-backdrop-filter: blur(24px);
                padding: 2.5rem;
                box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                gap: 2rem;
                transition: all 0.3s ease;
            }

            header {
                text-align: center;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }

            .badge {
                align-self: center;
                background: rgba(56, 189, 248, 0.1);
                color: var(--accent-blue);
                padding: 0.35rem 0.85rem;
                border-radius: 100px;
                font-size: 0.85rem;
                font-weight: 500;
                border: 1px solid rgba(56, 189, 248, 0.15);
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }

            h1 {
                font-size: 2.5rem;
                font-weight: 700;
                background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-indigo) 50%, var(--accent-purple) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                line-height: 1.2;
                letter-spacing: -0.02em;
            }

            .subtitle {
                color: var(--text-secondary);
                font-size: 1.05rem;
            }

            /* Drag and Drop Zone */
            .dropzone {
                border: 2px dashed rgba(255, 255, 255, 0.15);
                border-radius: 16px;
                padding: 3rem 2rem;
                text-align: center;
                cursor: pointer;
                background: rgba(255, 255, 255, 0.01);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 1.25rem;
                position: relative;
                overflow: hidden;
            }

            .dropzone:hover, .dropzone.dragover {
                border-color: var(--accent-blue);
                background: rgba(56, 189, 248, 0.02);
                box-shadow: 0 0 25px rgba(56, 189, 248, 0.05);
            }

            .dropzone-icon {
                width: 64px;
                height: 64px;
                background: rgba(255, 255, 255, 0.03);
                border-radius: 14px;
                display: flex;
                justify-content: center;
                align-items: center;
                color: var(--accent-blue);
                border: 1px solid var(--border-color);
                transition: all 0.3s ease;
            }

            .dropzone:hover .dropzone-icon {
                transform: translateY(-5px);
                background: rgba(56, 189, 248, 0.1);
                border-color: rgba(56, 189, 248, 0.2);
                box-shadow: 0 8px 20px -6px rgba(56, 189, 248, 0.2);
            }

            .dropzone input[type="file"] {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0;
                cursor: pointer;
            }

            .dropzone-text {
                display: flex;
                flex-direction: column;
                gap: 0.35rem;
            }

            .dropzone-title {
                font-size: 1.15rem;
                font-weight: 500;
                color: var(--text-primary);
            }

            .dropzone-desc {
                font-size: 0.9rem;
                color: var(--text-secondary);
            }

            /* File Info Box */
            .file-info {
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 1rem 1.25rem;
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                margin-top: 1.5rem;
                animation: slideIn 0.3s ease-out;
            }

            @keyframes slideIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .file-details {
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }

            .file-icon {
                color: var(--error-red);
            }

            .file-name {
                font-weight: 500;
                max-width: 400px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .file-size {
                font-size: 0.85rem;
                color: var(--text-secondary);
            }

            .remove-file {
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                transition: color 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0.25rem;
            }

            .remove-file:hover {
                color: var(--error-red);
            }

            /* Buttons styling */
            .btn-group {
                display: flex;
                gap: 1rem;
                width: 100%;
            }

            .btn {
                font-family: inherit;
                padding: 0.85rem 1.75rem;
                border-radius: 12px;
                font-weight: 500;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                border: none;
                text-decoration: none;
            }

            .btn-primary {
                background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
                color: #ffffff;
                flex-grow: 1;
                box-shadow: 0 4px 15px rgba(129, 140, 248, 0.2);
            }

            .btn-primary:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(129, 140, 248, 0.4);
                filter: brightness(1.1);
            }

            .btn-primary:disabled {
                opacity: 0.4;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }

            .btn-secondary {
                background: rgba(255, 255, 255, 0.05);
                color: var(--text-primary);
                border: 1px solid var(--border-color);
            }

            .btn-secondary:hover:not(:disabled) {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }

            /* Error/Status Alerts */
            .alert {
                display: flex;
                align-items: flex-start;
                gap: 0.75rem;
                padding: 1rem 1.25rem;
                border-radius: 12px;
                font-size: 0.95rem;
                line-height: 1.5;
                margin-top: 1.5rem;
                animation: slideIn 0.3s ease-out;
            }

            .alert-error {
                background: rgba(239, 68, 68, 0.08);
                border: 1px solid rgba(239, 68, 68, 0.2);
                color: #fca5a5;
            }

            .alert-error svg {
                flex-shrink: 0;
                color: var(--error-red);
                margin-top: 0.1rem;
            }

            /* Loading Indicator */
            .loading-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 1rem;
                padding: 2rem;
                animation: fadeIn 0.3s ease-out;
            }

            .spinner {
                width: 48px;
                height: 48px;
                border: 3px solid rgba(56, 189, 248, 0.1);
                border-radius: 50%;
                border-top-color: var(--accent-blue);
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            .loading-text {
                color: var(--text-secondary);
                font-weight: 500;
                animation: pulse 1.5s infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 0.6; }
                50% { opacity: 1; }
            }

            /* Preview area */
            .result-container {
                display: flex;
                flex-direction: column;
                gap: 1.25rem;
                animation: slideIn 0.4s ease-out;
            }

            .result-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .result-title {
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .result-actions {
                display: flex;
                gap: 0.5rem;
            }

            .btn-icon {
                width: 40px;
                height: 40px;
                padding: 0;
                border-radius: 10px;
                display: flex;
                justify-content: center;
                align-items: center;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid var(--border-color);
                color: var(--text-primary);
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .btn-icon:hover {
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.15);
                color: var(--accent-blue);
            }

            .preview-area {
                position: relative;
                background: #060913;
                border: 1px solid var(--border-color);
                border-radius: 16px;
                overflow: hidden;
                height: 400px;
                display: flex;
                flex-direction: column;
            }

            .preview-content {
                flex-grow: 1;
                padding: 1.5rem;
                overflow-y: auto;
                font-family: 'Fira Code', monospace;
                font-size: 0.9rem;
                line-height: 1.6;
                color: #cbd5e1;
                white-space: pre-wrap;
                word-break: break-all;
            }

            /* Custom Scrollbar */
            .preview-content::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            .preview-content::-webkit-scrollbar-track {
                background: rgba(0,0,0,0.1);
            }
            .preview-content::-webkit-scrollbar-thumb {
                background: rgba(255,255,255,0.1);
                border-radius: 100px;
            }
            .preview-content::-webkit-scrollbar-thumb:hover {
                background: rgba(255,255,255,0.2);
            }

            .hidden {
                display: none !important;
            }

            .footer-links {
                margin-top: 1.5rem;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 1rem;
                z-index: 1;
            }

            .btn-link {
                background: none;
                border: none;
                color: var(--text-secondary);
                font-family: inherit;
                font-size: 0.85rem;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 0.35rem;
                transition: color 0.2s ease;
            }

            .btn-link:hover {
                color: var(--error-red);
            }
        </style>
    </head>
    <body>
        <div class="blob blob-1"></div>
        <div class="blob blob-2"></div>

        <div class="app-container">
            <div class="card">
                <header>
                    <div class="badge">Self-Hosted</div>
                    <h1>Doc to Markdown</h1>
                    <p class="subtitle">Convert PDF documents into clean, structured Markdown locally</p>
                </header>

                <!-- Upload view -->
                <div id="upload-view" class="view-section">
                    <div class="dropzone" id="dropzone">
                        <div class="dropzone-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                        </div>
                        <div class="dropzone-text">
                            <span class="dropzone-title">Choose PDF or drag here</span>
                            <span class="dropzone-desc">Only PDF files up to 50MB</span>
                        </div>
                        <input type="file" id="file-input" accept=".pdf">
                    </div>

                    <div id="file-selected" class="file-info hidden">
                        <div class="file-details">
                            <svg class="file-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                            <div style="display: flex; flex-direction: column; gap: 0.15rem; text-align: left;">
                                <span class="file-name" id="selected-filename">-</span>
                                <span class="file-size" id="selected-filesize">-</span>
                            </div>
                        </div>
                        <button class="remove-file" id="btn-remove" title="Remove file">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                        </button>
                    </div>

                    <div id="error-alert" class="alert alert-error hidden">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                        <span id="error-text">An error occurred</span>
                    </div>

                    <div class="btn-group" style="margin-top: 1.5rem;">
                        <button class="btn btn-primary" id="btn-convert" disabled>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                            Convert to Markdown
                        </button>
                    </div>
                </div>

                <!-- Loading View -->
                <div id="loading-view" class="view-section hidden">
                    <div class="loading-container">
                        <div class="spinner"></div>
                        <div class="loading-text" id="loading-message">Reading document structure...</div>
                    </div>
                </div>

                <!-- Result View -->
                <div id="result-view" class="view-section hidden">
                    <div class="result-container">
                        <div class="result-header">
                            <div class="result-title">
                                <svg style="color: var(--success-green);" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                                Conversion Complete
                            </div>
                            <div class="result-actions">
                                <button class="btn-icon" id="btn-copy" title="Copy Markdown to Clipboard">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                </button>
                                <button class="btn-icon" id="btn-new" title="Convert another document">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
                                </button>
                            </div>
                        </div>

                        <div class="preview-area">
                            <pre class="preview-content" id="preview-text"></pre>
                        </div>

                        <div class="btn-group">
                            <a href="#" class="btn btn-primary" id="btn-download" download>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                Download Markdown File
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="footer-links">
                <button class="btn-link" id="btn-purge" title="Delete all uploaded and converted files from the local server">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                    Purge Server Files
                </button>
            </div>
        </div>

        <script>
            const fileInput = document.getElementById('file-input');
            const dropzone = document.getElementById('dropzone');
            const fileSelected = document.getElementById('file-selected');
            const selectedFilename = document.getElementById('selected-filename');
            const selectedFilesize = document.getElementById('selected-filesize');
            const btnRemove = document.getElementById('btn-remove');
            const btnConvert = document.getElementById('btn-convert');
            const errorAlert = document.getElementById('error-alert');
            const errorText = document.getElementById('error-text');

            const uploadView = document.getElementById('upload-view');
            const loadingView = document.getElementById('loading-view');
            const resultView = document.getElementById('result-view');
            const loadingMessage = document.getElementById('loading-message');

            const previewText = document.getElementById('preview-text');
            const btnCopy = document.getElementById('btn-copy');
            const btnNew = document.getElementById('btn-new');
            const btnDownload = document.getElementById('btn-download');
            const btnPurge = document.getElementById('btn-purge');

            let selectedFile = null;

            const loadingPhrases = [
                "Uploading file structure...",
                "Reading elements with MarkItDown...",
                "Converting layouts and tables...",
                "Polishing output markdown..."
            ];

            // Format File Size
            function formatBytes(bytes, decimals = 2) {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const dm = decimals < 0 ? 0 : decimals;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
            }

            // Error helper
            function showError(message) {
                errorText.textContent = message;
                errorAlert.classList.remove('hidden');
            }

            function hideError() {
                errorAlert.classList.add('hidden');
            }

            // Handling File Selection
            function handleFile(file) {
                hideError();
                if (!file) return;

                if (!file.name.toLowerCase().endsWith('.pdf')) {
                    showError("Only PDF files are supported at this time.");
                    clearFile();
                    return;
                }

                selectedFile = file;
                selectedFilename.textContent = file.name;
                selectedFilesize.textContent = formatBytes(file.size);
                
                fileSelected.classList.remove('hidden');
                btnConvert.removeAttribute('disabled');
            }

            function clearFile() {
                selectedFile = null;
                fileInput.value = '';
                fileSelected.classList.add('hidden');
                btnConvert.setAttribute('disabled', 'true');
            }

            // Drag & drop handlers
            ['dragenter', 'dragover'].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropzone.classList.add('dragover');
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropzone.classList.remove('dragover');
                }, false);
            });

            dropzone.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const file = dt.files[0];
                handleFile(file);
            });

            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                handleFile(file);
            });

            btnRemove.addEventListener('click', (e) => {
                e.stopPropagation();
                clearFile();
            });

            // Conversion trigger
            btnConvert.addEventListener('click', async () => {
                if (!selectedFile) return;

                // Show loading view
                uploadView.classList.add('hidden');
                loadingView.classList.remove('hidden');
                
                // Cycle loading status text
                let phraseIndex = 0;
                loadingMessage.textContent = loadingPhrases[phraseIndex];
                const intervalId = setInterval(() => {
                    phraseIndex = (phraseIndex + 1) % loadingPhrases.length;
                    loadingMessage.textContent = loadingPhrases[phraseIndex];
                }, 2500);

                const formData = new FormData();
                formData.append('file', selectedFile);

                try {
                    const response = await fetch('/convert', {
                        method: 'POST',
                        body: formData
                    });

                    clearInterval(intervalId);

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || "File conversion failed.");
                    }

                    const result = await response.json();
                    
                    // Show result view
                    previewText.textContent = result.markdown_text;
                    btnDownload.setAttribute('href', result.download_url);
                    btnDownload.setAttribute('download', result.original_filename.replace(/\\\\.pdf$/i, '.md'));

                    loadingView.classList.add('hidden');
                    resultView.classList.remove('hidden');

                } catch (err) {
                    clearInterval(intervalId);
                    loadingView.classList.add('hidden');
                    uploadView.classList.remove('hidden');
                    showError(err.message || "An unexpected error occurred during conversion.");
                }
            });

            // Copy Clipboard helper
            btnCopy.addEventListener('click', () => {
                navigator.clipboard.writeText(previewText.textContent)
                    .then(() => {
                        const originalHTML = btnCopy.innerHTML;
                        btnCopy.innerHTML = '<svg style="color: var(--success-green);" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
                        setTimeout(() => {
                            btnCopy.innerHTML = originalHTML;
                        }, 2000);
                    })
                    .catch(err => {
                        console.error('Could not copy text: ', err);
                    });
            });

            // Reset View
            btnNew.addEventListener('click', () => {
                clearFile();
                resultView.classList.add('hidden');
                uploadView.classList.remove('hidden');
            });

            // Purge Server Files event handler
            btnPurge.addEventListener('click', async () => {
                if (!confirm("Are you sure you want to delete all uploaded and converted files from the local server? This action cannot be undone.")) {
                    return;
                }
                try {
                    const response = await fetch('/cleanup', {
                        method: 'POST'
                    });
                    
                    if (!response.ok) {
                        throw new Error("Server failed to delete files.");
                    }
                    
                    const data = await response.json();
                    alert(data.message);
                    
                    // Reset UI to upload view if currently showing a preview
                    if (!resultView.classList.contains('hidden')) {
                        clearFile();
                        resultView.classList.add('hidden');
                        uploadView.classList.remove('hidden');
                    } else {
                        clearFile();
                    }
                } catch (err) {
                    alert("Failed to purge server files: " + err.message);
                }
            });
        </script>
    </body>
    </html>
    """


