# Scopus MCP Server

**Scopus MCP Server** is an MCP (Modular Communication Protocol) server that exposes tools to interact with Elsevier's Scopus API and extract text content from publicly accessible PDF URLs.

## 🚀 Features

- 🔍 **Scopus Search**: Queries the Scopus database via Elsevier's API to retrieve academic research results.
- 📄 **PDF Extraction**: Downloads a PDF from a URL and extracts plain text content.

## 📦 Project Structure

```
root/
├── scopus_mcp_server/
│   └── server.py        # Contains the MCP server logic and tool definitions
├── pyproject.toml       # Project configuration and dependencies
└── README.md
```

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/scopus_mcp_server.git
   cd scopus_mcp_server
   ```

2. Create a `.env` file at the root of the project (or in the parent directory of `server.py`) and add your Scopus API key:
   ```env
   SCOPUS_API_KEY=your_scopus_api_key_here
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

## ▶️ Usage

Run the server from the command line:

```bash
scopus-mcp-server
```

The server listens for MCP messages on `stdin` and exposes two tools:

### 🔹 `scopus_search`

Search for academic publications using Scopus.

**Parameters:**
- `query` *(str, required)*: Search query.
- `count` *(int, optional)*: Number of results (default: 5).
- `start` *(int, optional)*: Starting index for pagination.

**Example MCP message:**
```json
{
  "tool": "scopus_search",
  "parameters": {
    "query": "machine learning AND healthcare",
    "count": 3
  }
}
```

### 🔹 `read_pdf_from_url`

Downloads a PDF and extracts its text content.

**Parameters:**
- `url` *(str, required)*: Direct link to a PDF file.

**Example MCP message:**
```json
{
  "tool": "read_pdf_from_url",
  "parameters": {
    "url": "https://arxiv.org/pdf/2106.01345.pdf"
  }
}
```

## ✅ Key Dependencies

- `mcp` – For building the MCP server.
- `requests` – For HTTP requests to APIs and PDF files.
- `PyPDF2` – For reading PDF documents.
- `python-dotenv` – For loading API keys from `.env`.
- `ascii-colors` – For colorful terminal messages.

## 📄 License

MIT – Feel free to use, modify, and distribute this project.

---

**Author**: Your Name – [parisneo_ai@gmail.com](mailto:parisneo_ai@gmail.com)
