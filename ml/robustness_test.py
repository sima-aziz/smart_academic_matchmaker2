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

# Adaptation strengths
ALPHAS = [
    0.00,
    0.25,
    0.50,
    0.75,
    1.00
]

# Different train/test splits
SEEDS = [
    42,
    123,
    456,
    789,
    2026
]


# ============================================================
# Load dataset
# ============================================================

df = pd.read_csv(
    DATASET_PATH
)

X = df[FEATURES]
y = df[TARGET]


# ============================================================
# Calculate matching scores
# ============================================================

def calculate_scores(data, weights):

    return (
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


# ============================================================
# Evaluate weighting system
# ============================================================

def evaluate(scores, actual):

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
# Store all experiments
# ============================================================

all_results = []


# ============================================================
# Run experiments
# ============================================================

for seed in SEEDS:

    print("=" * 75)
    print(f"RANDOM SEED: {seed}")
    print("=" * 75)

    # --------------------------------------------------------
    # Train / test split
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=seed,
        stratify=y
    )

    # --------------------------------------------------------
    # Train ML model
    # --------------------------------------------------------

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(
        X_train
    )

    X_test_scaled = scaler.transform(
        X_test
    )

    model = LogisticRegression(
        random_state=seed
    )

    model.fit(
        X_train_scaled,
        y_train
    )

    # --------------------------------------------------------
    # Extract ML weights
    # --------------------------------------------------------

    coefficients = abs(
        model.coef_[0]
    )

    total_importance = sum(
        coefficients
    )

    ml_weights = {}

    for feature, coefficient in zip(
        FEATURES,
        coefficients
    ):

        ml_weights[feature] = (
            coefficient
            / total_importance
            * 100
        )

    print()
    print("ML-derived weights:")

    for feature in FEATURES:

        print(
            f"{feature:<25}"
            f"{ml_weights[feature]:>8.2f}"
        )

    print()

    # --------------------------------------------------------
    # Test every alpha
    # --------------------------------------------------------

    for alpha in ALPHAS:

        hybrid_weights = {}

        for feature in FEATURES:

            hybrid_weights[feature] = (
                (1 - alpha)
                * BASELINE_WEIGHTS[feature]

                + alpha
                * ml_weights[feature]
            )

        # Normalize
        total_weight = sum(
            hybrid_weights.values()
        )

        for feature in FEATURES:

            hybrid_weights[feature] = (
                hybrid_weights[feature]
                / total_weight
                * 100
            )

        # ----------------------------------------------------
        # Evaluate on unseen test data
        # ----------------------------------------------------

        scores = calculate_scores(
            X_test,
            hybrid_weights
        )

        metrics = evaluate(
            scores,
            y_test
        )

        all_results.append({
            "seed": seed,
            "alpha": alpha,
            **metrics
        })

        print(
            f"alpha={alpha:.2f} | "
            f"AUC={metrics['roc_auc']:.4f} | "
            f"F1={metrics['f1']:.4f}"
        )

    print()


# ============================================================
# Convert results to DataFrame
# ============================================================

results_df = pd.DataFrame(
    all_results
)


# ============================================================
# Calculate average performance
# ============================================================

summary = (
    results_df
    .groupby("alpha")
    .agg({
        "accuracy": ["mean", "std"],
        "precision": ["mean", "std"],
        "recall": ["mean", "std"],
        "f1": ["mean", "std"],
        "roc_auc": ["mean", "std"]
    })
)


# ============================================================
# Display summary
# ============================================================

print("=" * 75)
print("ROBUSTNESS SUMMARY")
print("=" * 75)

print(
    summary.to_string(
        float_format=lambda x: f"{x:.4f}"
    )
)

print()


# ============================================================
# Find best alpha based on mean ROC-AUC
# ============================================================

mean_auc = (
    results_df
    .groupby("alpha")["roc_auc"]
    .mean()
)

best_alpha = mean_auc.idxmax()

best_auc = mean_auc.max()


print("=" * 75)
print("BEST ADAPTATION STRENGTH")
print("=" * 75)

print(
    f"Best alpha: {best_alpha:.2f}"
)

print(
    f"Mean ROC-AUC: {best_auc:.4f}"
)


# ============================================================
# Compare baseline vs best
# ============================================================

baseline_auc = mean_auc.loc[0.00]

improvement = (
    best_auc
    - baseline_auc
)

print()
print(
    f"Baseline mean ROC-AUC: "
    f"{baseline_auc:.4f}"
)

print(
    f"Best mean ROC-AUC:      "
    f"{best_auc:.4f}"
)

print(
    f"Improvement:            "
    f"{improvement:+.4f}"
)

print()


# ============================================================
# Save results
# ============================================================

results_df.to_csv(
    "ml/robustness_results.csv",
    index=False
)

print(
    "Detailed results saved to:"
)

print(
    "ml/robustness_results.csv"
)