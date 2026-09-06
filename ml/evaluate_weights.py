import pandas as pd

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

# Project 1 weights
BASELINE_WEIGHTS = {
    "course_similarity": 35.0,
    "gpa_similarity": 25.0,
    "commitment_similarity": 20.0,
    "age_similarity": 10.0,
    "year_similarity": 10.0
}

# ML-informed weights from optimize_weights.py
ML_WEIGHTS = {
    "course_similarity": 31.635984,
    "gpa_similarity": 21.866631,
    "commitment_similarity": 24.991177,
    "age_similarity": 9.706654,
    "year_similarity": 11.799554
}


# ============================================================
# Calculate matching score
# ============================================================

def calculate_score(row, weights):

    score = 0

    for feature in FEATURES:
        score += (
            row[feature]
            * weights[feature]
        )

    return score


# ============================================================
# Convert score into prediction
# ============================================================

def predict_success(scores, threshold=50):

    return (
        scores >= threshold
    ).astype(int)


# ============================================================
# Evaluate one weighting system
# ============================================================

def evaluate_model(scores, actual):

    predictions = predict_success(
        scores
    )

    accuracy = accuracy_score(
        actual,
        predictions
    )

    precision = precision_score(
        actual,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        actual,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        actual,
        predictions,
        zero_division=0
    )

    auc = roc_auc_score(
        actual,
        scores
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": auc
    }


# ============================================================
# Main
# ============================================================

def main():

    df = pd.read_csv(
        DATASET_PATH
    )

    actual = df[
        "successful_collaboration"
    ]

    # --------------------------------------------------------
    # Calculate both scores
    # --------------------------------------------------------

    baseline_scores = df.apply(
        lambda row:
        calculate_score(
            row,
            BASELINE_WEIGHTS
        ),
        axis=1
    )

    ml_scores = df.apply(
        lambda row:
        calculate_score(
            row,
            ML_WEIGHTS
        ),
        axis=1
    )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    baseline_results = evaluate_model(
        baseline_scores,
        actual
    )

    ml_results = evaluate_model(
        ml_scores,
        actual
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print("=" * 70)
    print("BASELINE VS ML-INFORMED MATCHING")
    print("=" * 70)

    print()

    print("PROJECT 1 - BASELINE")
    print("-" * 70)

    for metric, value in baseline_results.items():
        print(
            f"{metric:<12}: {value:.4f}"
        )

    print()

    print("PROJECT 2 - ML-INFORMED")
    print("-" * 70)

    for metric, value in ml_results.items():
        print(
            f"{metric:<12}: {value:.4f}"
        )

    # --------------------------------------------------------
    # Improvement
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("IMPROVEMENT")
    print("=" * 70)

    for metric in baseline_results:

        improvement = (
            ml_results[metric]
            - baseline_results[metric]
        )

        print(
            f"{metric:<12}: "
            f"{improvement:+.4f}"
        )

    # --------------------------------------------------------
    # Score statistics
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SCORE STATISTICS")
    print("=" * 70)

    print()

    print("Baseline:")
    print(
        baseline_scores.describe()
        .to_string()
    )

    print()

    print("ML-informed:")
    print(
        ml_scores.describe()
        .to_string()
    )


if __name__ == "__main__":
    main()