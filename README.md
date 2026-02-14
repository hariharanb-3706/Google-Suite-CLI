# 🚀 GSuite CLI - Advanced AI-Powered Google Workspace Tool

A powerful, feature-rich command-line interface for managing your Google Workspace services including Calendar, Gmail, Sheets, Drive, Docs, and Tasks. Enhanced with AI-powered insights, smart scheduling, and natural language processing.

---

## 🏗️ Tech Stack

*   **Core**: Python 3.11+
*   **CLI Framework**: [Click](https://click.palletsprojects.com/)
*   **APIs**: Google Workspace APIs (Calendar, Gmail, Sheets, Drive, Docs, Tasks)
*   **Authentication**: OAuth 2.0 with secure token management
*   **UI/UX**: [Rich](https://github.com/Textualize/rich) for beautiful tables, colors, and progress bars
*   **Infrastructure**: Docker & Docker Compose
*   **Caching**: Redis-backed intelligent caching (10x performance)
*   **AI Engine**: Integrated Natural Language Processing (NLP) for smart commands and insights

---

## 🔄 Workflow

1.  **Configuration**: Load user settings and initialize the `ConfigManager`.
2.  **Authentication**: The `OAuthManager` checks for valid tokens. If missing, it initiates a secure OAuth 2.0 flow via the browser.
3.  **Service Discovery**: Dynamically initializes Google API service clients based on the requested command.
4.  **Cache Layer**: Checks the `CacheManager` (Redis/File-based) for existing data to reduce API calls.
5.  **Execution**: Processes commands through the modular Click groups (`calendar`, `gmail`, `sheets`, etc.).
6.  **AI Enhancement**: For advanced commands, the AI module performs NLP analysis, summarization, or analytics.
7.  **Output**: Formats results into pristine Tables, JSON, or CSV using the `UI` module.

---

## 🧠 Algorithms & Logic

*   **Smart Scheduling**: Analyzes calendar density and focus time availability to suggest optimal meeting slots.
*   **Intelligent Caching**: Implements a TTL-based caching strategy to minimize Google API latency and prevent rate limiting.
*   **NLP Command Parsing**: Translates natural language queries into specific Google API parameters.
*   **OAuth Flow**: Robust token refresh logic ensures long-running sessions without re-authentication.
*   **Data Transformation**: Advanced logic to convert complex Google API nested responses into flat, user-friendly table structures.

---

## 🚀 Features

*   📅 **Calendar**: List, create, search events; AI-powered insights and smart scheduling.
*   📧 **Gmail**: Manage emails, search with advanced syntax, send with attachments, and AI summarization.
*   📊 **Sheets**: Read/write ranges, append data from CSV/JSON, list spreadsheets.
*   📂 **Drive & Docs**: Professional templates (meeting notes, project plans) and file management.
*   🤖 **AI Assistant**: Natural language commands, productivity analytics, and smart replies.
*   💻 **Interactive Mode**: A beautiful REPL-like shell for repeated commands.
*   ⚡ **Performance**: 10x faster operations with intelligent caching.

---

## 📦 Installation & Setup

### Quick Start (Local)

```bash
# Clone the repository
git clone <repository-url>
cd gsuite-cli

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

### Google Cloud Setup

1.  Go to [Google Cloud Console](https://console.cloud.google.com/).
2.  Enable APIs: Calendar, Gmail, Sheets, Drive, Tasks.
3.  Create **OAuth 2.0 Client ID** (Desktop app).
4.  Download the JSON and save as `~/.config/gsuite-cli/credentials.json`.
5.  Run `gs auth login` to authenticate.

### Docker Deployment

```bash
# Provide credentials.json in config/ folder
mkdir -p config
cp credentials.json config/

# Build and start
docker-compose up -d

# Access CLI
docker-compose exec gsuite-cli gs welcome
```

---

## 📖 Usage Examples

```bash
# Check status
gs auth status

# Calendar Insights
gs calendar insights --days 7

# AI Natural Language Command
gs ai ask "show my calendar for today"

# Gmail Search
gs gmail search "is:unread subject:urgent"

# Write to Sheets from CSV
gs sheets write <spreadsheet-id> "Sheet1!A1" data.csv
```

---

## 🛠️ Development

```bash
# Run tests
pytest

# Enable Debug Mode
gs --debug <command>
```

---

## 📄 License

This project is licensed under the MIT License.

---

**Built with ❤️ for the Google Workspace ecosystem**
