
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt

DB_NAME = "bmi_history.db"


# ---------- DATABASE ----------
def init_database():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bmi_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    weight REAL NOT NULL,
                    height REAL NOT NULL,
                    bmi REAL NOT NULL,
                    category TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
    except sqlite3.Error as error:
        messagebox.showerror("Database Error", str(error))


# ---------- BMI CALCULATION ----------
def get_category(bmi):
    if bmi < 18.5:
        return "Underweight", "#1565C0"
    elif bmi < 25:
        return "Normal weight", "#16803C"
    elif bmi < 30:
        return "Overweight", "#E67E22"
    return "Obese", "#D32F2F"


def calculate_bmi():
    name = name_entry.get().strip()

    try:
        weight = float(weight_entry.get())
        height = float(height_entry.get())

        if not name:
            messagebox.showerror("Input Error", "Please enter your name.")
            return

        if weight <= 0 or height <= 0:
            messagebox.showerror(
                "Input Error",
                "Weight and height must be greater than zero."
            )
            return

        if weight > 500 or height > 3:
            messagebox.showerror(
                "Input Error",
                "Please check your weight and height values."
            )
            return

        bmi = weight / (height ** 2)
        category, color = get_category(bmi)

        result_label.config(
            text=f"{name}, your BMI is {bmi:.2f}\nCategory: {category}",
            fg=color
        )

        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("""
                    INSERT INTO bmi_records
                    (name, weight, height, bmi, category, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    name, weight, height, bmi, category,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

            messagebox.showinfo(
                "Success", "BMI calculated and saved successfully."
            )

        except sqlite3.Error as error:
            messagebox.showerror(
                "Database Error",
                f"Could not save the record:\n{error}"
            )

    except ValueError:
        messagebox.showerror(
            "Input Error",
            "Please enter valid numeric weight and height."
        )


# ---------- BMI HISTORY ----------
def show_history():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            records = conn.execute("""
                SELECT name, weight, height, bmi, category, recorded_at
                FROM bmi_records
                WHERE name = ? COLLATE NOCASE
                ORDER BY id DESC
            """, (name_entry.get().strip(),)).fetchall()

        if not name_entry.get().strip():
            messagebox.showwarning(
                "Name Required", "Enter a name to view BMI history."
            )
            return

        history_window = tk.Toplevel(root)
        history_window.title("BMI History")
        history_window.geometry("900x350")

        columns = (
            "Name", "Weight (kg)", "Height (m)",
            "BMI", "Category", "Date"
        )

        table = ttk.Treeview(
            history_window, columns=columns, show="headings"
        )

        for column in columns:
            table.heading(column, text=column)
            table.column(column, width=140, anchor="center")

        for record in records:
            table.insert("", tk.END, values=record)

        table.pack(fill="both", expand=True, padx=10, pady=10)

        if not records:
            messagebox.showinfo(
                "BMI History",
                "No records found for this user.",
                parent=history_window
            )

    except sqlite3.Error as error:
        messagebox.showerror("Database Error", str(error))


# ---------- BMI GRAPH ----------
def show_graph():
    name = name_entry.get().strip()

    if not name:
        messagebox.showwarning(
            "Name Required", "Enter a name to view BMI history."
        )
        return

    try:
        with sqlite3.connect(DB_NAME) as conn:
            records = conn.execute("""
                SELECT recorded_at, bmi
                FROM bmi_records
                WHERE name = ? COLLATE NOCASE
                ORDER BY id
            """, (name,)).fetchall()

        if not records:
            messagebox.showinfo(
                "BMI Graph", "No BMI records found for this user."
            )
            return

        dates = [record[0] for record in records]
        bmi_values = [record[1] for record in records]

        plt.figure(figsize=(9, 5))
        plt.plot(dates, bmi_values, marker="o", linewidth=2)
        plt.axhline(
            18.5, linestyle="--", label="Normal range lower limit"
        )
        plt.axhline(
            25, linestyle="--", label="Normal range upper limit"
        )
        plt.title(f"BMI History for {name}")
        plt.xlabel("Recorded Date and Time")
        plt.ylabel("BMI")
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.show()

    except sqlite3.Error as error:
        messagebox.showerror("Database Error", str(error))


# ---------- GUI ----------
root = tk.Tk()
root.title("Advanced BMI Calculator")
root.geometry("460x590")
root.resizable(False, False)
root.configure(bg="#F0F4F8")

init_database()

tk.Label(
    root,
    text="BMI CALCULATOR",
    font=("Arial", 22, "bold"),
    bg="#F0F4F8",
    fg="#17365D"
).pack(pady=20)

tk.Label(root, text="Your Name", bg="#F0F4F8").pack()
name_entry = tk.Entry(root, font=("Arial", 12), justify="center")
name_entry.pack(pady=6)

tk.Label(root, text="Weight (kg)", bg="#F0F4F8").pack()
weight_entry = tk.Entry(root, font=("Arial", 12), justify="center")
weight_entry.pack(pady=6)

tk.Label(root, text="Height (metres)", bg="#F0F4F8").pack()
height_entry = tk.Entry(root, font=("Arial", 12), justify="center")
height_entry.pack(pady=6)

tk.Button(
    root,
    text="Calculate BMI & Save",
    command=calculate_bmi,
    font=("Arial", 12, "bold"),
    bg="#17365D",
    fg="white",
    padx=12,
    pady=8
).pack(pady=15)

tk.Button(
    root,
    text="View BMI History",
    command=show_history,
    font=("Arial", 11),
    padx=12,
    pady=5
).pack(pady=5)

tk.Button(
    root,
    text="View BMI Graph",
    command=show_graph,
    font=("Arial", 11),
    padx=12,
    pady=5
).pack(pady=5)

result_label = tk.Label(
    root,
    text="Enter your details above",
    font=("Arial", 14, "bold"),
    bg="#F0F4F8",
    fg="#333333",
    justify="center"
)
result_label.pack(pady=20)

tk.Label(
    root,
    text="BMI = Weight (kg) / Height (m)²",
    font=("Arial", 9),
    bg="#F0F4F8",
    fg="#555555"
).pack(side="bottom", pady=10)

root.mainloop()
