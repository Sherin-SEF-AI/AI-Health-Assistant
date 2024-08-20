import sys
import requests
import base64
import time
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QFileDialog, QLabel, QProgressBar, 
                             QListWidget, QTabWidget, QLineEdit, QFormLayout, QSpinBox,
                             QComboBox, QCalendarWidget, QMessageBox, QScrollArea, QDateEdit,
                             QDoubleSpinBox)
from PyQt6.QtGui import QPixmap, QFont, QIcon, QPainter
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtCharts import QChart, QChartView, QLineSeries

API_KEY = ''
API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'

class AnalysisThread(QThread):
    analysis_complete = pyqtSignal(str)
    analysis_error = pyqtSignal(str)
    retry_attempt = pyqtSignal(int)

    def __init__(self, image_path, max_retries=3, retry_delay=5):
        QThread.__init__(self)
        self.image_path = image_path
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def run(self):
        prompt = "Analyze this image of a meal or exercise routine and provide personalized health advice, dietary suggestions, or fitness plans based on what you see. Include estimated calorie count for meals and suggested duration for exercises."
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {
                        "mime_type": "image/jpeg",
                        "data": self.encode_image(self.image_path)
                    }}
                ]
            }]
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(f'{API_URL}?key={API_KEY}', headers=headers, json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result['candidates'][0]['content']['parts'][0]['text']
                    self.analysis_complete.emit(generated_text)
                    return
                elif response.status_code == 503:
                    if attempt < self.max_retries - 1:
                        self.retry_attempt.emit(attempt + 1)
                        time.sleep(self.retry_delay)
                    else:
                        self.analysis_error.emit("The model is currently overloaded. Please try again later.")
                else:
                    self.analysis_error.emit(f"Error: {response.status_code} - {response.text}")
                    return
            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    self.retry_attempt.emit(attempt + 1)
                    time.sleep(self.retry_delay)
                else:
                    self.analysis_error.emit(f"Network error: {str(e)}")
                    return

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

class HealthAssistant(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.history = []
        self.load_user_data()

    def initUI(self):
        self.setWindowTitle('AI Health Assistant')
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon('health_icon.png'))  # Add an icon file to your project

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Left panel for navigation
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.nav_buttons = []
        for nav_item in ['Dashboard', 'Image Analysis', 'Meal Planner', 'Exercise Tracker', 'Profile']:
            btn = QPushButton(nav_item)
            btn.clicked.connect(lambda checked, text=nav_item: self.switch_tab(text))
            left_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        left_layout.addStretch()

        # Right panel for content
        self.content_tabs = QTabWidget()
        self.content_tabs.setTabPosition(QTabWidget.TabPosition.East)
        self.content_tabs.tabBar().setVisible(False)
        
        self.init_dashboard_tab()
        self.init_image_analysis_tab()
        self.init_meal_planner_tab()
        self.init_exercise_tracker_tab()
        self.init_profile_tab()

        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.content_tabs, 4)

        self.switch_tab('Dashboard')

    def switch_tab(self, tab_name):
        self.content_tabs.setCurrentIndex(self.content_tabs.indexOf(self.content_tabs.findChild(QWidget, tab_name)))
        for btn in self.nav_buttons:
            btn.setStyleSheet("" if btn.text() != tab_name else "background-color: #e0e0e0;")

    def init_dashboard_tab(self):
        dashboard = QWidget()
        dashboard.setObjectName("Dashboard")
        layout = QVBoxLayout(dashboard)

        welcome_label = QLabel("Welcome to Your Health Dashboard")
        welcome_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(welcome_label)

        # Add charts and summary widgets here
        self.weight_chart = self.create_weight_chart()
        layout.addWidget(self.weight_chart)

        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        
        calories_label = QLabel("Today's Calories: 1800 / 2000")
        steps_label = QLabel("Steps: 8000 / 10000")
        water_label = QLabel("Water: 6 / 8 glasses")
        
        summary_layout.addWidget(calories_label)
        summary_layout.addWidget(steps_label)
        summary_layout.addWidget(water_label)
        
        layout.addWidget(summary_widget)

        self.content_tabs.addTab(dashboard, "Dashboard")

    def create_weight_chart(self):
        series = QLineSeries()
        # Sample data - replace with actual user data
        for i in range(10):
            series.append(i, 70 + i * 0.1)

        chart = QChart()
        chart.addSeries(series)
        chart.createDefaultAxes()
        chart.setTitle("Weight Trend")

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return chart_view

    def init_image_analysis_tab(self):
        image_analysis = QWidget()
        image_analysis.setObjectName("Image Analysis")
        layout = QVBoxLayout(image_analysis)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        layout.addWidget(self.image_label)

        button_layout = QHBoxLayout()
        self.upload_button = QPushButton('Upload Image')
        self.upload_button.clicked.connect(self.upload_image)
        button_layout.addWidget(self.upload_button)

        self.analyze_button = QPushButton('Analyze')
        self.analyze_button.clicked.connect(self.analyze_image)
        self.analyze_button.setEnabled(False)
        button_layout.addWidget(self.analyze_button)

        layout.addLayout(button_layout)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Arial", 12))
        layout.addWidget(QLabel("Analysis Results:"))
        layout.addWidget(self.result_text)

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.load_history_item)
        layout.addWidget(QLabel("Analysis History:"))
        layout.addWidget(self.history_list)

        self.content_tabs.addTab(image_analysis, "Image Analysis")

    def init_meal_planner_tab(self):
        meal_planner = QWidget()
        meal_planner.setObjectName("Meal Planner")
        layout = QVBoxLayout(meal_planner)

        # Calendar for selecting date
        self.meal_calendar = QCalendarWidget()
        self.meal_calendar.selectionChanged.connect(self.update_meal_plan)
        layout.addWidget(self.meal_calendar)

        # Meal inputs
        self.meal_inputs = {}
        for meal in ['Breakfast', 'Lunch', 'Dinner', 'Snacks']:
            meal_layout = QHBoxLayout()
            meal_layout.addWidget(QLabel(f"{meal}:"))
            meal_input = QLineEdit()
            self.meal_inputs[meal] = meal_input
            meal_layout.addWidget(meal_input)
            layout.addLayout(meal_layout)

        # Save button
        save_button = QPushButton("Save Meal Plan")
        save_button.clicked.connect(self.save_meal_plan)
        layout.addWidget(save_button)

        self.content_tabs.addTab(meal_planner, "Meal Planner")

    def init_exercise_tracker_tab(self):
        exercise_tracker = QWidget()
        exercise_tracker.setObjectName("Exercise Tracker")
        layout = QVBoxLayout(exercise_tracker)

        # Date selection
        self.exercise_date = QDateEdit()
        self.exercise_date.setDate(QDate.currentDate())
        layout.addWidget(self.exercise_date)

        # Exercise inputs
        form_layout = QFormLayout()
        self.exercise_type = QComboBox()
        self.exercise_type.addItems(['Running', 'Cycling', 'Swimming', 'Weight Training', 'Yoga'])
        form_layout.addRow("Type:", self.exercise_type)

        self.exercise_duration = QSpinBox()
        self.exercise_duration.setRange(1, 300)
        self.exercise_duration.setSuffix(" minutes")
        form_layout.addRow("Duration:", self.exercise_duration)

        self.exercise_intensity = QComboBox()
        self.exercise_intensity.addItems(['Low', 'Medium', 'High'])
        form_layout.addRow("Intensity:", self.exercise_intensity)

        layout.addLayout(form_layout)

        # Save button
        save_button = QPushButton("Log Exercise")
        save_button.clicked.connect(self.log_exercise)
        layout.addWidget(save_button)

        # Exercise history
        self.exercise_history = QListWidget()
        layout.addWidget(QLabel("Exercise History:"))
        layout.addWidget(self.exercise_history)

        self.content_tabs.addTab(exercise_tracker, "Exercise Tracker")

    def init_profile_tab(self):
        profile = QWidget()
        profile.setObjectName("Profile")
        layout = QVBoxLayout(profile)

        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)

        self.age_input = QSpinBox()
        self.age_input.setRange(1, 120)
        form_layout.addRow("Age:", self.age_input)

        self.gender_input = QComboBox()
        self.gender_input.addItems(['Male', 'Female', 'Other'])
        form_layout.addRow("Gender:", self.gender_input)

        self.height_input = QSpinBox()
        self.height_input.setRange(100, 250)
        self.height_input.setSuffix(" cm")
        form_layout.addRow("Height:", self.height_input)

        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(30, 300)
        self.weight_input.setSuffix(" kg")
        form_layout.addRow("Weight:", self.weight_input)

        layout.addLayout(form_layout)

        save_button = QPushButton("Save Profile")
        save_button.clicked.connect(self.save_profile)
        layout.addWidget(save_button)

        self.content_tabs.addTab(profile, "Profile")

    def upload_image(self):
        file_dialog = QFileDialog()
        self.image_path, _ = file_dialog.getOpenFileName(self, 'Open Image', '', 'Image Files (*.png *.jpg *.jpeg)')
        if self.image_path:
            pixmap = QPixmap(self.image_path)
            self.image_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio))
            self.analyze_button.setEnabled(True)
            self.status_label.setText("Image uploaded. Ready for analysis.")

    def analyze_image(self):
        if not self.image_path:
            self.result_text.setText("Please upload an image first.")
            return

        self.progress_bar.setValue(0)
        self.analyze_button.setEnabled(False)
        self.upload_button.setEnabled(False)
        self.status_label.setText("Analyzing image...")

        self.analysis_thread = AnalysisThread(self.image_path)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.analysis_error.connect(self.on_analysis_error)
        self.analysis_thread.retry_attempt.connect(self.on_retry_attempt)
        self.analysis_thread.start()

        # Simulate progress
        for i in range(101):
            self.progress_bar.setValue(i)
            QApplication.processEvents()
            self.analysis_thread.msleep(50)

    def on_analysis_complete(self, result):
        self.result_text.setText(result)
        self.analyze_button.setEnabled(True)
        self.upload_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText("Analysis complete.")

        # Add to history
        history_item = f"Analysis {len(self.history) + 1}"
        self.history.append((self.image_path, result))
        self.history_list.addItem(history_item)

    def on_analysis_error(self, error_message):
        self.result_text.setText(error_message)
        self.analyze_button.setEnabled(True)
        self.upload_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Analysis failed. Please try again.")
        
        QMessageBox.warning(self, "Analysis Error", error_message)

    def on_retry_attempt(self, attempt):
        self.status_label.setText(f"Retrying analysis (Attempt {attempt})...")
        self.progress_bar.setValue(0)

    def load_history_item(self, item):
        index = self.history_list.row(item)
        image_path, result = self.history[index]
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio))
        self.result_text.setText(result)

    def update_meal_plan(self):
        selected_date = self.meal_calendar.selectedDate().toString("yyyy-MM-dd")
        meal_plan = self.load_meal_plan(selected_date)
        for meal, input_field in self.meal_inputs.items():
            input_field.setText(meal_plan.get(meal, ""))

    def save_meal_plan(self):
        selected_date = self.meal_calendar.selectedDate().toString("yyyy-MM-dd")
        meal_plan = {meal: input_field.text() for meal, input_field in self.meal_inputs.items()}
        self.save_meal_plan_data(selected_date, meal_plan)
        QMessageBox.information(self, "Meal Plan", "Meal plan saved successfully!")

    def log_exercise(self):
        date = self.exercise_date.date().toString("yyyy-MM-dd")
        exercise_data = {
            "type": self.exercise_type.currentText(),
            "duration": self.exercise_duration.value(),
            "intensity": self.exercise_intensity.currentText()
        }
        self.save_exercise_data(date, exercise_data)
        self.update_exercise_history()
        QMessageBox.information(self, "Exercise Logged", "Exercise session logged successfully!")

    def update_exercise_history(self):
        self.exercise_history.clear()
        exercise_data = self.load_exercise_data()
        for date, exercises in exercise_data.items():
            for exercise in exercises:
                item_text = f"{date}: {exercise['type']} - {exercise['duration']} mins ({exercise['intensity']})"
                self.exercise_history.addItem(item_text)

    def save_profile(self):
        profile_data = {
            "name": self.name_input.text(),
            "age": self.age_input.value(),
            "gender": self.gender_input.currentText(),
            "height": self.height_input.value(),
            "weight": self.weight_input.value()
        }
        self.save_user_data(profile_data)
        QMessageBox.information(self, "Profile Saved", "Your profile has been updated successfully!")

    def load_user_data(self):
        if os.path.exists("user_data.json"):
            with open("user_data.json", "r") as file:
                data = json.load(file)
                self.name_input.setText(data.get("name", ""))
                self.age_input.setValue(data.get("age", 0))
                self.gender_input.setCurrentText(data.get("gender", ""))
                self.height_input.setValue(data.get("height", 170))
                self.weight_input.setValue(data.get("weight", 70))

    def save_user_data(self, data):
        with open("user_data.json", "w") as file:
            json.dump(data, file)

    def load_meal_plan(self, date):
        if os.path.exists("meal_plans.json"):
            with open("meal_plans.json", "r") as file:
                all_meal_plans = json.load(file)
                return all_meal_plans.get(date, {})
        return {}

    def save_meal_plan_data(self, date, meal_plan):
        if os.path.exists("meal_plans.json"):
            with open("meal_plans.json", "r") as file:
                all_meal_plans = json.load(file)
        else:
            all_meal_plans = {}
        
        all_meal_plans[date] = meal_plan
        
        with open("meal_plans.json", "w") as file:
            json.dump(all_meal_plans, file)

    def load_exercise_data(self):
        if os.path.exists("exercise_data.json"):
            with open("exercise_data.json", "r") as file:
                return json.load(file)
        return {}

    def save_exercise_data(self, date, exercise_data):
        all_exercise_data = self.load_exercise_data()
        
        if date in all_exercise_data:
            all_exercise_data[date].append(exercise_data)
        else:
            all_exercise_data[date] = [exercise_data]
        
        with open("exercise_data.json", "w") as file:
            json.dump(all_exercise_data, file)

def main():
    app = QApplication(sys.argv)
    ex = HealthAssistant()
    ex.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

