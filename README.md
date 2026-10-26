# 🎓 AI Study Planner with Exam Prediction System – Agentic Edition

An AI-powered educational assistant designed to help students plan their studies, predict exam performance, identify weak topics, and prepare more effectively using Artificial Intelligence and agent-based workflows.

## 📌 Project Overview

The **AI Study Planner with Exam Prediction System** is an intelligent study management application built using Python, Streamlit, and Google Gemini AI. It helps students create personalized study schedules based on their exam dates, available study hours, preparation levels, and preferred learning styles.

The system also provides exam prediction insights, potential exam questions, score-range estimates, and weak-topic identification to support smarter and more focused exam preparation.

## 🎯 Objectives

- Generate personalized and adaptive study plans.
- Predict potential exam performance using available preparation information.
- Identify weak topics and recommend areas for improvement.
- Generate likely exam questions for revision.
- Analyze previous question papers to support exam preparation.
- Maintain student learning information and evaluation history.
- Provide an interactive and user-friendly interface.

## ✨ Key Features

### 1. 📅 AI Study Planner
- Create customized study schedules.
- Set exam dates and daily study hours.
- Choose preparation levels and learning preferences.
- Generate study plans using Google Gemini AI.

### 2. 🔮 Exam Prediction System
- Estimate potential exam performance.
- Display predicted score ranges and probability-based insights.
- Identify weak topics that require additional preparation.
- Generate likely exam questions for practice.

*Note: Predictions are estimates, not guaranteed exam results. Their reliability depends on the quality of the available information and the prediction method used.*

### 3. 🤖 Agent-Based Architecture
The application is designed around specialized agent roles:

- **Tutor Agent:** Supports learning and study-plan generation.
- **Memory Agent:** Helps maintain relevant student learning information.
- **Evaluator Agent:** Supports assessment and performance evaluation.
- **Adaptive Engine:** Helps tailor study recommendations based on available learning information.

### 4. 📚 Previous Question Paper Analysis
- Analyze previous exam question papers.
- Identify important topics and recurring question patterns when supported by the input.
- Assist students in prioritizing revision.

### 5. 🧠 Student Memory Management
- Maintain student profiles and evaluation records.
- Track weak topics and study-planning activity.
- Use stored information to support more personalized recommendations.

### 6. 🌐 Interactive Web Application
- Built with Streamlit.
- Provides an interactive dashboard and configuration controls.
- Supports Google Gemini AI integration.
- Includes Progressive Web App (PWA) related files for potential app-like access.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Streamlit | User interface and web application |
| Google Gemini AI | AI-powered study assistance |
| JSON | Student memory and configuration storage |
| SQLite | Local database storage |
| HTML, CSS and JavaScript | Supporting web and PWA functionality |
| Git and GitHub | Version control and project hosting |

*The technologies listed above are based on the current project structure; individual features depend on their implementation in the source code.*

## 📂 Project Structure

```text
ai_study_planner_agents/
│
├── .streamlit/          # Streamlit configuration
├── static/              # Static assets
├── __pycache__/         # Python-generated cache files
│
├── app.py               # Main Streamlit application
├── database.py          # Database operations
├── model.py             # AI/model-related functionality
├── server.py            # Server-related functionality
│
├── memory.json          # Student memory data
├── study_planner.db     # Local SQLite database
├── manifest.json        # PWA manifest
├── sw.js                # Service worker
│
├── requirements.txt     # Python dependencies
├── package-lock.json    # Node.js dependency lock file, if applicable
├── .gitignore           # Git ignore rules
└── README.md            # Project documentation
```

## ⚙️ Installation and Setup

### Prerequisites

Install the following before running the application:

- Python 3.10 or a compatible version supported by the project's dependencies.
- Visual Studio Code or another Python IDE.
- A Google Gemini API key.
- Git (optional, for version control).

### Step 1: Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd ai_study_planner_agents
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual GitHub repository URL.

If you already have the project on your computer, open its existing folder in VS Code instead.

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure the Gemini API Key

If the application reads its key using `st.secrets["GEMINI_API_KEY"]`, create the following file:

`.streamlit/secrets.toml`

Add:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
```

Replace the placeholder with your own API key.

**Security:** Never upload your real API key or `secrets.toml` file to a public GitHub repository. Keep credentials private and add sensitive files to `.gitignore`.

### Step 5: Run the Application

From the project root directory, run:

```bash
streamlit run app.py
```

Open the local URL displayed in the terminal, usually:

```text
http://localhost:8501
```

## 🚀 How to Use the Application

1. Launch the application.
2. Configure the Gemini API key if required.
3. Enter your exam date and available daily study hours.
4. Select your preparation level and learning style.
5. Generate a personalized study plan.
6. Review exam prediction insights and likely questions.
7. Examine weak-topic alerts and prioritize revision.
8. Analyze previous question papers when the feature is available.
9. Use evaluation history and recommendations to improve your preparation.

## 🔮 Future Enhancements

- Student authentication and individual accounts.
- Cloud-based database integration.
- Advanced machine-learning-based exam performance prediction.
- Performance dashboards with charts and progress tracking.
- Automated reminders and notifications.
- PDF export of study plans and reports.
- Mobile-friendly Progressive Web App enhancements.
- Integration with learning management systems.
- More advanced autonomous agent workflows.

## 🎓 Academic Significance

This project demonstrates how generative AI, personalized learning, student data management, and agent-based workflows can be combined to develop an intelligent educational application.

The exam prediction module aims to help students understand their preparation status, identify areas requiring improvement, and allocate study time more effectively.

## 👨‍💻 Project Information

**Project Title:** AI Study Planner with Exam Prediction System – Agentic Edition

**Domain:** Artificial Intelligence and Educational Technology

**Programming Language:** Python

**AI Integration:** Google Gemini AI

**Interface Framework:** Streamlit

**Project Type:** MCA Academic Project

## 📜 Disclaimer

This application is intended for educational and study-planning purposes. AI-generated content and predicted scores may contain inaccuracies. The application does not guarantee actual examination questions, marks, or academic outcomes. Students should verify important information using their official syllabus and learning materials.

## 🙌 Acknowledgements

Thanks to the developers of Python, Streamlit, Google Gemini, and the open-source technologies that support this project.

---

⭐ If you find this project useful, consider starring the repository on GitHub.
