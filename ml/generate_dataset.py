import random
import os
from itertools import combinations

import pandas as pd


# ============================================================
# Configuration
# ============================================================

# Reproducible results
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

NUM_STUDENTS = 1000

PROGRAMS = [
    "ITE",
    "BAIT",
    "ISE"
]

SEMESTERS = [
    "S24",
    "F24",
    "S25"
]

ACADEMIC_YEARS = [
    1,
    2,
    3,
    4,
    5
]

COMMITMENT_LEVELS = [
    1,
    2,
    3,
    4,
    5
]

# Synthetic course catalogue
COURSES = [
    "CS101",
    "CS102",
    "CS201",
    "CS202",
    "CS301",
    "CS302",
    "CS401",
    "CS402",
    "ML301",
    "ML302",
    "DB201",
    "WEB201",
]

MAX_COURSES = 5


# ============================================================
# 1. Generate synthetic students
# ============================================================

def generate_students(num_students):

    students = []

    for student_id in range(
        1,
        num_students + 1
    ):

        age = random.randint(
            18,
            30
        )

        gpa = round(
            random.uniform(
                2.0,
                4.0
            ),
            2
        )

        academic_year = random.choice(
            ACADEMIC_YEARS
        )

        commitment_level = random.choice(
            COMMITMENT_LEVELS
        )

        program = random.choice(
            PROGRAMS
        )

        semester = random.choice(
            SEMESTERS
        )

        # Each student takes 3–6 courses
        number_of_courses = random.randint(
            3,
            6
        )

        courses = random.sample(
            COURSES,
            number_of_courses
        )

        course_preferences = []

        for course in courses:

            cross_section = random.choice(
                [True, False]
            )

            section = None

            if not cross_section:

                section = (
                    f"C{random.randint(1, 10)}"
                )

            course_preferences.append({
                "code": course,
                "cross_section": cross_section,
                "section": section
            })

        students.append({
            "student_id": student_id,
            "age": age,
            "gpa": gpa,
            "academic_year": academic_year,
            "commitment_level": commitment_level,
            "program": program,
            "semester": semester,
            "courses": course_preferences
        })

    return students


# ============================================================
# 2. Project 1 hard eligibility rules
# ============================================================

def count_valid_shared_courses(
    student_1,
    student_2
):

    # Same academic program
    if (
        student_1["program"]
        != student_2["program"]
    ):
        return 0

    # Same semester
    if (
        student_1["semester"]
        != student_2["semester"]
    ):
        return 0

    s1_courses = {
        course["code"]: course
        for course
        in student_1["courses"]
    }

    s2_courses = {
        course["code"]: course
        for course
        in student_2["courses"]
    }

    common_courses = (
        set(s1_courses)
        & set(s2_courses)
    )

    if not common_courses:
        return 0

    valid_count = 0

    for code in common_courses:

        c1 = s1_courses[code]
        c2 = s2_courses[code]

        # Cross-section collaboration is allowed
        # only when both students allow it
        if (
            c1["cross_section"]
            and c2["cross_section"]
        ):
            valid_count += 1
            continue

        # Otherwise both students must be
        # in the same section
        if (
            c1["section"]
            == c2["section"]
        ):
            valid_count += 1

    return valid_count


# ============================================================
# 3. Calculate pair features
# ============================================================

def calculate_pair_features(
    student_1,
    student_2
):

    # --------------------------------------------------------
    # Course similarity
    # --------------------------------------------------------

    shared_course_count = (
        count_valid_shared_courses(
            student_1,
            student_2
        )
    )

    course_similarity = min(
        shared_course_count
        / MAX_COURSES,
        1.0
    )

    # --------------------------------------------------------
    # GPA similarity
    # --------------------------------------------------------

    gpa_difference = abs(
        student_1["gpa"]
        - student_2["gpa"]
    )

    gpa_similarity = max(
        0,
        1 - (
            gpa_difference / 2
        )
    )

    # --------------------------------------------------------
    # Commitment similarity
    # --------------------------------------------------------

    commitment_difference = abs(
        student_1["commitment_level"]
        - student_2["commitment_level"]
    )

    commitment_similarity = max(
        0,
        1 - (
            commitment_difference / 4
        )
    )

    # --------------------------------------------------------
    # Age similarity
    # --------------------------------------------------------

    age_difference = abs(
        student_1["age"]
        - student_2["age"]
    )

    age_similarity = max(
        0,
        1 - (
            age_difference / 12
        )
    )

    # --------------------------------------------------------
    # Academic-year similarity
    # --------------------------------------------------------

    year_difference = abs(
        student_1["academic_year"]
        - student_2["academic_year"]
    )

    year_similarity = max(
        0,
        1 - (
            year_difference / 4
        )
    )

    return {
        "course_similarity":
            round(
                course_similarity,
                4
            ),

        "gpa_similarity":
            round(
                gpa_similarity,
                4
            ),

        "commitment_similarity":
            round(
                commitment_similarity,
                4
            ),

        "age_similarity":
            round(
                age_similarity,
                4
            ),

        "year_similarity":
            round(
                year_similarity,
                4
            ),

        "shared_courses":
            shared_course_count
    }


# ============================================================
# 4. Generate simulated collaboration outcome
# ============================================================

def generate_outcome(features):
    """
    Simulates whether two eligible students would
    successfully collaborate.

    This is synthetic behavioral data,
    not real user feedback.
    """

    probability = (
        0.40
        * features[
            "course_similarity"
        ]

        + 0.25
        * features[
            "commitment_similarity"
        ]

        + 0.15
        * features[
            "gpa_similarity"
        ]

        + 0.10
        * features[
            "year_similarity"
        ]

        + 0.10
        * features[
            "age_similarity"
        ]
    )

    # Controlled random variation
    probability += random.uniform(
        -0.10,
        0.10
    )

    probability = max(
        0,
        min(
            1,
            probability
        )
    )

    outcome = (
        1
        if random.random()
        < probability
        else 0
    )

    return (
        outcome,
        probability
    )


# ============================================================
# 5. Generate all ordinary candidate pairs,
#    then filter them using the hard rules
# ============================================================

def generate_pairs(students):

    dataset = []

    statistics = {
        "total_candidate_pairs": 0,
        "program_mismatch": 0,
        "semester_mismatch": 0,
        "no_valid_shared_course": 0,
        "valid_pairs": 0
    }

    # combinations() creates each pair once only:
    # (1, 2) is included, but (2, 1) is not repeated.
    for student_1, student_2 in combinations(
        students,
        2
    ):

        statistics[
            "total_candidate_pairs"
        ] += 1

        # ----------------------------------------------------
        # Hard rule 1: same program
        # ----------------------------------------------------

        if (
            student_1["program"]
            != student_2["program"]
        ):

            statistics[
                "program_mismatch"
            ] += 1

            continue

        # ----------------------------------------------------
        # Hard rule 2: same semester
        # ----------------------------------------------------

        if (
            student_1["semester"]
            != student_2["semester"]
        ):

            statistics[
                "semester_mismatch"
            ] += 1

            continue

        # ----------------------------------------------------
        # Calculate pair features
        # ----------------------------------------------------

        features = calculate_pair_features(
            student_1,
            student_2
        )

        # ----------------------------------------------------
        # Hard rule 3:
        # at least one valid shared course
        # ----------------------------------------------------

        if (
            features[
                "shared_courses"
            ]
            == 0
        ):

            statistics[
                "no_valid_shared_course"
            ] += 1

            continue

        # ----------------------------------------------------
        # Pair is academically eligible
        # ----------------------------------------------------

        (
            outcome,
            simulated_probability
        ) = generate_outcome(
            features
        )

        dataset.append({
            "student_1_id":
                student_1["student_id"],

            "student_2_id":
                student_2["student_id"],

            **features,

            "simulated_probability":
                simulated_probability,

            "successful_collaboration":
                outcome
        })

        statistics[
            "valid_pairs"
        ] += 1

    return (
        dataset,
        statistics
    )


# ============================================================
# 6. Main
# ============================================================

def main():

    print("=" * 70)
    print("SYNTHETIC DATASET GENERATOR")
    print("=" * 70)
    print()

    print(
        "Generating synthetic students..."
    )

    students = generate_students(
        NUM_STUDENTS
    )

    print(
        f"Generated students: "
        f"{len(students)}"
    )

    print()

    print(
        "Generating all unique candidate pairs "
        "and applying eligibility rules..."
    )

    (
        dataset,
        statistics
    ) = generate_pairs(
        students
    )

    df = pd.DataFrame(
        dataset
    )

    output_file = os.path.join(
        "ml",
        "matchmaking_dataset.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    # ========================================================
    # Dataset statistics
    # ========================================================

    print()
    print("=" * 70)
    print("ELIGIBILITY FILTERING")
    print("=" * 70)

    print(
        f"Total candidate pairs:       "
        f"{statistics['total_candidate_pairs']}"
    )

    print(
        f"Rejected - program mismatch: "
        f"{statistics['program_mismatch']}"
    )

    print(
        f"Rejected - semester mismatch:"
        f" {statistics['semester_mismatch']}"
    )

    print(
        f"Rejected - no valid course:  "
        f"{statistics['no_valid_shared_course']}"
    )

    print(
        f"Valid eligible pairs:        "
        f"{statistics['valid_pairs']}"
    )

    eligibility_rate = (
        statistics["valid_pairs"]
        / statistics[
            "total_candidate_pairs"
        ]
        * 100
    )

    print(
        f"Eligibility rate:            "
        f"{eligibility_rate:.2f}%"
    )

    # ========================================================
    # Output information
    # ========================================================

    print()
    print("=" * 70)
    print("FINAL DATASET")
    print("=" * 70)

    print(
        f"Rows:    {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print()

    print("First rows:")
    print(
        df.head(10).to_string(
            index=False
        )
    )

    # ========================================================
    # Outcome distribution
    # ========================================================

    print()
    print("=" * 70)
    print("OUTCOME DISTRIBUTION")
    print("=" * 70)

    print(
        df[
            "successful_collaboration"
        ].value_counts()
    )

    print()

    print("Outcome percentages:")

    print(
        df[
            "successful_collaboration"
        ]
        .value_counts(
            normalize=True
        )
        .mul(100)
        .round(2)
    )

    # ========================================================
    # Shared-course distribution
    # ========================================================

    print()
    print("=" * 70)
    print("VALID SHARED COURSE DISTRIBUTION")
    print("=" * 70)

    print(
        df[
            "shared_courses"
        ]
        .value_counts()
        .sort_index()
    )

    print()

    print(
        "Dataset saved to:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()