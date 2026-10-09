# Advanced Python Voice Assistant

## Internship Task
**Oasis Infobyte – Python Programming Internship**

**Task 1: Advanced Voice Assistant**

## Project Description
An advanced Python-based voice assistant that listens to spoken commands, processes them using rule-based intent recognition, and responds with voice output. It supports everyday tasks such as checking the weather, setting reminders, searching the web, and retrieving general knowledge.

## Features
- Voice input through a microphone
- Voice responses using Windows PowerShell speech synthesis
- Greeting and conversational responses
- Current time and date
- Weather information using the OpenWeatherMap API
- Timed reminders
- Google web searches
- Opens Google and YouTube
- General knowledge answers using the Wikipedia API
- Rule-based command recognition
- Error handling for unclear or unrecognized commands
- Exit commands such as `exit`, `quit`, and `stop`

## Technologies Used
- Python
- SpeechRecognition
- PyAudio
- Requests
- Wikipedia MediaWiki API
- OpenWeatherMap API
- Windows PowerShell System.Speech
- `datetime`
- `webbrowser`
- `threading`
- `queue`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/suhas018-hub/OIBSIP.git
   ```
2. Open the project folder:
   ```bash
   cd OIBSIP/Python-Task1-VoiceAssistant
   ```
3. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
4. Activate it on Windows:
   ```bash
   .venv\Scripts\activate
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

For weather functionality, configure your OpenWeatherMap API key as an environment variable in Command Prompt:

```cmd
set OPENWEATHER_API_KEY=YOUR_API_KEY
```

Replace `YOUR_API_KEY` with your own API key. Run the application from the same terminal. Never commit API keys or other secrets to GitHub.

**Note:** Voice output uses Windows PowerShell System.Speech, so this implementation is intended for Windows.

## How to Run

Run the following command from the project folder:

```bash
python main.py
```

Allow microphone access and speak a supported command.

## Example Commands
- "Hello"
- "What is the time?"
- "What is today's date?"
- "What's the weather?"
- "Remind me in one minute to drink water"
- "Who is the president of India?"
- "Search for Python programming tutorials"
- "Open YouTube"
- "Open Google"
- "Exit"

## Project Structure

```text
OIBSIP/
└── Python-Task1-VoiceAssistant/
    ├── main.py
    ├── requirements.txt
    ├── README.md
    └── screenshots/
```

## Internship
Developed as part of the Oasis Infobyte Python Programming Internship.

## Author
Suhas Kumbar
