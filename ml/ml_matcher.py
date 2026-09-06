import os
import pickle
import pandas as pd


# ============================================================
# Configuration
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
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


# Load trained model

with open(
    MODEL_PATH,
    "rb"
) as file:

    model = pickle.load(
        file
    )


if model.n_features_in_ != len(FEATURES):
    raise ValueError(
        "Saved model does not match current ML feature configuration."
    )

# Load feature scaler

with open(
    SCALER_PATH,
    "rb"
) as file:

    scaler = pickle.load(
        file
    )
    
if scaler.n_features_in_ != len(FEATURES):
    raise ValueError(
        "Saved scaler does not match current ML feature configuration."
    )

# Predict collaboration probability

def predict_collaboration(
    course_similarity,
    gpa_similarity,
    commitment_similarity,
    age_similarity,
    year_similarity
):

    data = pd.DataFrame([{
    "course_similarity": course_similarity,
    "gpa_similarity": gpa_similarity,
    "commitment_similarity": commitment_similarity,
    "age_similarity": age_similarity,
    "year_similarity": year_similarity
    }])

    # Guarantee same feature order used during training
    data = data[FEATURES]

    # Apply the same scaling used during training
    scaled_data = scaler.transform(
        data
    )

    # Probability of successful collaboration
    probability = model.predict_proba(
        scaled_data
    )[0][1]

    return round(
        float(probability),
        4
    )