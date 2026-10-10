# OIBSIP Python Task 5 — Advanced Chat Application

A real-time chat application built with Python, FastAPI, WebSockets, SQLite, HTML, CSS, and JavaScript. It supports authenticated users, group chat rooms, private messaging, and persistent message history.

## Features

- User registration and login
- Password hashing using PBKDF2
- Real-time group messaging using WebSockets
- Multiple chat rooms: General, Technology, and Random
- Private messaging between registered users
- Private message history saved in SQLite
- Group message history saved in SQLite
- Online user list and typing indicators
- Emoji support
- Browser notifications when permitted
- Responsive web interface

## Technologies Used

- **Backend:** Python, FastAPI, Uvicorn
- **Real-time communication:** WebSockets
- **Database:** SQLite
- **Frontend:** HTML5, CSS3, JavaScript

## Project Structure

```text
Python-Task5-ChatApplication/
├── main.py
├── chat.db
├── requirements.txt
├── README.md
└── static/
    ├── index.html
    ├── style.css
    └── script.js
```

The `chat.db` database is generated automatically when the application starts.

## Installation and Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate the environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the application

```bash
python -m uvicorn main:app --reload
```

### 5. Open the application

Visit:

http://127.0.0.1:8000

Register two accounts in separate browser windows to test real-time group and private messaging.

## Database and Message Storage

User account information and password hashes are stored in SQLite. Group messages are stored with their room names, sender names, and timestamps. Private messages are stored with sender, recipient, message content, and timestamp, allowing previous conversations to be loaded again.

Messages are stored without end-to-end encryption. This project is intended for learning and demonstration, not production use.

## Testing

- Registration, login, and logout
- Real-time messaging between two accounts
- Switching between chat rooms
- Private messages delivered without duplicate display
- Private conversation history after logging out and back in
- Group message history persistence
- Online user updates

## Internship

**Program:** Oasis Infobyte Internship Program (OIBSIP)  
**Track:** Python Programming  
**Task:** Task 5 — Advanced Chat Application

Developed as a practical project to learn backend APIs, WebSockets, database persistence, authentication, and frontend integration.