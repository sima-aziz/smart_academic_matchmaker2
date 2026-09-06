import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
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

# Project 1 baseline weights
BASELINE_WEIGHTS = {
    "course_similarity": 35.0,
    "gpa_similarity": 25.0,
    "commitment_similarity": 20.0,
    "age_similarity": 10.0,
    "year_similarity": 10.0
}

# Adaptation strengths to test
ALPHAS = [
    0.00,
    0.25,
    0.50,
    0.75,
    1.00
]


# ============================================================
# 1. Load dataset
# ============================================================

df = pd.read_csv(
    DATASET_PATH
)

X = df[FEATURES]
y = df[TARGET]


# ============================================================
# 2. Train / test split
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# ============================================================
# 3. Train Logistic Regression ONLY on training data
# ============================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train
)

X_test_scaled = scaler.transform(
    X_test
)

model = LogisticRegression(
    random_state=42
)

model.fit(
    X_train_scaled,
    y_train
)


# ============================================================
# 4. Extract ML feature importance
# ============================================================

coefficients = model.coef_[0]

absolute_coefficients = abs(
    coefficients
)

total_importance = sum(
    absolute_coefficients
)

ml_weights = {}

for feature, coefficient in zip(
    FEATURES,
    absolute_coefficients
):

    ml_weights[feature] = (
        coefficient
        / total_importance
        * 100
    )


# ============================================================
# 5. Display ML weights
# ============================================================

print("=" * 75)
print("ML-DERIVED WEIGHTS FROM TRAINING DATA")
print("=" * 75)

for feature in FEATURES:

    print(
        f"{feature:<25}"
        f"{ml_weights[feature]:>8.2f}"
    )

print()


# ============================================================
# 6. Calculate matching scores
# ============================================================

def calculate_scores(data, weights):

    scores = (
        data["course_similarity"]
        * weights["course_similarity"]

        + data["gpa_similarity"]
        * weights["gpa_similarity"]

        + data["commitment_similarity"]
        * weights["commitment_similarity"]

        + data["age_similarity"]
        * weights["age_similarity"]

        + data["year_similarity"]
        * weights["year_similarity"]
    )

    return scores*100


# ============================================================
# 7. Evaluate a weighting system
# ============================================================

def evaluate(scores, actual):

    # Convert score to binary prediction
    predictions = (
        scores >= 50
    ).astype(int)

    return {
        "accuracy": accuracy_score(
            actual,
            predictions
        ),

        "precision": precision_score(
            actual,
            predictions,
            zero_division=0
        ),

        "recall": recall_score(
            actual,
            predictions,
            zero_division=0
        ),

        "f1": f1_score(
            actual,
            predictions,
            zero_division=0
        ),

        "roc_auc": roc_auc_score(
            actual,
            scores
        )
    }


# ============================================================
# 8. Test different alpha values
# ============================================================

results = []

for alpha in ALPHAS:

    # --------------------------------------------------------
    # Combine baseline and ML weights
    # --------------------------------------------------------

    hybrid_weights = {}

    for feature in FEATURES:

        hybrid_weights[feature] = (
            (1 - alpha)
            * BASELINE_WEIGHTS[feature]

            + alpha
            * ml_weights[feature]
        )

    # Ensure total = 100
    total_weight = sum(
        hybrid_weights.values()
    )

    for feature in FEATURES:

        hybrid_weights[feature] = (
            hybrid_weights[feature]
            / total_weight
            * 100
        )

    # --------------------------------------------------------
    # Evaluate ONLY on unseen test data
    # --------------------------------------------------------

    scores = calculate_scores(
        X_test,
        hybrid_weights
    )

    metrics = evaluate(
        scores,
        y_test
    )

    results.append({
        "alpha": alpha,
        **metrics
    })


# ============================================================
# 9. Display results
# ============================================================

results_df = pd.DataFrame(
    results
)

print("=" * 75)
print("ADAPTATION STRENGTH EXPERIMENT")
print("=" * 75)

print(
    results_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)

print()


# ============================================================
# 10. Find best alpha
# ============================================================

best_result = results_df.loc[
    results_df["roc_auc"].idxmax()
]

print("=" * 75)
print("BEST ADAPTATION STRENGTH")
print("=" * 75)

print(
    f"Alpha:   {best_result['alpha']:.2f}"
)

print(
    f"Accuracy: {best_result['accuracy']:.4f}"
)

print(
    f"Precision: {best_result['precision']:.4f}"
)

print(
    f"Recall:    {best_result['recall']:.4f}"
)

print(
    f"F1:        {best_result['f1']:.4f}"
)

print(
    f"ROC-AUC:   {best_result['roc_auc']:.4f}"
)

print()


# ============================================================
# 11. Show final weights for best alpha
# ============================================================

best_alpha = best_result["alpha"]

best_weights = {}

for feature in FEATURES:

    best_weights[feature] = (
        (1 - best_alpha)
        * BASELINE_WEIGHTS[feature]

        + best_alpha
        * ml_weights[feature]
    )

total_weight = sum(
    best_weights.values()
)

for feature in FEATURES:

    best_weights[feature] = (
        best_weights[feature]
        / total_weight
        * 100
    )


print("=" * 75)
print("FINAL WEIGHTS FOR BEST ALPHA")
print("=" * 75)

for feature in FEATURES:

    print(
        f"{feature:<25}"
        f"{best_weights[feature]:>8.2f}"
    )