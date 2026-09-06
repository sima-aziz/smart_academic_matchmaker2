from ml_matcher import predict_collaboration


print("=" * 70)
print("ML MATCHER TEST")
print("=" * 70)


# Example 1
probability_1 = predict_collaboration(
    course_similarity=0.8,
    gpa_similarity=0.9,
    commitment_similarity=0.8,
    age_similarity=0.9,
    year_similarity=0.8
)

print()
print("Example 1")
print(
    f"Successful collaboration probability: "
    f"{probability_1:.4f}"
)


# Example 2
probability_2 = predict_collaboration(
    course_similarity=0.2,
    gpa_similarity=0.2,
    commitment_similarity=0.1,
    age_similarity=0.3,
    year_similarity=0.2
)

print()
print("Example 2")
print(
    f"Successful collaboration probability: "
    f"{probability_2:.4f}"
)


print()
print("=" * 70)
print("TEST COMPLETED")
print("=" * 70)