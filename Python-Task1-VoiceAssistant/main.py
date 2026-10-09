import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser


# Initialize text-to-speech engine
#engine = pyttsx3.init()


def speak(text):
    """Convert text to speech."""
    print("Assistant:", text)

    engine = pyttsx3.init("sapi5")
    engine.setProperty("volume", 1.0)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def listen():
    """Listen to the user's voice and convert it to text."""
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("\nListening...")
        recognizer.adjust_for_ambient_noise(source, duration=1)

        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            command = recognizer.recognize_google(audio)
            print("You:", command)
            return command.lower()

        except sr.WaitTimeoutError:
            speak("I did not hear anything,please try again")
            return ""

        except sr.UnknownValueError:
            speak("Sorry, I could not understand you,please repeat")
            return ""

        except sr.RequestError:
            speak("Speech recognition service is unavailable.")
            return ""


def process_command(command):
    """Process the user's command."""

    if "hello" in command or "hi" in command:
        speak("Hello! How can I help you?")

    elif "time" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {current_time}.")

    elif "date" in command:
        current_date = datetime.datetime.now().strftime("%d %B %Y")
        speak(f"Today's date is {current_date}.")

    elif "search" in command:
        query = command.replace("search", "").strip()

        if query:
            speak(f"Searching for {query}.")
            webbrowser.open(
                "https://www.google.com/search?q=" + query.replace(" ", "+")
            )
        else:
            speak("Please tell me what you want to search for.")

    elif "open youtube" in command:
        speak("Opening YouTube.")
        webbrowser.open("https://www.youtube.com")

    elif "open google" in command:
        speak("Opening Google.")
        webbrowser.open("https://www.google.com")

    elif "exit" in command or "quit" in command or "stop" in command:
        speak("Goodbye! Have a nice day.")
        return False

    else:
        speak("I don't know that command yet.")

    return True


def main():
    """Main program."""
    speak("Hello! I am your voice assistant.")
    speak("You can ask me for the time, date, search the web, or open websites.")

    running = True

    while running:
        command = listen()

        if command:
            running = process_command(command)


if __name__ == "__main__":
    main()