import random
import pandas as pd
import os


# Reproducible results
random.seed(42)


NUM_STUDENTS = 1000
NUM_PAIRS = 10000

PROGRAM = "ITE"
SEMESTERS = ["S24", "F24", "S25"]  # last 3 semesters

ACADEMIC_YEARS = [1, 2, 3, 4, 5]
COMMITMENT_LEVELS = [1, 2, 3, 4, 5]

# Available courses in the synthetic university
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

# Project 1 algorithm settings
MAX_COURSES = 5

WEIGHTS = {
    "courses": 35,
    "gpa": 25,
    "commitment": 20,
    "age": 10,
    "year": 10
}


# 1. Generate synthetic students

def generate_students(num_students):
    students = []

    for student_id in range(1, num_students + 1):

        age = random.randint(18, 30)

        gpa = round(random.uniform(2.0, 4.0), 2)

        academic_year = random.choice(ACADEMIC_YEARS)

        commitment_level = random.choice(COMMITMENT_LEVELS)

        semester = random.choice(SEMESTERS)

        # Each student takes 3-6 courses
        number_of_courses = random.randint(3, 6)

        courses = random.sample(
            COURSES,
            number_of_courses
        )

        course_preferences = []

        for course in courses:

            cross_section = random.choice([True, False])

            section = None

            if not cross_section:
                section = f"C{random.randint(1, 10)}"

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
            "program": PROGRAM,
            "semester": semester,
            "courses": course_preferences
        })

    return students

def count_valid_shared_courses(student_1, student_2):

    if student_1["program"] != student_2["program"]:
        return 0

    if student_1["semester"] != student_2["semester"]:
        return 0

    s1_courses = {
        course["code"]: course
        for course in student_1["courses"]
    }

    s2_courses = {
        course["code"]: course
        for course in student_2["courses"]
    }

    common_courses = set(s1_courses) & set(s2_courses)

    valid_count = 0

    for code in common_courses:

        c1 = s1_courses[code]
        c2 = s2_courses[code]

        if c1["cross_section"] and c2["cross_section"]:
            valid_count += 1
            continue

        if c1["section"] == c2["section"]:
            valid_count += 1

    return valid_count


# 2. Calculate pair features

def calculate_pair_features(student_1, student_2):

    # Course compatibility

    shared_course_count = count_valid_shared_courses(
        student_1,
        student_2
    )

    course_similarity = min(
        shared_course_count / MAX_COURSES,
        1.0
    )

    # GPA compatibility

    gpa_difference = abs(
        student_1["gpa"] - student_2["gpa"]
    )

    gpa_similarity = max(
        0,
        1 - (gpa_difference / 2)
    )

    # Commitment compatibility

    commitment_difference = abs(
        student_1["commitment_level"]
        - student_2["commitment_level"]
    )

    commitment_similarity = max(
        0,
        1 - (commitment_difference / 4)
    )

    # Age compatibility

    age_difference = abs(
        student_1["age"] - student_2["age"]
    )

    age_similarity = max(
        0,
        1 - (age_difference / 12)
    )

    # Academic year compatibility

    year_difference = abs(
        student_1["academic_year"]
        - student_2["academic_year"]
    )

    year_similarity = max(
        0,
        1 - (year_difference / 4)
    )

    return {
        "course_similarity": round(course_similarity, 4),
        "gpa_similarity": round(gpa_similarity, 4),
        "commitment_similarity": round(commitment_similarity, 4),
        "age_similarity": round(age_similarity, 4),
        "year_similarity": round(year_similarity, 4),
        "shared_courses": shared_course_count
    }


# 3. Generate simulated collaboration outcome

def generate_outcome(features):
    """
    Simulates whether two students would successfully
    collaborate.

    IMPORTANT:
    This is simulated behavioral data, NOT real user feedback.
    """

    # Hidden relationship used to create the simulated environment
    probability = (
        0.40 * features["course_similarity"]
        + 0.25 * features["commitment_similarity"]
        + 0.15 * features["gpa_similarity"]
        + 0.10 * features["year_similarity"]
        + 0.10 * features["age_similarity"]
    )

    # Add small random variation
    probability += random.uniform(-0.10, 0.10)

    probability = max(0, min(1, probability))

    outcome = 1 if random.random() < probability else 0

    return outcome, probability


# 4. Generate pair dataset

def generate_pairs(students, num_pairs):

    dataset = []

    while len(dataset) < num_pairs:

        student_1, student_2 = random.sample(
            students,
            2
        )

        # Hard Project I eligibility rules
        if student_1["program"] != student_2["program"]:
            continue

        if student_1["semester"] != student_2["semester"]:
            continue

        features = calculate_pair_features(
            student_1,
            student_2
        )

        if features["shared_courses"] == 0:
            continue

        outcome, simulated_probability = generate_outcome(features)

        dataset.append({
            "student_1_id": student_1["student_id"],
            "student_2_id": student_2["student_id"],
            **features,
            "simulated_probability": simulated_probability,
            "successful_collaboration": outcome
        })

    return dataset


# ============================================================
# 5. Main
# ============================================================

def main():

    print("Generating synthetic students...")

    students = generate_students(NUM_STUDENTS)

    print(f"Generated {len(students)} students.")

    print("Generating student pairs...")

    dataset = generate_pairs(
        students,
        NUM_PAIRS
    )

    df = pd.DataFrame(dataset)

    output_file = os.path.join(
        "ml",
        "matchmaking_dataset.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    print()
    print("Dataset generated successfully!")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print()
    print(df.head())
    print()
    print("Outcome distribution:")
    print(df["successful_collaboration"].value_counts())


if __name__ == "__main__":
    main()