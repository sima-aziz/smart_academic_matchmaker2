"""Matching logic for Smart Academic Matchmaker.

Eligibility is enforced first through hard academic constraints.  Eligible
pairs are then scored in two independent ways:

1. Project 1 rule-based compatibility score.
2. Project 2 unsupervised academic-profile similarity learned from real data.

The deployed score is the agreed 50/50 hybrid of the normalized rule score and
the unsupervised ML similarity.
"""

from ml.ml_matcher import profile_similarity


def count_valid_shared_courses(p1, p2):
    """Count shared courses that satisfy the current section rules.

    Hard constraints kept unchanged from the existing system:
    * same program
    * same semester
    * at least one shared course
    * if both users allow cross-section collaboration, the course is valid;
      otherwise their section must match
    """

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

        # Cross-section collaboration is valid only when both users allow it.
        if c1.cross_section and c2.cross_section:
            valid_count += 1
            continue

        # Otherwise both users must be in the same section.
        if c1.section == c2.section:
            valid_count += 1

    return valid_count


# ---------------------------------------------------------------------------
# Project 1 rule-based score
# ---------------------------------------------------------------------------

def compatibility_score(p1, p2, weights):
    """Return the original rule-based score using the configured weights."""

    score = 0.0

    shared_courses = count_valid_shared_courses(p1, p2)

    if shared_courses == 0:
        return 0.0

    max_possible_courses = weights["max_courses"]

    course_score = min(
        weights["courses"],
        (shared_courses / max_possible_courses) * weights["courses"],
    )
    score += course_score

    # GPA similarity: smaller difference keeps more of the GPA weight.
    gpa_diff = abs(p1.gpa - p2.gpa)
    gpa_score = max(
        0.0,
        weights["gpa"] - (gpa_diff * 4),
    )
    score += gpa_score

    # Commitment similarity.
    commitment_diff = abs(
        p1.commitment_level - p2.commitment_level
    )
    commitment_score = max(
        0.0,
        weights["commitment"] - commitment_diff,
    )
    score += commitment_score

    # Age similarity.
    age_diff = abs(p1.age - p2.age)
    age_score = max(
        0.0,
        weights["age"] - age_diff,
    )
    score += age_score

    # Academic-year similarity.
    year_diff = abs(
        p1.academic_year - p2.academic_year
    )
    year_score = max(
        0.0,
        weights["year"] - year_diff,
    )
    score += year_score

    return round(score, 2)


def normalized_rule_score(p1, p2, weights):
    """Normalize the Project 1 score to [0, 1] for hybrid combination."""

    rule_score = compatibility_score(p1, p2, weights)

    max_rule_score = (
        weights["courses"]
        + weights["gpa"]
        + weights["commitment"]
        + weights["age"]
        + weights["year"]
    )

    if max_rule_score <= 0:
        return 0.0

    normalized = rule_score / max_rule_score
    return max(0.0, min(1.0, normalized))


# ---------------------------------------------------------------------------
# Project 2 unsupervised ML similarity
# ---------------------------------------------------------------------------

def ml_profile_similarity(p1, p2):
    """Return learned academic-profile similarity in [0, 1].

    The unsupervised model uses only fields that have direct equivalents in
    both the real training data and the deployed application:

        age, GPA, academic year

    This value is NOT a probability that collaboration will succeed.
    """

    return profile_similarity(
        p1.age,
        p1.gpa,
        p1.academic_year,
        p2.age,
        p2.gpa,
        p2.academic_year,
    )


def hybrid_compatibility_score(p1, p2, weights):
    """Return the agreed 50% rule-based + 50% unsupervised-ML score."""

    # Keep the hard academic eligibility constraints in front of both scores.
    if count_valid_shared_courses(p1, p2) == 0:
        return 0.0

    rule_score = normalized_rule_score(p1, p2, weights)
    ml_similarity = ml_profile_similarity(p1, p2)

    hybrid_score = (
        0.50 * rule_score
        + 0.50 * ml_similarity
    )

    return round(hybrid_score, 4)


# ---------------------------------------------------------------------------
# Ranking helpers
# ---------------------------------------------------------------------------

def find_matches(current_pref, all_prefs, weights):
    """Return Project 1 rule-based matches (kept for baseline/debugging)."""

    matches = []

    for pref in all_prefs:
        if pref.user_id == current_pref.user_id:
            continue

        score = compatibility_score(
            current_pref,
            pref,
            weights,
        )

        if score == 0:
            continue

        matches.append((pref, score))

    matches.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return matches


def find_hybrid_matches(current_pref, all_prefs, weights):
    """Return eligible candidates ranked by the final 50/50 hybrid score."""

    matches = []

    for pref in all_prefs:
        if pref.user_id == current_pref.user_id:
            continue

        # Apply hard constraints before either scoring component.
        if count_valid_shared_courses(current_pref, pref) == 0:
            continue

        hybrid_score = hybrid_compatibility_score(
            current_pref,
            pref,
            weights,
        )

        matches.append((pref, hybrid_score))

    matches.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return matches
