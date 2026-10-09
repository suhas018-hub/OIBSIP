import subprocess
import datetime
import json
import os
import queue
import re
import smtplib
import ssl
import threading
import time
import webbrowser
from email.message import EmailMessage
from urllib.parse import quote_plus

import requests
import speech_recognition as sr
import pyttsx3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "commands.json")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

speech_queue = queue.Queue()
reminder_queue = queue.Queue()
stop_event = threading.Event()
speech_ready = threading.Event()
speech_engine_error = None



def speech_worker():
    """Speak queued responses using Windows PowerShell speech."""
    global speech_engine_error
    speech_ready.set()

    while True:
        item = speech_queue.get()

        if item is None:
            speech_queue.task_done()
            break

        text, finished = item

        try:
            escaped_text = text.replace("'", "''")
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Speak('{escaped_text}'); "
                "$s.Dispose()"
            )

            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

        except Exception as exc:
            print("[TTS error]", exc)

        finally:
            if finished:
                finished.set()
            speech_queue.task_done()



speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()
speech_ready.wait(timeout=5)



def speak(text, wait=True):
    """Print and speak the assistant's response."""
    text = str(text)
    print("Assistant:", text)

    if speech_engine_error is not None:
        print("TTS initialization failed:", speech_engine_error)
        return

    finished = threading.Event() if wait else None
    speech_queue.put((text, finished))

    if finished:
        finished.wait(timeout=60)



def listen():
    """Listen to one voice command and return recognized lowercase text."""
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("\nListening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        command = recognizer.recognize_google(audio).strip().lower()
        print("You:", command)
        return command
    except sr.WaitTimeoutError:
        speak("I did not hear anything. Please try again.")
    except sr.UnknownValueError:
        speak("Sorry, I could not understand. Please repeat.")
    except sr.RequestError:
        speak("Speech recognition is unavailable. Check your internet connection.")
    except (OSError, AttributeError) as exc:
        print("Microphone error:", exc)
        speak("I could not access the microphone.")
    return ""


def create_default_config():
    """Create a starter custom-command configuration if missing."""
    if not os.path.exists(CONFIG_FILE):
        defaults = {"commands": [
            {"phrases": ["open github", "github"], "url": "https://github.com"},
            {"phrases": ["open linkedin", "linkedin"], "url": "https://www.linkedin.com"}
        ]}
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(defaults, file, indent=4)


def run_custom_command(command):
    """Run a URL command defined in commands.json."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        for item in data.get("commands", []):
            if any(str(p).lower() in command for p in item.get("phrases", [])):
                url = str(item.get("url", "")).strip()
                if url.startswith(("https://", "http://")):
                    speak("Opening your custom command.")
                    webbrowser.open(url)
                    return True
    except (OSError, json.JSONDecodeError) as exc:
        print("Custom command configuration error:", exc)
    return False


def detect_intent(command):
    """Match common natural-language requests to supported intents."""
    text = command.lower().strip()
    if re.search(r"\b(hello|hi|hey)\b", text):
        return "greeting"
    if re.search(r"\b(time|clock)\b", text):
        return "time"
    if re.search(r"\b(date|today|day is it)\b", text):
        return "date"
    if re.search(r"\b(weather|temperature|forecast)\b", text):
        return "weather"
    if re.search(r"\b(remind|reminder|timer)\b", text):
        return "reminder"
    if re.search(r"\b(email|send a mail|send mail)\b", text):
        return "email"
    if re.search(r"\b(search|google|look up|find online)\b", text):
        return "search"
    if re.search(r"\b(open youtube|youtube)\b", text):
        return "youtube"
    if re.search(r"\b(open google|google home)\b", text):
        return "google"
    if re.search(r"\b(who is|what is|who was|tell me about)\b", text):
        return "knowledge"
    if re.search(r"\b(exit|quit|stop assistant|goodbye)\b", text):
        return "exit"
    return "unknown"


def tell_time():
    speak("The current time is " + datetime.datetime.now().strftime("%I:%M %p") + ".")


def tell_date():
    speak("Today is " + datetime.datetime.now().strftime("%A, %d %B %Y") + ".")


def search_web(command):
    query = re.sub(
        r"^(please\s+)?(search for|search|google|look up|find online)\s*",
        "", command, flags=re.IGNORECASE
    ).strip()
    if not query:
        speak("What would you like me to search for?")
        query = listen()
    if query:
        speak("Searching the web for " + query + ".")
        webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
    else:
        speak("I did not receive a search topic.")


def get_weather(command):
    # Read at call time so a terminal environment variable is detected.
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        speak("Weather needs an OpenWeatherMap API key. Set OPENWEATHER_API_KEY in the same terminal used to start the assistant.")
        return

    city = re.sub(
        r"\b(weather|temperature|forecast|in|for|what is|what's|the)\b",
        " ", command, flags=re.IGNORECASE
    )
    city = re.sub(r"\s+", " ", city).strip(" ?.,")

    if not city:
        speak("Which city should I check?")
        city = listen()
    if not city:
        speak("Please provide a city name.")
        return

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=10
        )
        if response.status_code == 404:
            speak("I could not find that city.")
            return
        if response.status_code == 401:
            speak("The weather API key is invalid or not activated yet.")
            return
        response.raise_for_status()
        data = response.json()
        temp_c = data["main"]["temp"]
        temp_f = temp_c * 9 / 5 + 32
        humidity = data["main"]["humidity"]
        condition = data["weather"][0]["description"]
        wind = data["wind"]["speed"]
        speak(
            f"Weather in {data['name']}: {condition}. Temperature "
            f"{temp_c:.1f} degrees Celsius, or {temp_f:.1f} Fahrenheit. "
            f"Humidity {humidity} percent. Wind speed {wind} meters per second."
        )
    except requests.Timeout:
        speak("The weather request timed out. Please try again.")
    except requests.RequestException as exc:
        print("Weather request failed:", exc)
        speak("I could not retrieve weather data. Check your internet connection.")
    except (KeyError, ValueError) as exc:
        print("Unexpected weather response:", exc)
        speak("The weather service returned an unexpected response.")


def reminder_worker():
    """Wait for reminder deadlines and announce them."""
    while not stop_event.is_set():
        try:
            deadline, message = reminder_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        remaining = deadline - time.monotonic()
        if remaining > 0 and stop_event.wait(remaining):
            reminder_queue.task_done()
            break
        if not stop_event.is_set():
            speak("Reminder: " + message)
        reminder_queue.task_done()


def set_reminder(command):
    match = re.search(
        r"\bin\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)\b",
        command
    )
    if not match:
        speak("Say something like: remind me in 2 minutes to drink water.")
        return
    amount = int(match.group(1))
    unit = match.group(2)
    if unit.startswith(("second", "sec")):
        seconds = amount
    elif unit.startswith(("minute", "min")):
        seconds = amount * 60
    else:
        seconds = amount * 3600
    if seconds <= 0 or seconds > 86400:
        speak("Please choose a duration between 1 second and 24 hours.")
        return
    message = re.sub(
        r"^(please\s+)?(remind me|set a reminder|set timer)\s*",
        "", command, flags=re.IGNORECASE
    )
    message = re.sub(
        r"\bin\s+\d+\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)\b",
        "", message, flags=re.IGNORECASE
    )
    message = re.sub(r"^\s*(to|that)\s+", "", message).strip(" .,?")
    if not message:
        message = "Your timer has finished."
    reminder_queue.put((time.monotonic() + seconds, message))
    speak(f"Reminder set for {amount} {unit}. I will remind you.")


def send_email():
    """Send email only after reading details and receiving confirmation."""
    address = os.getenv("ASSISTANT_EMAIL", "").strip()
    password = os.getenv("ASSISTANT_EMAIL_PASSWORD", "").strip()
    recipient = os.getenv("ASSISTANT_EMAIL_RECIPIENT", "").strip()
    if not all([address, password, recipient]):
        speak("Email is not configured. Set the sender address, app password, and recipient environment variables.")
        return
    speak("What should the email subject be?")
    subject = listen()
    if not subject:
        speak("Email cancelled because no subject was received.")
        return
    speak("What should the email message say?")
    body = listen()
    if not body:
        speak("Email cancelled because no message was received.")
        return
    speak(f"I will send an email to the configured recipient with subject {subject}. Say confirm send to send it, or say cancel.")
    if "confirm send" not in listen():
        speak("Email cancelled.")
        return
    message = EmailMessage()
    message["From"] = address
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context, timeout=15) as server:
            server.login(address, password)
            server.send_message(message)
        speak("Your email was sent successfully.")
    except (smtplib.SMTPException, OSError) as exc:
        print("Email sending failed:", exc)
        speak("I could not send the email. Please check the configuration.")




def answer_question(command):
    """Answer general knowledge questions using Wikipedia."""

    question = re.sub(
        r"^\s*(please\s+)?",
        "",
        command,
        flags=re.IGNORECASE
    ).strip(" ?.")

    # Remove common question phrases
    question = re.sub(
        r"^(who is|what is|who was|what was|tell me about|"
        r"what is the name of|what's the name of|"
        r"just say the name of)\s+",
        "",
        question,
        flags=re.IGNORECASE
    ).strip(" ?.")

    # Direct answers for common questions
    q = question.lower()

    if "prime minister of india" in q or "indian prime minister" in q:
        speak("Narendra Modi")
        return

    if "president of india" in q or "indian president" in q:
        speak("Droupadi Murmu")
        return

    if not question:
        speak("What would you like to know about?")
        question = listen()

    if not question:
        speak("I did not receive a question.")
        return

    try:
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": question,
                "gsrnamespace": 0,
                "gsrlimit": 1,
                "prop": "extracts",
                "exintro": 1,
                "explaintext": 1,
                "format": "json"
            },
            headers={"User-Agent": "OIBSIPVoiceAssistant/1.0"},
            timeout=10
        )
        response.raise_for_status()

        pages = response.json().get("query", {}).get("pages", {})

        if not pages:
            speak("Sorry, I could not find an answer. Try asking differently.")
            return

        page = next(iter(pages.values()))
        answer = page.get("extract", "").strip()

        if answer:
            sentences = re.split(r'(?<=[.!?])\s+', answer)
            speak(" ".join(sentences[:2])[:400])
        else:
            speak("I could not find an answer for that topic.")

    except requests.RequestException as error:
        print("Wikipedia request failed:", error)
        speak("I could not connect to Wikipedia. Please check your internet connection.")

    except (ValueError, KeyError) as error:
        print("Wikipedia response error:", error)
        speak("I could not process the answer.")




def process_command(command):
    
    if not command:
        return True
    intent = detect_intent(command)
    if intent == "greeting":
        speak("Hello! How can I help you?")
    elif intent == "time":
        tell_time()
    elif any(phrase in command.lower() for phrase in [
            "who are you",
            "what are you",
            "introduce yourself",
            "your name"
        ]):
            speak(
                "I am your Python voice assistant, "
                "built with speech recognition, voice responses, "
                "weather updates, reminders, and general knowledge."
            )
    elif intent == "date":
        tell_date()
    elif intent == "weather":
        get_weather(command)
    elif intent == "reminder":
        set_reminder(command)
    elif intent == "email":
        send_email()
    elif intent == "search":
        search_web(command)
    elif intent == "youtube":
        speak("Opening YouTube.")
        webbrowser.open("https://www.youtube.com")
    elif intent == "google":
        speak("Opening Google.")
        webbrowser.open("https://www.google.com")
    elif intent == "knowledge":
        answer_question(command)
    elif intent == "exit":
        speak("Goodbye! Have a nice day.")
        return False
    elif run_custom_command(command):
        pass
    else:
        speak("I don't know that command yet. You can ask for the time, date, weather, a reminder, a web search, or a general knowledge question.")
    return True


def main():
    create_default_config()
    threading.Thread(target=reminder_worker, daemon=True).start()
    speak("Hello! I am your advanced voice assistant.")
    speak("You can ask for the time, date, weather, reminders, web searches, general knowledge, or email.")
    try:
        running = True
        while running:
            command = listen()
            if command:
                running = process_command(command)
    except KeyboardInterrupt:
        print("\nAssistant stopped by keyboard.")
    finally:
        stop_event.set()
        # Finish queued speech before shutting down the speech thread.
        speech_queue.join()
        speech_queue.put(None)
        speech_thread.join(timeout=3)
        print("Voice assistant closed.")


if __name__ == "__main__":
    main()
