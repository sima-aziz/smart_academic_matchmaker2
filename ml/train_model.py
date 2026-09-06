import pandas as pd
import json

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report
)


# ============================================================
# Configuration
# ============================================================

DATASET_PATH = "ml/matchmaking_dataset.csv"

FEATURES = [
    "course_similarity",
    "gpa_similarity",
    "commitment_similarity",
    "age_similarity",
    "year_similarity"
]

TARGET = "successful_collaboration"


# ============================================================
# 1. Load dataset
# ============================================================

df = pd.read_csv(
    DATASET_PATH
)

required_columns = FEATURES + [TARGET]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Dataset is missing required columns: {missing_columns}"
    )

if df[required_columns].isnull().any().any():
    raise ValueError(
        "Dataset contains missing values in ML columns."
    )


print("=" * 70)
print("ML COMPATIBILITY PREDICTOR")
print("=" * 70)


print("Outcome distribution:")
print(df[TARGET].value_counts())
print()

print("Outcome percentages:")
print(
    df[TARGET]
    .value_counts(normalize=True)
    .mul(100)
    .round(2)
)
print()

print()
print(f"Dataset size: {len(df)}")
print()


# 2. Separate features and target

X = df[FEATURES]
y = df[TARGET]


# ============================================================
# 3. Train / test split
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("Data split:")
print(f"Training samples: {len(X_train)}")
print(f"Testing samples:  {len(X_test)}")
print()


# ============================================================
# 4. Standardize features
# ============================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train
)

X_test_scaled = scaler.transform(
    X_test
)


# 5. Train Logistic Regression

model = LogisticRegression(
    random_state=42,
    max_iter=1000
)

model.fit(
    X_train_scaled,
    y_train
)


# 6. Generate predictions

probabilities = model.predict_proba(
    X_test_scaled
)[:, 1]

predictions = (
    probabilities >= 0.50
).astype(int)


# 7. Evaluate model

accuracy = accuracy_score(
    y_test,
    predictions
)

precision = precision_score(
    y_test,
    predictions,
    zero_division=0
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0
)

f1 = f1_score(
    y_test,
    predictions,
    zero_division=0
)

roc_auc = roc_auc_score(
    y_test,
    probabilities
)

oracle_auc = roc_auc_score(
    y_test,
    df.loc[y_test.index, "simulated_probability"]
)

print(
    f"Latent simulation probability ROC-AUC {oracle_auc:.4f}"
)

metrics = {
    "dataset_size": len(df),
    "training_samples": len(X_train),
    "testing_samples": len(X_test),
    "accuracy": accuracy,
    "precision": precision,
    "recall": recall,
    "f1_score": f1,
    "roc_auc": roc_auc
}

with open(
    "ml/training_metrics.json",
    "w"
) as file:
    json.dump(
        metrics,
        file,
        indent=4
    )


print("=" * 70)
print("LOGISTIC REGRESSION RESULTS")
print("=" * 70)

print(
    f"Accuracy:  {accuracy:.4f}"
)

print(
    f"Precision: {precision:.4f}"
)

print(
    f"Recall:    {recall:.4f}"
)

print(
    f"F1-score:  {f1:.4f}"
)

print(
    f"ROC-AUC:   {roc_auc:.4f}"
)

print()


# 8. Classification report

print("=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


# 9. Feature coefficients

coefficients = model.coef_[0]


absolute_coefficients = abs(coefficients)

importance_percentages = (
    absolute_coefficients
    / absolute_coefficients.sum()
    * 100
)

feature_importance = pd.DataFrame({
    "feature": FEATURES,
    "coefficient": coefficients,
    "absolute_coefficient": absolute_coefficients,
    "relative_importance_percent": importance_percentages
})

feature_importance = (
    feature_importance
    .sort_values(
        "absolute_coefficient",
        ascending=False
    )
)

feature_importance.to_csv(
    "ml/learned_coefficients.csv",
    index=False
)

print("=" * 70)
print("LEARNED FEATURE IMPORTANCE")
print("=" * 70)

print(
    feature_importance.to_string(
        index=False
    )
)

print()


# 10. Example predictions

print("=" * 70)
print("EXAMPLE ML PREDICTIONS")
print("=" * 70)

examples = X_test.copy()

examples["actual"] = y_test.values

examples["predicted_probability"] = probabilities

examples["prediction"] = predictions

print(
    examples
    .head(10)
    .to_string(index=False)
)

print()


# 11. Save model components

import pickle

with open(
    "ml/logistic_model.pkl",
    "wb"
) as file:

    pickle.dump(
        model,
        file
    )


with open(
    "ml/feature_scaler.pkl",
    "wb"
) as file:

    pickle.dump(
        scaler,
        file
    )


print("=" * 70)
print("MODEL SAVED")
print("=" * 70)

print("ml/logistic_model.pkl")
print("ml/feature_scaler.pkl")