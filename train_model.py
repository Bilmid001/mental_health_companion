import pandas as pd
import joblib
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "train.csv"
MODEL_PATH = BASE_DIR / "models" / "sentiment_model.pkl"

df = pd.read_csv(DATA_PATH)
required_columns = {"text", "sentiment"}
if not required_columns.issubset(df.columns):
    raise ValueError("train.csv must contain 'text' and 'sentiment' columns.")

df = df.dropna(subset=["text", "sentiment"])
df["text"] = df["text"].astype(str).str.strip()
df["sentiment"] = df["sentiment"].astype(str).str.strip().str.lower()
df = df[df["text"] != ""]
if df["sentiment"].nunique() < 2 or df["sentiment"].value_counts().min() < 2:
    raise ValueError("Each sentiment class must have at least two non-empty examples.")

X_train, X_test, y_train, y_test = train_test_split(
    df["text"], df["sentiment"], test_size=0.2, random_state=42, stratify=df["sentiment"]
)

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
    ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))
])

pipeline.fit(X_train, y_train)
preds = pipeline.predict(X_test)

print("=== Model Evaluation ===")
print(f"Accuracy : {accuracy_score(y_test, preds):.4f}")
print(f"Precision: {precision_score(y_test, preds, average='weighted', zero_division=0):.4f}")
print(f"Recall   : {recall_score(y_test, preds, average='weighted', zero_division=0):.4f}")
print(f"F1-Score : {f1_score(y_test, preds, average='weighted', zero_division=0):.4f}")
print(classification_report(y_test, preds, zero_division=0))

pipeline.fit(df["text"], df["sentiment"])
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(pipeline, MODEL_PATH)
print(f"Model saved to {MODEL_PATH}")