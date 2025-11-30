# Baby Activity Tracker - Architecture & Plan

## 1. Overview
A smart baby activity tracker that uses natural language (voice/text) to log and retrieve data.

## 2. Architecture
We will follow your proposed modular architecture with some refinements for practical implementation:

### A. Core API (The "Brain" & Storage)
*   **Role**: Manages data persistence, business logic, and user accounts.
*   **Tech**: Python (FastAPI) or Node.js (Express/NestJS).
*   **Database**: MongoDB or PostgreSQL (flexible schema is good for varied activities).
*   **Endpoints**: `/activities`, `/babies`, `/users`.

### B. Intelligence Layer (The "Agent")
*   **Role**: Interprets natural language and converts it into structured API calls.
*   **Implementation**:
    *   This could be a service that accepts text/audio.
    *   It uses an LLM (Gemini/OpenAI) to parse intent.
    *   *Example*: Input "Tom drank 150ml milk" -> Output `POST /activities { type: "feeding", amount: 150, unit: "ml", baby: "Tom" }`.

### C. MCP Server (The "Bridge")
*   **Role**: Exposes the Core API as "Tools" for AI agents.
*   **Benefit**: Allows you to connect this system to *any* MCP-compliant client (like Claude Desktop, or your own custom agent).
*   **Tools**: `log_activity`, `get_last_sleep`, `summarize_day`.

### D. Client (The "Interface")
*   **Role**: The user interface for voice/text input.
*   **Tech**: A simple Web App (React/Vite) or Mobile App.
*   **Features**: Microphone button (Speech-to-Text), Chat interface.

## 3. Workflow
1.  **User** says: "Leo just fell asleep."
2.  **Client** converts audio to text (or sends audio).
3.  **Agent** receives text, identifies intent ("Sleep started"), and calls the **MCP Tool** (or API directly).
4.  **API** saves the record to the **Database**.

## 4. Next Steps
1.  **Initialize Project**: Create the folder structure.
2.  **Define Data Model**: What does an "Activity" look like?
3.  **Build Core API**: Basic CRUD.
