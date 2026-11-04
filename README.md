# Mindful Companion — AI Mental Health Chatbot

## Setup
Requires Python 3.10 or later.

From the project directory, create and activate a virtual environment, then install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Train the sentiment model and start the app:

```powershell
python train_model.py
python app.py
```

Open http://127.0.0.1:5000. The model and SQLite database are resolved relative to the project, so these commands also work when launched from another working directory.

For deployments, set a persistent, randomly generated `SECRET_KEY` in the environment and serve the app behind an HTTPS-capable production WSGI server. The built-in Flask server is for local development only.

## Features
- Register/Login (secure password hashing)
- Chat with empathetic AI (TF-IDF + Logistic Regression)
- Public landing page, responsive signed-in sidebar, and mobile navigation drawer
- Optional spoken replies and browser-based voice input in chat (browser support and microphone permission required)
- Crisis keyword detection with helpline info
- Real-time sentiment badge
- 14-day emotional trend chart
- Emotion distribution doughnut chart
- Fully responsive (Bootstrap 5)

Voice input is provided by the browser's Web Speech API and requires a supported browser and microphone permission. Replies are read aloud automatically by default; each assistant reply also has a **Listen** button to play it again. Spoken replies use the browser's speech synthesis voices. Typed chat remains available if either voice feature is unsupported.

## Evaluation metrics
Printed by `train_model.py` — use these in your Chapter 4 results.