"""Runtime unsupervised profile similarity for Smart Academic Matchmaker.

The old supervised implementation predicted a synthetic
``successful_collaboration`` label.  This module instead compares two users
using soft academic-profile memberships learned from real student data.

Important: the returned value is a *profile similarity*, not a probability
that collaboration will succeed.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import pandas as pd
from scipy.spatial.distance import jensenshannon


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "gmm_profile_model.pkl"
SCALER_PATH = BASE_DIR / "profile_scaler.pkl"

FEATURES = [
    "age",
    "gpa",
    "academic_year",
]


def _load_artifacts():
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        raise FileNotFoundError(
            "Unsupervised ML artifacts are missing. Run "
            "`python -m ml.train_unsupervised_model` from the project root."
        )

    with open(MODEL_PATH, "rb") as handle:
        model = pickle.load(handle)

    with open(SCALER_PATH, "rb") as handle:
        scaler = pickle.load(handle)

    if getattr(model, "n_features_in_", len(FEATURES)) != len(FEATURES):
        raise ValueError("Saved GMM model does not match current feature configuration.")

    if getattr(scaler, "n_features_in_", len(FEATURES)) != len(FEATURES):
        raise ValueError("Saved scaler does not match current feature configuration.")

    return model, scaler


model, scaler = _load_artifacts()


def academic_profile_membership(age, gpa, academic_year):
    """Return the GMM soft-membership probabilities for one user profile."""

    row = pd.DataFrame([{
        "age": float(age),
        "gpa": float(gpa),
        "academic_year": float(academic_year),
    }], columns=FEATURES)

    scaled = scaler.transform(row)
    probabilities = model.predict_proba(scaled)[0]

    # Do not round here; downstream similarity should use full precision.
    return probabilities


def profile_similarity(
    age_1,
    gpa_1,
    academic_year_1,
    age_2,
    gpa_2,
    academic_year_2,
):
    """Calculate learned academic-profile similarity in the closed interval [0, 1].

    Each student is represented by the GMM posterior probability vector over
    latent academic profiles.  Jensen-Shannon distance compares the two
    probability distributions.  With logarithm base 2 the returned distance
    lies in [0, 1], so ``1 - distance`` is a convenient similarity score.
    """

    p = academic_profile_membership(age_1, gpa_1, academic_year_1)
    q = academic_profile_membership(age_2, gpa_2, academic_year_2)

    distance = float(jensenshannon(p, q, base=2.0))
    similarity = 1.0 - distance

    # Numerical protection only; mathematically the score is already [0, 1].
    return max(0.0, min(1.0, similarity))


def explain_profile(age, gpa, academic_year):
    """Return a small diagnostic dictionary useful in tests and reports."""

    probabilities = academic_profile_membership(age, gpa, academic_year)
    cluster = int(probabilities.argmax())

    return {
        "cluster": cluster,
        "membership_probabilities": [float(value) for value in probabilities],
        "membership_confidence": float(probabilities.max()),
    }
