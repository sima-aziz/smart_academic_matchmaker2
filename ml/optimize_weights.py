import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


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

# Project 1 baseline weights
BASELINE_WEIGHTS = {
    "course_similarity": 35.0,
    "gpa_similarity": 25.0,
    "commitment_similarity": 20.0,
    "age_similarity": 10.0,
    "year_similarity": 10.0
}

# Controls how strongly ML influences the original weights
ALPHA = 0.50


# ============================================================
# 1. Load dataset
# ============================================================

df = pd.read_csv(DATASET_PATH)

X = df[FEATURES]
y = df["successful_collaboration"]


# ============================================================
# 2. Train Logistic Regression
# ============================================================

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X)

model = LogisticRegression(
    random_state=42
)

model.fit(
    X_scaled,
    y
)


# ============================================================
# 3. Extract ML coefficients
# ============================================================

coefficients = model.coef_[0]

ml_importance = pd.DataFrame({
    "feature": FEATURES,
    "coefficient": coefficients
})

# Absolute values represent relative importance
ml_importance["absolute_coefficient"] = (
    ml_importance["coefficient"].abs()
)


# ============================================================
# 4. Normalize ML importance to 100
# ============================================================

total_importance = (
    ml_importance["absolute_coefficient"].sum()
)

ml_importance["ml_weight"] = (
    ml_importance["absolute_coefficient"]
    / total_importance
    * 100
)


# ============================================================
# 5. Convert Project 1 weights into a DataFrame
# ============================================================

weights = pd.DataFrame({
    "feature": FEATURES
})

weights["baseline_weight"] = weights["feature"].map(
    BASELINE_WEIGHTS
)

weights = weights.merge(
    ml_importance[
        ["feature", "coefficient", "ml_weight"]
    ],
    on="feature"
)


# ============================================================
# 6. Calculate hybrid weights
# ============================================================

weights["hybrid_weight"] = (
    (1 - ALPHA) * weights["baseline_weight"]
    + ALPHA * weights["ml_weight"]
)


# ============================================================
# 7. Normalize hybrid weights
# ============================================================

weights["hybrid_weight"] = (
    weights["hybrid_weight"]
    / weights["hybrid_weight"].sum()
    * 100
)


# ============================================================
# 8. Display results
# ============================================================

print("=" * 70)
print("ML-INFORMED WEIGHT ADAPTATION")
print("=" * 70)

print()
print(f"Adaptation strength (alpha): {ALPHA}")
print()

print(weights.to_string(index=False))

print()
print("=" * 70)
print("FINAL WEIGHTS")
print("=" * 70)

for _, row in weights.iterrows():

    print(
        f"{row['feature']:<25} "
        f"{row['hybrid_weight']:.2f}"
    )