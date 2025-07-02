# SharePoint MCP Server

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

An MCP (Model Context Protocol) server that provides tools for an LLM to interact with a Microsoft SharePoint site. It enables reading, writing, and managing files and folders within a corporate document library.

## ⚠️ CRITICAL: SharePoint Authentication Setup

This server authenticates using **application credentials**, not user credentials. You must be an Azure/M365 administrator or have permissions to create and consent to an "App Registration" in Azure Active Directory.

### Steps to Create App Credentials

1.  **Navigate to Azure Portal**: Go to [portal.azure.com](https://portal.azure.com/) and sign in.
2.  **Go to Azure Active Directory**: Search for and select "Azure Active Directory".
3.  **App Registrations**: In the left menu, go to **App registrations** and click **+ New registration**.
    -   Give it a descriptive name (e.g., `SharePoint-MCP-Server-App`).
    -   Choose "Accounts in this organizational directory only".
    -   Click **Register**.
4.  **Grant API Permissions**:
    -   In your new app registration, go to **API permissions** in the left menu.
    -   Click **+ Add a permission**, then select **Microsoft Graph**.
    -   Select **Application permissions**.
    -   In the search box, type `Sites`.
    -   Check the box for **`Sites.ReadWrite.All`**. *This permission allows the app to read and write to all SharePoint sites.*
    -   Click **Add permissions**.
    -   **Important**: You must now **Grant admin consent**. Click the `Grant admin consent for [Your Tenant]` button and confirm. The status column should update to show green checkmarks.
5.  **Create a Client Secret**:
    -   Go to **Certificates & secrets** in the left menu.
    -   Click **+ New client secret**.
    -   Give it a description (e.g., `mcp-server-key`) and choose an expiration period.
    -   Click **Add**.
    -   **IMMEDIATELY COPY THE SECRET VALUE**. The value is shown only once. This is your `CLIENT_SECRET`.
6.  **Get IDs**:
    -   Go back to the **Overview** tab for your app registration.
    -   Copy the **Application (client) ID**. This is your `CLIENT_ID`.
    -   Copy the **Directory (tenant) ID**. This is your `TENANT_ID`.

You now have all the values needed for the `.env` file.

## ⚙️ Installation

1.  **Clone the Repository** and navigate to this server's directory.
2.  **Create and Activate a Python Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -e .
    ```

## 🔧 Configuration

1.  **Create `.env` file**: Copy the example file.
    ```bash
    cp .env.example .env
    ```
2.  **Edit `.env`**: Open the `.env` file and fill in the values you obtained from the Azure setup process.
    -   `SHAREPOINT_URL`: The full URL to the *specific site* you want the MCP to access (e.g., `https://mycompany.sharepoint.com/sites/Marketing`).
    -   `TENANT_ID`: From your app's Overview page.
    -   `CLIENT_ID`: From your app's Overview page.
    -   `CLIENT_SECRET`: The secret *value* you copied.

## ▶️ Running the Server

Use the script installed by `pip`:

```bash
# Run with settings from .env file
sharepoint-mcp-server

# See all command-line options
sharepoint-mcp-server --help
```

## 🚀 Available Tools

### 📂 `list_document_libraries`
Lists all document libraries in the configured SharePoint site.
- **Parameters**: None
- **Success Response**: `{"status": "success", "libraries": ["Documents", "Style Library", "Site Assets"]}`

### 📄 `list_files`
Lists files and folders within a document library.
- **Parameters**:
    - `library_name` (string, required): The name of the library (e.g., "Documents").
    - `folder_path` (string, optional): A path to a subfolder (e.g., "Annual Reports/2023").
- **Success Response**: `{"status": "success", "items": [{"name": "Q1_Report.pdf", "type": "file"}, {"name": "Images", "type": "folder"}]}`

### ⬆️ `upload_file`
Uploads a file from the server's local filesystem to SharePoint.
- **Parameters**:
    - `local_file_path` (string, required): Path to the file on the server's machine.
    - `library_name` (string, required): The destination library.
    - `remote_folder_path` (string, optional): Destination subfolder.
- **Success Response**: `{"status": "success", "message": "File uploaded successfully.", "sharepoint_url": "/sites/Marketing/Documents/filename.txt"}`

### ⬇️ `download_file`
Downloads a file from SharePoint to the server's local filesystem.
- **Parameters**:
    - `remote_file_path` (string, required): The path within SharePoint (e.g., `Documents/Reports/Q1.pdf`).
    - `local_save_path` (string, required): The path where the file will be saved locally.
- **Success Response**: `{"status": "success", "message": "File downloaded to /path/to/local/save/location/Q1.pdf"}`