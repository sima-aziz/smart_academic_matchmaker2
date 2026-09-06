import os
import pickle

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from scipy.stats import spearmanr


# Configuration
BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATASET_PATH = os.path.join(
    BASE_DIR,
    "matchmaking_dataset.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "logistic_model.pkl"
)

SCALER_PATH = os.path.join(
    BASE_DIR,
    "feature_scaler.pkl"
)


FEATURES = [
    "course_similarity",
    "gpa_similarity",
    "commitment_similarity",
    "age_similarity",
    "year_similarity"
]

TARGET = "successful_collaboration"


# Project 1 default weights
WEIGHTS = {
    "courses": 40,
    "gpa": 35,
    "commitment": 10,
    "age": 5,
    "year": 10
}

PROJECT1_MAX_COURSES = 3


# Project 1 score reconstruction

def calculate_project1_score(row):
    """
    Reconstruct the original Project 1 compatibility score
    from the normalized features stored in the synthetic dataset.

    The inverse transformations correspond exactly to the
    formulas used when generating the dataset.
    """

    # Courses
    course_score = min(
        WEIGHTS["courses"],
        (
            row["shared_courses"]
            / PROJECT1_MAX_COURSES
        ) * WEIGHTS["courses"]
    )


    # GPA
    #
    # Dataset:
    # similarity = 1 - difference / 2
    # Therefore:
    # difference = (1 - similarity) * 2

    gpa_difference = (
        1 - row["gpa_similarity"]
    ) * 2

    gpa_score = max(
        0,
        WEIGHTS["gpa"]
        - (gpa_difference * 4)
    )


    # Commitment
    #
    # Dataset:
    # similarity = 1 - difference / 4
    commitment_difference = (
        1 - row["commitment_similarity"]
    ) * 4

    commitment_score = max(
        0,
        WEIGHTS["commitment"]
        - commitment_difference
    )


    # Age
    #
    # Dataset:
    # similarity = 1 - difference / 12
    age_difference = (
        1 - row["age_similarity"]
    ) * 12

    age_score = max(
        0,
        WEIGHTS["age"]
        - age_difference
    )


    
    # Academic year
    # Dataset:
    # similarity = 1 - difference / 4
    year_difference = (
        1 - row["year_similarity"]
    ) * 4

    year_score = max(
        0,
        WEIGHTS["year"]
        - year_difference
    )


    total_score = (
        course_score
        + gpa_score
        + commitment_score
        + age_score
        + year_score
    )

    return round(
        total_score,
        4
    )


# Create ranking records

def create_ranking_records(df):
    """
    Each pair is symmetric.

    A pair (student 1, student 2) is therefore represented
    from both students' perspectives so that ranking agreement
    can be measured.
    """

    records = []

    for _, row in df.iterrows():

        # Student 1 sees Student 2
        records.append({
            "student": int(row["student_1_id"]),
            "candidate": int(row["student_2_id"]),
            "project1_score": row["project1_score"],
            "project2_probability": row["project2_probability"]
        })

        # Student 2 sees Student 1
        records.append({
            "student": int(row["student_2_id"]),
            "candidate": int(row["student_1_id"]),
            "project1_score": row["project1_score"],
            "project2_probability": row["project2_probability"]
        })

    return pd.DataFrame(records)


# Top-K ranking comparison

def calculate_top_k_overlap(
    ranking_df,
    k
):
    overlaps = []

    grouped = ranking_df.groupby(
        "student"
    )

    for student_id, group in grouped:

        # Need at least k candidates
        if len(group) < k:
            continue

        project1_top = set(
            group
            .sort_values(
                "project1_score",
                ascending=False
            )
            .head(k)["candidate"]
        )

        project2_top = set(
            group
            .sort_values(
                "project2_probability",
                ascending=False
            )
            .head(k)["candidate"]
        )

        overlap = (
            len(
                project1_top
                & project2_top
            )
            / k
        )

        overlaps.append(
            overlap
        )

    if not overlaps:
        return None, 0

    return (
        np.mean(overlaps),
        len(overlaps)
    )


# Top-1 agreement
def calculate_top1_agreement(
    ranking_df
):
    agreements = []

    grouped = ranking_df.groupby(
        "student"
    )

    for student_id, group in grouped:

        if len(group) < 2:
            continue

        project1_best = (
            group
            .sort_values(
                "project1_score",
                ascending=False
            )
            .iloc[0]["candidate"]
        )

        project2_best = (
            group
            .sort_values(
                "project2_probability",
                ascending=False
            )
            .iloc[0]["candidate"]
        )

        agreements.append(
            project1_best
            == project2_best
        )

    if not agreements:
        return None, 0

    return (
        np.mean(agreements),
        len(agreements)
    )


# Main experiment

def main():

    print("=" * 70)
    print("PROJECT 1 vs PROJECT 2 COMPARISON")
    print("=" * 70)
    print()


    # Load dataset
    df = pd.read_csv(
        DATASET_PATH
    )

    print(
        f"Full dataset: {len(df)} pairs"
    )


    # Reproduce same train/test split

    train_indices, test_indices = train_test_split(
        df.index,
        test_size=0.20,
        random_state=42,
        stratify=df[TARGET]
    )

    test_df = (
        df
        .loc[test_indices]
        .copy()
    )

    print(
        f"Evaluation pairs: {len(test_df)}"
    )

    print()


    # --------------------------------------------------------
    # Project 1 scores
    # --------------------------------------------------------

    test_df["project1_score"] = (
        test_df.apply(
            calculate_project1_score,
            axis=1
        )
    )

    # Convert score to 0-1 range
    test_df[
        "project1_normalized"
    ] = (
        test_df["project1_score"]
        / 100
    )


    # --------------------------------------------------------
    # Load Project 2 model
    # --------------------------------------------------------

    with open(
        MODEL_PATH,
        "rb"
    ) as file:

        model = pickle.load(
            file
        )


    with open(
        SCALER_PATH,
        "rb"
    ) as file:

        scaler = pickle.load(
            file
        )


    # --------------------------------------------------------
    # Project 2 probabilities
    # --------------------------------------------------------

    X_test = test_df[
        FEATURES
    ]

    X_test_scaled = scaler.transform(
        X_test
    )

    test_df[
        "project2_probability"
    ] = model.predict_proba(
        X_test_scaled
    )[:, 1]


    # ========================================================
    # Basic score comparison
    # ========================================================

    print("=" * 70)
    print("SCORE DISTRIBUTION")
    print("=" * 70)

    print()

    print(
        "Project 1 average score: "
        f"{test_df['project1_score'].mean():.2f}%"
    )

    print(
        "Project 2 average probability: "
        f"{test_df['project2_probability'].mean() * 100:.2f}%"
    )

    print()

    print(
        "Project 1 score range: "
        f"{test_df['project1_score'].min():.2f}%"
        " - "
        f"{test_df['project1_score'].max():.2f}%"
    )

    print(
        "Project 2 probability range: "
        f"{test_df['project2_probability'].min() * 100:.2f}%"
        " - "
        f"{test_df['project2_probability'].max() * 100:.2f}%"
    )

    print()


    # ========================================================
    # Correlation
    # ========================================================

    correlation, p_value = spearmanr(
        test_df["project1_score"],
        test_df["project2_probability"]
    )

    print("=" * 70)
    print("PROJECT 1 / PROJECT 2 RANK CORRELATION")
    print("=" * 70)

    print()

    print(
        f"Spearman correlation: {correlation:.4f}"
    )

    print(
        f"P-value: {p_value:.6f}"
    )

    print()


    # ========================================================
    # Compare predictive discrimination
    # ========================================================

    y_test = test_df[
        TARGET
    ]

    project1_auc = roc_auc_score(
        y_test,
        test_df["project1_normalized"]
    )

    project2_auc = roc_auc_score(
        y_test,
        test_df["project2_probability"]
    )

    print("=" * 70)
    print("PREDICTIVE COMPARISON")
    print("=" * 70)

    print()

    print(
        f"Project 1 ROC-AUC: {project1_auc:.4f}"
    )

    print(
        f"Project 2 ROC-AUC: {project2_auc:.4f}"
    )

    latent_auc = roc_auc_score(
        y_test,
        test_df["simulated_probability"]
    )
    print(
        f"Latent simulation probability ROC-AUC: "
        f"{latent_auc:.4f}"
    )
    print()

    print(
        "ROC-AUC difference (P2 - P1): "
        f"{project2_auc - project1_auc:+.4f}"
    )

    print()


    # Ranking comparison

    ranking_df = create_ranking_records(
        test_df
    )

    top1, top1_users = (
        calculate_top1_agreement(
            ranking_df
        )
    )

    top3, top3_users = (
        calculate_top_k_overlap(
            ranking_df,
            3
        )
    )

    top5, top5_users = (
        calculate_top_k_overlap(
            ranking_df,
            5
        )
    )


    print("=" * 70)
    print("MATCH RANKING COMPARISON")
    print("=" * 70)

    print()

    if top1 is not None:
        print(
            "Top-1 agreement: "
            f"{top1 * 100:.2f}% "
            f"({top1_users} students)"
        )

    if top3 is not None:
        print(
            "Average Top-3 overlap: "
            f"{top3 * 100:.2f}% "
            f"({top3_users} students)"
        )

    if top5 is not None:
        print(
            "Average Top-5 overlap: "
            f"{top5 * 100:.2f}% "
            f"({top5_users} students)"
        )

    print()


    # Example comparison rows

    print("=" * 70)
    print("EXAMPLE PAIR COMPARISONS")
    print("=" * 70)

    print()

    examples = test_df[
        [
            "student_1_id",
            "student_2_id",
            TARGET,
            "project1_score",
            "project2_probability"
        ]
    ].copy()

    examples[
        "project2_probability"
    ] = (
        examples[
            "project2_probability"
        ] * 100
    )

    examples = examples.rename(
        columns={
            TARGET: "actual",
            "project1_score":
                "project1_percent",
            "project2_probability":
                "project2_percent"
        }
    )

    print(
        examples
        .head(15)
        .to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )

    print()


    print("=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()