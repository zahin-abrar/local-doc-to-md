# Local Document to Markdown Converter

A self-hosted, clean, and minimal PDF-to-Markdown converter using FastAPI and MarkItDown.

This tool lets you upload a PDF file through a browser, convert it into Markdown, preview the generated content, and download the converted `.md` file.

## Features

- Upload a PDF file from the browser
- Convert PDF content into Markdown using MarkItDown
- Preview the generated Markdown in the browser
- Download the converted `.md` file
- Purge uploaded and generated files from the server
- Dockerized for local/self-hosted usage

## Project Structure

```text
local-doc-to-md/
├── app/
│   ├── main.py        # FastAPI application and routing
│   ├── converter.py   # MarkItDown conversion logic
│   ├── static/        # Static assets (CSS, JS)
│   └── templates/     # HTML templates
├── uploads/
│   └── .keep          # Keeps the directory tracked by Git
├── outputs/
│   └── .keep          # Keeps the directory tracked by Git
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup & Running

### 1. Create a Virtual Environment

Create a virtual environment to manage dependencies locally:

```bash
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# Or on Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

### 3. Run the Development Server

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --reload
```

Once running, you can access:

- **Homepage**: http://localhost:8080
- **Health Check**: http://localhost:8080/health
- **API Documentation**: http://localhost:8080/docs

## Running with Docker (Recommended)

You can run the application containerized using Docker and Docker Compose. This manages all Python and system dependencies automatically.

### 1. Build and Start the Container

```bash
docker compose up --build -d
```

This command will:

- Build the Docker image
- Expose the app on port `8080`
- Mount local `./uploads` and `./outputs` directories as persistent volumes

### 2. Access the Application

Once the container is running, open:

- **Homepage**: http://localhost:8080
- **Health Check**: http://localhost:8080/health
- **API Documentation**: http://localhost:8080/docs

### 3. Stop the Container

To stop the services, run:

```bash
docker compose down
```

## Basic Usage

1. Open the application in your browser.
2. Select a PDF file.
3. Click the convert button.
4. Preview the generated Markdown.
5. Download the `.md` file.
6. Use the purge option if you want to clear uploaded and generated files from the server.

## Security & Self-Hosted Guardrails

This utility is designed **strictly for local, self-hosted use cases** such as running on your own computer or a trusted intranet.

It includes the following safety features to protect your local environment:

- **Filename Sanitization**: Uploaded filenames are stripped of non-alphanumeric characters, except `.`, `_`, and `-`, to prevent shell injection or command issues.
- **Path Traversal Protection**: Only the base filename of uploads and output downloads is evaluated, preventing directory traversal attacks such as `../` paths.
- **Upload Size Limit**: Strict 50MB file size limits are enforced on the backend during stream writing.
- **Server File Purging**: You can instantly delete all uploaded and converted files from the local server's disk using the **"Purge Server Files"** button in the UI or by calling the `POST /cleanup` endpoint.

## Known Limitations

- **File Formats**: Currently supports `.pdf` file uploads only.
- **Encrypted PDFs**: Password-protected or encrypted PDF documents cannot be parsed. You must decrypt them before conversion.
- **Optical Character Recognition (OCR)**: MarkItDown parses digital text, layouts, and tables natively. Scanned image-only PDFs that contain no embedded text layer will yield empty output unless processed by an external OCR layer.

## Roadmap Ideas

These are possible future improvements for later versions:

- Support for additional document formats such as `.docx`, `.pptx`, `.xlsx`, and `.html`
- Batch file conversion
- ZIP download for multiple converted files
- Drag-and-drop upload
- Markdown copy-to-clipboard button
- Better conversion history
- Optional OCR support for scanned PDFs
- Improved UI polish and responsive layout
