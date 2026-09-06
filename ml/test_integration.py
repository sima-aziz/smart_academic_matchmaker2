from ml_matcher import predict_collaboration

print("=" * 70)
print("PROJECT 2 ML INTEGRATION TEST")
print("=" * 70)


# High compatibility example
features_high = {
    "course_similarity": 0.8,
    "gpa_similarity": 0.9,
    "commitment_similarity": 0.8,
    "age_similarity": 0.9,
    "year_similarity": 0.8
}

probability_high = predict_collaboration(
    features_high["course_similarity"],
    features_high["gpa_similarity"],
    features_high["commitment_similarity"],
    features_high["age_similarity"],
    features_high["year_similarity"]
)


# Low compatibility example
features_low = {
    "course_similarity": 0.2,
    "gpa_similarity": 0.2,
    "commitment_similarity": 0.1,
    "age_similarity": 0.3,
    "year_similarity": 0.2
}

probability_low = predict_collaboration(
    features_low["course_similarity"],
    features_low["gpa_similarity"],
    features_low["commitment_similarity"],
    features_low["age_similarity"],
    features_low["year_similarity"]
)


print()
print(
    f"High compatibility probability: "
    f"{probability_high:.4f}"
)

print(
    f"Low compatibility probability:  "
    f"{probability_low:.4f}"
)

print()

if probability_high > probability_low:
    print("PASS: ML model behaves as expected.")
else:
    print("WARNING: Unexpected ML behavior.")

print("=" * 70)