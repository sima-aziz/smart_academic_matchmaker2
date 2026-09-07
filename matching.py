from models import Preferences
from flask import current_app

from ml.ml_matcher import predict_collaboration

# Must match the normalization used during ML training
ML_MAX_SHARED_COURSES = 5

def count_valid_shared_courses(p1, p2):
    if p1.program != p2.program:
        return 0

    if p1.semester != p2.semester:
        return 0

    p1_courses = {pc.course.code: pc for pc in p1.courses}
    p2_courses = {pc.course.code: pc for pc in p2.courses}

    common_courses = set(p1_courses) & set(p2_courses)

    if not common_courses:
        return 0

    valid_count = 0

    for code in common_courses:
        c1 = p1_courses[code]
        c2 = p2_courses[code]

        # cross-section allowed
        if c1.cross_section and c2.cross_section:
            valid_count += 1
            continue

        # otherwise must match section
        if c1.section == c2.section:
            valid_count += 1

    return valid_count


# Calculate the five normalized ML features

def calculate_ml_features(p1, p2):
    """
    Extract the same five compatibility criteria used by
    Project 1 and convert them into normalized similarity values.
    """
    # Shared courses
    shared_courses = count_valid_shared_courses(
        p1,
        p2
    )

    course_similarity = min(
        1,
        shared_courses / ML_MAX_SHARED_COURSES
    )


    # GPA
    gpa_diff = abs(
        p1.gpa - p2.gpa
    )

    # Convert GPA difference to similarity
    gpa_similarity = max(
        0,
        1 - (gpa_diff / 2)
    )


    # Commitment
    time_diff = abs(
        p1.commitment_level
        - p2.commitment_level
    )

    commitment_similarity = max(
        0,
        1 - (time_diff / 4)
    )


    # Age
    age_diff = abs(
        p1.age - p2.age
    )

    # A difference of 12 years or more gives zero similarity.
    age_similarity = max(
        0,
        1 - (age_diff / 12)
    )


    # Academic year
    year_diff = abs(
        p1.academic_year
        - p2.academic_year
    )

    # Academic year ranges from 1 to 5,
    year_similarity = max(
        0,
        1 - (year_diff / 4)
    )


    return {
        "course_similarity": round(
            course_similarity,
            4
        ),

        "gpa_similarity": round(
            gpa_similarity,
            4
        ),

        "commitment_similarity": round(
            commitment_similarity,
            4
        ),

        "age_similarity": round(
            age_similarity,
            4
        ),

        "year_similarity": round(
            year_similarity,
            4
        )
    }


# Project 1 - Dynamic Score Calculation
def compatibility_score(p1, p2, weights):
    score = 0

    # Count valid shared courses
    shared_courses = count_valid_shared_courses(
        p1,
        p2
    )

    if shared_courses == 0:
        return 0

    # normalize course score
    max_possible_courses = weights["max_courses"]

    course_score = min(
        weights["courses"],
        (
            shared_courses
            / max_possible_courses
        ) * weights["courses"]
    )

    score += course_score

    # GPA
    gpa_diff = abs(
        p1.gpa - p2.gpa
    )

    gpa_score = max(
        0,
        weights["gpa"] - (gpa_diff * 4)
    )

    score += gpa_score

    # Commitment
    time_diff = abs(
        p1.commitment_level
        - p2.commitment_level
    )

    commitment_score = max(
        0,
        weights["commitment"] - time_diff
    )

    score += commitment_score

    # Age
    age_diff = abs(
        p1.age - p2.age
    )

    age_score = max(
        0,
        weights["age"] - age_diff
    )

    score += age_score

    # Academic year
    year_diff = abs(
        p1.academic_year
        - p2.academic_year
    )

    year_score = max(
        0,
        weights["year"] - year_diff
    )

    score += year_score

    return round(
        score,
        2
    )


# Project 2 - ML Prediction
def ml_compatibility_probability(
    p1,
    p2
):
    """
    Calculate the ML probability for a pair
    using the same five criteria as Project 1.
    """

    features = calculate_ml_features(
        p1,
        p2
    )

    probability = predict_collaboration(
        features["course_similarity"],
        features["gpa_similarity"],
        features["commitment_similarity"],
        features["age_similarity"],
        features["year_similarity"]
    )


    return probability


def normalized_rule_score(
    p1,
    p2,
    weights
):
    rule_score = compatibility_score(
        p1,
        p2,
        weights
    )

    max_rule_score = (
        weights["courses"]
        + weights["gpa"]
        + weights["commitment"]
        + weights["age"]
        + weights["year"]
    )

    if max_rule_score <= 0:
        return 0.0

    normalized_score = (
        rule_score
        / max_rule_score
    )

    return max(
        0.0,
        min(
            1.0,
            normalized_score
        )
    )


def hybrid_compatibility_score(
    p1,
    p2,
    weights
):
    rule_score = normalized_rule_score(
        p1,
        p2,
        weights
    )

    ml_probability = (
        ml_compatibility_probability(
            p1,
            p2
        )
    )

    hybrid_score = (
        0.50 * rule_score
        + 0.50 * ml_probability
    )

    return round(
        hybrid_score,
        4
    )

# Find matches
def find_matches(
    current_pref,
    all_prefs,
    weights
):

    matches = []

    for pref in all_prefs:

        if pref.user_id == current_pref.user_id:
            continue

        score = compatibility_score(
            current_pref,
            pref,
            weights
        )

        if score == 0:
            continue

        matches.append(
            (
                pref,
                score
            )
        )

    matches.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return matches


def find_hybrid_matches(
    current_pref,
    all_prefs,
    weights
):

    matches = []

    for pref in all_prefs:

        if pref.user_id == current_pref.user_id:
            continue

        shared_courses = (
            count_valid_shared_courses(
                current_pref,
                pref
            )
        )

        if shared_courses == 0:
            continue

        hybrid_score = (
            hybrid_compatibility_score(
                current_pref,
                pref,
                weights
            )
        )

        matches.append(
            (
                pref,
                hybrid_score
            )
        )

    matches.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return matches