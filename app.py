import os
import random
import secrets
import hmac
import joblib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
Path(app.instance_path).mkdir(parents=True, exist_ok=True)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.environ.get("DATABASE_URL")
    or "sqlite:///" + (Path(app.instance_path) / "mental_health.db").as_posix()
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# -------- Model --------
MODEL_PATH = BASE_DIR / "models" / "sentiment_model.pkl"
if not MODEL_PATH.is_file():
    raise RuntimeError("Model not found. Run `python train_model.py` first.")
model = joblib.load(MODEL_PATH)

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@app.context_processor
def inject_csrf_token():
    def csrf_token():
        return session.setdefault("_csrf_token", secrets.token_urlsafe(32))

    return {"csrf_token": csrf_token}


@app.before_request
def protect_state_changing_requests():
    if request.method == "POST":
        expected = session.get("_csrf_token", "")
        supplied = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            return jsonify({"error": "Invalid or missing CSRF token."}), 400

# -------- Crisis keywords --------
CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die",
    "self harm", "hurt myself", "no reason to live", "better off dead"
]

# -------- Empathetic response library --------
RESPONSES = {
    "positive": [
        "That's wonderful to hear! 🌟 It sounds like you're in a good place right now. What's been contributing to this positive feeling?",
        "I'm so glad you're feeling this way. Positive moments are worth savoring — what's one thing you'd like to remember about today?",
        "It's great that you're experiencing some joy. How can you carry this feeling forward into the rest of your week?"
    ],
    "negative": [
        "I hear you, and I'm really sorry you're feeling this way. 💙 You're not alone. Would you like to tell me more about what's going on?",
        "Thank you for sharing that with me. It takes courage to put difficult feelings into words. What feels heaviest right now?",
        "That sounds really tough. Remember, feelings are temporary even when they feel overwhelming. What's one small thing that might help you feel a little grounded right now?"
    ],
    "neutral": [
        "Thanks for sharing. How are you feeling underneath the surface today?",
        "I'm here and listening. Is there anything on your mind you'd like to explore a bit more?",
        "It sounds like a fairly steady moment. What would you like to talk about?"
    ]
}

# -------- Models --------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sender = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    text = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(10))
    score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=utcnow)


@login_manager.user_loader
def load_user(user_id):
    if not user_id.isdigit():
        return None
    return db.session.get(User, int(user_id))


# -------- NLP helpers --------
def analyze_sentiment(text: str):
    prediction = model.predict([text])[0]
    probabilities = model.predict_proba([text])[0]
    return prediction, float(max(probabilities))


def detect_crisis(text: str) -> bool:
    t = text.casefold()
    return any(k in t for k in CRISIS_KEYWORDS)


def generate_response(sentiment: str, text: str) -> str:
    if detect_crisis(text):
        return (
            "I'm really concerned about what you've just shared. 💙 You deserve immediate support. "
            "Please contact a crisis line right now:\n\n"
            "• Nigeria: SURPIN — 08091116264\n"
            "• International: https://findahelpline.com\n\n"
            "If you're in immediate danger, please call your local emergency number. "
            "You are not alone, and reaching out is a sign of strength."
        )

    base = random.choice(RESPONSES.get(sentiment, RESPONSES["neutral"]))

    # context-aware follow-ups based on keywords
    t = text.lower()
    if "sleep" in t:
        base += " Sleep and mood are closely linked — have you been resting well lately?"
    elif "work" in t or "school" in t or "exam" in t:
        base += " Academic or work pressure can be exhausting. Have you taken any breaks today?"
    elif "family" in t or "friend" in t:
        base += " Relationships can be a big source of both support and stress. Want to talk about it?"
    elif "tired" in t or "exhausted" in t:
        base += " Emotional fatigue is real. Have you been able to rest or eat properly today?"

    # gentle coping suggestion
    if sentiment == "negative":
        base += "\n\n💡 *A small coping idea:* Try the 4-7-8 breathing technique — inhale for 4s, hold 7s, exhale 8s, three times."

    return base


# -------- Routes --------
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("chat"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("chat"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or len(username) > 80 or not 6 <= len(password) <= 128:
            flash("Username must be 1–80 characters and password 6–128 characters.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return redirect(url_for("register"))
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("chat"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("chat"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=current_user.username)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=current_user.username)


# -------- API --------
@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required."}), 400
    text = data.get("message")
    if not isinstance(text, str):
        return jsonify({"error": "Message must be a string."}), 400
    text = text.strip()
    if not text:
        return jsonify({"error": "Empty message"}), 400
    if len(text) > 2000:
        return jsonify({"error": "Message must be 2,000 characters or fewer."}), 400

    sentiment, score = analyze_sentiment(text)
    reply = generate_response(sentiment, text)

    user_msg = Message(user_id=current_user.id, sender="user",
                       text=text, sentiment=sentiment, score=score)
    bot_msg = Message(user_id=current_user.id, sender="bot",
                      text=reply, sentiment=sentiment, score=score)
    db.session.add_all([user_msg, bot_msg])
    db.session.commit()

    return jsonify({
        "reply": reply,
        "sentiment": sentiment,
        "confidence": round(score * 100, 2),
        "timestamp": utcnow().isoformat()
    })


@app.route("/api/history")
@login_required
def api_history():
    msgs = Message.query.filter_by(user_id=current_user.id)\
                        .order_by(Message.created_at.asc()).all()
    return jsonify([{
        "id": m.id,
        "sender": m.sender,
        "text": m.text,
        "sentiment": m.sentiment,
        "created_at": m.created_at.isoformat()
    } for m in msgs])


@app.route("/api/history/clear", methods=["POST"])
@login_required
def api_clear_history():
    deleted_count = Message.query.filter_by(user_id=current_user.id).delete(
        synchronize_session=False
    )
    db.session.commit()
    return jsonify({"deleted_messages": deleted_count})


@app.route("/api/trends")
@login_required
def api_trends():
    """Daily sentiment counts for the last 14 days."""
    now = utcnow()
    since = now - timedelta(days=14)
    msgs = Message.query.filter(
        Message.user_id == current_user.id,
        Message.sender == "user",
        Message.created_at >= since
    ).all()

    buckets = {}
    for i in range(14):
        d = (now - timedelta(days=13 - i)).date().isoformat()
        buckets[d] = {"positive": 0, "neutral": 0, "negative": 0}

    for m in msgs:
        d = m.created_at.date().isoformat()
        if d in buckets and m.sentiment in buckets[d]:
            buckets[d][m.sentiment] += 1

    return jsonify({
        "labels": list(buckets.keys()),
        "positive": [b["positive"] for b in buckets.values()],
        "neutral":  [b["neutral"]  for b in buckets.values()],
        "negative": [b["negative"] for b in buckets.values()],
    })


@app.route("/api/stats")
@login_required
def api_stats():
    msgs = Message.query.filter_by(user_id=current_user.id, sender="user").all()
    total = len(msgs)
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for m in msgs:
        if m.sentiment in counts:
            counts[m.sentiment] += 1
    return jsonify({
        "total_messages": total,
        "distribution": counts
    })


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "").lower() == "true",
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
    )