import random
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
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

RANDOM_SEED = 42


# ============================================================
# Hidden environments
# ============================================================

SCENARIOS = {

    "Courses Dominant": {
        "course_similarity": 0.50,
        "gpa_similarity": 0.15,
        "commitment_similarity": 0.20,
        "age_similarity": 0.05,
        "year_similarity": 0.10
    },

    "Commitment Dominant": {
        "course_similarity": 0.15,
        "gpa_similarity": 0.15,
        "commitment_similarity": 0.50,
        "age_similarity": 0.05,
        "year_similarity": 0.15
    },

    "GPA Dominant": {
        "course_similarity": 0.15,
        "gpa_similarity": 0.50,
        "commitment_similarity": 0.20,
        "age_similarity": 0.05,
        "year_similarity": 0.10
    },

    "Equal Influence": {
        "course_similarity": 0.20,
        "gpa_similarity": 0.20,
        "commitment_similarity": 0.20,
        "age_similarity": 0.20,
        "year_similarity": 0.20
    }
}


# ============================================================
# Generate simulated outcomes
# ============================================================

def generate_outcomes(X, weights):

    random.seed(RANDOM_SEED)

    outcomes = []

    for _, row in X.iterrows():

        probability = (
            weights["course_similarity"]
            * row["course_similarity"]

            + weights["gpa_similarity"]
            * row["gpa_similarity"]

            + weights["commitment_similarity"]
            * row["commitment_similarity"]

            + weights["age_similarity"]
            * row["age_similarity"]

            + weights["year_similarity"]
            * row["year_similarity"]
        )

        # Add controlled noise
        probability += random.uniform(-0.10, 0.10)

        probability = max(
            0,
            min(1, probability)
        )

        outcome = (
            1
            if random.random() < probability
            else 0
        )

        outcomes.append(outcome)

    return pd.Series(
        outcomes,
        index=X.index
    )


# ============================================================
# Train Logistic Regression
# ============================================================

def train_logistic_regression(X_train, X_test, y_train, y_test):

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(
        random_state=RANDOM_SEED
    )

    model.fit(
        X_train_scaled,
        y_train
    )

    predictions = model.predict(
        X_test_scaled
    )

    probabilities = model.predict_proba(
        X_test_scaled
    )[:, 1]

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    f1 = f1_score(
        y_test,
        predictions
    )

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    return model, accuracy, f1, auc


# ============================================================
# Run one scenario
# ============================================================

def run_scenario(df, scenario_name, weights):

    X = df[FEATURES]

    y = generate_outcomes(
        X,
        weights
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=y
    )

    model, accuracy, f1, auc = train_logistic_regression(
        X_train,
        X_test,
        y_train,
        y_test
    )

    coefficients = pd.DataFrame({
        "feature": FEATURES,
        "coefficient": model.coef_[0]
    })

    coefficients["absolute_coefficient"] = (
        coefficients["coefficient"].abs()
    )

    coefficients = coefficients.sort_values(
        "absolute_coefficient",
        ascending=False
    )

    return {
        "scenario": scenario_name,
        "accuracy": accuracy,
        "f1": f1,
        "roc_auc": auc,
        "coefficients": coefficients
    }


# ============================================================
# Main experiment
# ============================================================

def main():

    df = pd.read_csv(
        DATASET_PATH
    )

    print("=" * 70)
    print("CONTROLLED ML EXPERIMENTS")
    print("=" * 70)
    print()

    results = []

    for scenario_name, weights in SCENARIOS.items():

        print("=" * 70)
        print(scenario_name)
        print("=" * 70)

        print("Hidden weights:")

        for feature, weight in weights.items():
            print(
                f"  {feature}: {weight:.2f}"
            )

        print()

        result = run_scenario(
            df,
            scenario_name,
            weights
        )

        results.append(result)

        print(
            f"Accuracy: {result['accuracy']:.4f}"
        )

        print(
            f"F1-score: {result['f1']:.4f}"
        )

        print(
            f"ROC-AUC: {result['roc_auc']:.4f}"
        )

        print()
        print("Learned feature importance:")
        print(
            result["coefficients"]
            .to_string(index=False)
        )

        print()


if __name__ == "__main__":
    main()