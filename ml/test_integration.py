"""Functional sanity tests for the unsupervised ML matcher."""

try:
    from ml.ml_matcher import explain_profile, profile_similarity
except ModuleNotFoundError:
    from ml_matcher import explain_profile, profile_similarity


print("=" * 78)
print("PROJECT 2 UNSUPERVISED ML INTEGRATION TEST")
print("=" * 78)

# 1) Identical academic profiles must have maximum similarity.
identical = profile_similarity(
    21, 3.20, 2,
    21, 3.20, 2,
)

# 2) A nearby profile.
close = profile_similarity(
    21, 3.20, 2,
    22, 3.30, 2,
)

# 3) A profile at a substantially different academic stage.
distant = profile_similarity(
    21, 3.20, 2,
    24, 3.20, 4,
)

# 4) Two similar advanced students.
advanced_close = profile_similarity(
    24, 3.50, 4,
    23, 3.20, 4,
)

print()
print(f"Identical profile similarity:       {identical:.4f}")
print(f"Close profile similarity:           {close:.4f}")
print(f"Distant-stage profile similarity:   {distant:.4f}")
print(f"Advanced-close profile similarity:  {advanced_close:.4f}")
print()
print("Example membership vectors:")
print("Profile A:", explain_profile(21, 3.20, 2))
print("Profile B:", explain_profile(24, 3.20, 4))
print()

checks = {
    "identical_is_one": abs(identical - 1.0) < 1e-12,
    "scores_in_range": all(
        0.0 <= score <= 1.0
        for score in [identical, close, distant, advanced_close]
    ),
    "close_exceeds_distant": close > distant,
    "advanced_pair_is_high": advanced_close > 0.75,
}

for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'}: {name}")

if not all(checks.values()):
    raise SystemExit("One or more unsupervised matcher sanity checks failed.")

print()
print("PASS: Unsupervised profile similarity behaves as expected.")
print("=" * 78)
