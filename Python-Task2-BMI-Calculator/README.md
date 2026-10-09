
# Advanced BMI Calculator

## Oasis Infobyte Python Programming Internship
**Task 2: BMI Calculator — Advanced Tier**

## Project Description
The Advanced BMI Calculator is a Python desktop application that calculates Body Mass Index (BMI), classifies results, stores user records in an SQLite database, and visualizes BMI history using a graph.

## Features
- Graphical user interface using Tkinter
- BMI calculation using weight and height
- Colour-coded BMI categories
- Input validation and error messages
- User-specific BMI history
- SQLite database storage
- BMI history table
- BMI history graph using Matplotlib
- Records persist after restarting the application
- Database error handling

## Technologies Used
- Python
- Tkinter
- SQLite3
- Matplotlib
- datetime

## BMI Formula
BMI = Weight (kg) / Height (m)²

## BMI Categories
- Underweight: BMI below 18.5
- Normal weight: BMI from 18.5 to below 25
- Overweight: BMI from 25 to below 30
- Obese: BMI 30 or above

## Requirements
Python 3 and Matplotlib are required.

Install the external dependency:

    python -m pip install -r requirements.txt

## How to Run
1. Open the project folder in VS Code.
2. Install the requirements.
3. Run the application:

       python main.py

4. Enter your name, weight in kilograms, and height in metres.
5. Click Calculate BMI & Save.
6. Use View BMI History to see saved records.
7. Use View BMI Graph to visualize your BMI history.

## Database
The application automatically creates `bmi_history.db` to store BMI records.

## Project Structure
    Python-Task2-BMI-Calculator/
    ├── main.py
    ├── requirements.txt
    ├── README.md
    └── screenshots/

## Author
Suhas Kumbar

## Internship
Developed as part of the Oasis Infobyte Python Programming Internship.
