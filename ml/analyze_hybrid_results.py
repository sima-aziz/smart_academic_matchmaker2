import pandas as pd
from scipy.stats import spearmanr

from app import (
    app,
    get_matching_weights,
    is_blocked_between,
)
from models import User, Preferences, db

from matching import (
    count_valid_shared_courses,
    compatibility_score,
    normalized_rule_score,
    ml_profile_similarity,
    hybrid_compatibility_score,
)

from ml.ml_matcher import explain_profile


# Configuration

TARGET_EMAIL = "sima2@test.com"



# Helper

def full_name(pref):
    return (
        f"{pref.user.first_name} "
        f"{pref.user.last_name}"
    )


# Current-user analysis

def analyze_current_user():

    user = User.query.filter(
        db.func.lower(User.email)
        == TARGET_EMAIL.lower()
    ).first()

    if not user:
        print(
            f"ERROR: User {TARGET_EMAIL} "
            "was not found."
        )
        return None

    if not user.preferences:
        print(
            "ERROR: Target user has no preferences."
        )
        return None

    current_pref = user.preferences
    weights = get_matching_weights()

    print("=" * 90)
    print("CURRENT USER HYBRID MATCH ANALYSIS")
    print("=" * 90)

    print(
        f"User: {user.first_name} "
        f"{user.last_name}"
    )

    print(f"Email: {user.email}")
    print(f"Age: {current_pref.age}")
    print(f"GPA: {current_pref.gpa}")
    print(
        f"Academic year: "
        f"{current_pref.academic_year}"
    )

    current_profile = explain_profile(
        current_pref.age,
        current_pref.gpa,
        current_pref.academic_year,
    )

    print("\nGMM profile:")
    print(
        f"Cluster: "
        f"{current_profile['cluster']}"
    )

    print(
        "Membership probabilities:",
        [
            round(value, 4)
            for value
            in current_profile[
                "membership_probabilities"
            ]
        ],
    )

    print(
        "Membership confidence:",
        round(
            current_profile[
                "membership_confidence"
            ],
            4,
        ),
    )

    print("\nRule weights:")
    print(weights)

    rows = []

    for pref in Preferences.query.all():

        if pref.user_id == current_pref.user_id:
            continue

        valid_shared = (
            count_valid_shared_courses(
                current_pref,
                pref,
            )
        )

        # Hard constraints failed
        if valid_shared == 0:
            continue

        # Match page also excludes blocks
        if is_blocked_between(
            user.id,
            pref.user_id,
        ):
            continue

        rule_raw = compatibility_score(
            current_pref,
            pref,
            weights,
        )

        rule_normalized = (
            normalized_rule_score(
                current_pref,
                pref,
                weights,
            )
        )

        ml_similarity = (
            ml_profile_similarity(
                current_pref,
                pref,
            )
        )

        hybrid = (
            hybrid_compatibility_score(
                current_pref,
                pref,
                weights,
            )
        )

        profile = explain_profile(
            pref.age,
            pref.gpa,
            pref.academic_year,
        )

        rows.append({
            "user_id":
                pref.user_id,

            "name":
                full_name(pref),

            "age":
                pref.age,

            "gpa":
                pref.gpa,

            "academic_year":
                pref.academic_year,

            "commitment":
                pref.commitment_level,

            "valid_shared_courses":
                valid_shared,

            "rule_raw":
                rule_raw,

            "rule_normalized":
                rule_normalized,

            "rule_percent":
                rule_normalized * 100,

            "ml_similarity":
                ml_similarity,

            "ml_percent":
                ml_similarity * 100,

            "hybrid":
                hybrid,

            "hybrid_percent":
                hybrid * 100,

            "gmm_cluster":
                profile["cluster"],

            "gmm_confidence":
                profile[
                    "membership_confidence"
                ],
        })

    if not rows:
        print(
            "\nNo eligible matches found."
        )
        return None

    df = pd.DataFrame(rows)

    # --------------------------------------------------------
    # Ranking comparison
    # --------------------------------------------------------

    df["rule_rank"] = (
        df["rule_normalized"]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )

    df["hybrid_rank"] = (
        df["hybrid"]
        .rank(
            ascending=False,
            method="min",
        )
        .astype(int)
    )

    # Positive value means the candidate moved UP
    # after introducing ML.
    df["rank_change"] = (
        df["rule_rank"]
        - df["hybrid_rank"]
    )

    df = df.sort_values(
        by="hybrid",
        ascending=False,
    )

    print("\n")
    print("=" * 90)
    print("FINAL BREAKDOWN")
    print("=" * 90)

    display_columns = [
        "name",
        "valid_shared_courses",
        "rule_percent",
        "ml_percent",
        "hybrid_percent",
        "rule_rank",
        "hybrid_rank",
        "rank_change",
        "gmm_cluster",
        "gmm_confidence",
    ]

    display_df = df[
        display_columns
    ].copy()

    for column in [
        "rule_percent",
        "ml_percent",
        "hybrid_percent",
        "gmm_confidence",
    ]:
        display_df[column] = (
            display_df[column]
            .round(2)
        )

    print(
        display_df.to_string(
            index=False
        )
    )

    output_path = (
        "ml/current_user_hybrid_breakdown.csv"
    )

    df.to_csv(
        output_path,
        index=False,
    )

    print(
        f"\nSaved detailed results to: "
        f"{output_path}"
    )

    return df


# Global pair analysis

def analyze_all_pairs():

    preferences = Preferences.query.all()
    weights = get_matching_weights()

    pair_rows = []

    for i in range(len(preferences)):

        p1 = preferences[i]

        for j in range(
            i + 1,
            len(preferences),
        ):

            p2 = preferences[j]

            shared = (
                count_valid_shared_courses(
                    p1,
                    p2,
                )
            )

            if shared == 0:
                continue

            if is_blocked_between(
                p1.user_id,
                p2.user_id,
            ):
                continue

            rule = normalized_rule_score(
                p1,
                p2,
                weights,
            )

            ml = ml_profile_similarity(
                p1,
                p2,
            )

            hybrid = (
                hybrid_compatibility_score(
                    p1,
                    p2,
                    weights,
                )
            )

            pair_rows.append({
                "user1":
                    full_name(p1),

                "user2":
                    full_name(p2),

                "valid_shared_courses":
                    shared,

                "rule":
                    rule,

                "ml":
                    ml,

                "hybrid":
                    hybrid,
            })

    if not pair_rows:
        print(
            "\nNo eligible pairs found "
            "for global analysis."
        )
        return

    pairs = pd.DataFrame(pair_rows)

    print("\n")
    print("=" * 90)
    print("GLOBAL HYBRID BEHAVIOUR ANALYSIS")
    print("=" * 90)

    print(
        f"Eligible unique pairs: "
        f"{len(pairs)}"
    )

    print(
        f"Average Rule score: "
        f"{pairs['rule'].mean() * 100:.2f}%"
    )

    print(
        f"Average ML similarity: "
        f"{pairs['ml'].mean() * 100:.2f}%"
    )

    print(
        f"Average Hybrid score: "
        f"{pairs['hybrid'].mean() * 100:.2f}%"
    )

    print(
        "\nScore ranges:"
    )

    print(
        "Rule:   "
        f"{pairs['rule'].min() * 100:.2f}% "
        "to "
        f"{pairs['rule'].max() * 100:.2f}%"
    )

    print(
        "ML:     "
        f"{pairs['ml'].min() * 100:.2f}% "
        "to "
        f"{pairs['ml'].max() * 100:.2f}%"
    )

    print(
        "Hybrid: "
        f"{pairs['hybrid'].min() * 100:.2f}% "
        "to "
        f"{pairs['hybrid'].max() * 100:.2f}%"
    )

    correlation, p_value = spearmanr(
        pairs["rule"],
        pairs["hybrid"],
    )

    print(
        "\nRule vs Hybrid "
        "Spearman correlation:"
    )

    print(
        f"rho = {correlation:.4f}"
    )

    print(
        f"p-value = {p_value:.8f}"
    )

    pairs.to_csv(
        "ml/hybrid_pairwise_analysis.csv",
        index=False,
    )

    print(
        "\nSaved pair analysis to: "
        "ml/hybrid_pairwise_analysis.csv"
    )


# Run

if __name__ == "__main__":

    with app.app_context():

        analyze_current_user()
        analyze_all_pairs()