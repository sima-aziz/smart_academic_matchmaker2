"""Train the final unsupervised academic-profile model on real student data."""

from __future__ import annotations

import json
import pickle
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

try:
    from ml.real_data import load_real_student_profiles
except ModuleNotFoundError:
    from real_data import load_real_student_profiles


BASE_DIR = Path(__file__).resolve().parent
SCALER_PATH = BASE_DIR / "profile_scaler.pkl"
MODEL_PATH = BASE_DIR / "gmm_profile_model.pkl"
METRICS_PATH = BASE_DIR / "unsupervised_training_metrics.json"
PROFILE_PATH = BASE_DIR / "cluster_profiles.csv"

N_COMPONENTS = 3
RANDOM_STATE = 42
STABILITY_SEEDS = [0, 1, 2, 3, 4, 42]


def _stability_ari(X_scaled):
    label_sets = []
    for seed in STABILITY_SEEDS:
        model = GaussianMixture(
            n_components=N_COMPONENTS,
            covariance_type="spherical",
            random_state=seed,
            n_init=10,
            max_iter=1000,
            reg_covar=1e-6,
        )
        label_sets.append(model.fit_predict(X_scaled))

    scores = [
        adjusted_rand_score(a, b)
        for a, b in combinations(label_sets, 2)
    ]
    return float(np.mean(scores)) if scores else 1.0


def train_final_model():
    profiles, audit = load_real_student_profiles()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(profiles)

    model = GaussianMixture(
        n_components=N_COMPONENTS,
        covariance_type="spherical",
        random_state=RANDOM_STATE,
        n_init=20,
        max_iter=1000,
        reg_covar=1e-6,
    )
    labels = model.fit_predict(X_scaled)
    responsibilities = model.predict_proba(X_scaled)

    with open(SCALER_PATH, "wb") as handle:
        pickle.dump(scaler, handle)

    with open(MODEL_PATH, "wb") as handle:
        pickle.dump(model, handle)

    analysis = profiles.copy()
    analysis["cluster"] = labels
    analysis["membership_confidence"] = responsibilities.max(axis=1)

    summary_rows = []
    for cluster_id, group in analysis.groupby("cluster"):
        summary_rows.append({
            "cluster": int(cluster_id),
            "students": int(len(group)),
            "percentage": float(len(group) / len(analysis) * 100),
            "mean_age": float(group["age"].mean()),
            "min_age": float(group["age"].min()),
            "max_age": float(group["age"].max()),
            "mean_gpa": float(group["gpa"].mean()),
            "min_gpa": float(group["gpa"].min()),
            "max_gpa": float(group["gpa"].max()),
            "mean_academic_year": float(group["academic_year"].mean()),
            "min_academic_year": float(group["academic_year"].min()),
            "max_academic_year": float(group["academic_year"].max()),
            "mean_membership_confidence": float(group["membership_confidence"].mean()),
        })

    cluster_profiles = pd.DataFrame(summary_rows).sort_values("cluster")
    cluster_profiles.to_csv(PROFILE_PATH, index=False)

    cluster_sizes = {
        str(int(cluster_id)): int(count)
        for cluster_id, count in analysis["cluster"].value_counts().sort_index().items()
    }

    metrics = {
        "learning_type": "unsupervised",
        "target_column": None,
        "synthetic_data_used": False,
        "source_rows": audit["source_rows"],
        "usable_rows": audit["usable_rows"],
        "dropped_rows_total": audit["dropped_rows_total"],
        "semester_out_of_application_range_rows": audit[
            "semester_out_of_application_range_rows"
        ],
        "features": ["age", "gpa", "academic_year"],
        "scaling": "StandardScaler",
        "model": "GaussianMixture",
        "covariance_type": "spherical",
        "n_components": N_COMPONENTS,
        "random_state": RANDOM_STATE,
        "silhouette": float(silhouette_score(X_scaled, labels)),
        "davies_bouldin": float(davies_bouldin_score(X_scaled, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(X_scaled, labels)),
        "stability_ari": _stability_ari(X_scaled),
        "average_membership_confidence": float(responsibilities.max(axis=1).mean()),
        "cluster_sizes": cluster_sizes,
        "selection_note": (
            "K=3 was selected after comparison with K-Means and GMM candidates. "
            "K=2 mostly isolated the small no-established-GPA profile while grouping "
            "the rest of the students together. K=3 retains that profile and separates "
            "earlier/mid from later academic profiles. Spherical covariance regularizes "
            "the model and soft GMM memberships support graded profile similarity."
        ),
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, ensure_ascii=False)

    print("=" * 78)
    print("FINAL UNSUPERVISED ACADEMIC-PROFILE MODEL")
    print("=" * 78)
    print(f"Source rows:                  {metrics['source_rows']}")
    print(f"Usable real students:         {metrics['usable_rows']}")
    print(f"Dropped rows:                 {metrics['dropped_rows_total']}")
    print("Synthetic students:           0")
    print("Synthetic collaboration label: none")
    print("Features:                     age, gpa, academic_year")
    print("Model:                        GMM (spherical, K=3)")
    print()
    print(f"Silhouette:                   {metrics['silhouette']:.4f}")
    print(f"Davies-Bouldin:               {metrics['davies_bouldin']:.4f}")
    print(f"Calinski-Harabasz:            {metrics['calinski_harabasz']:.4f}")
    print(f"Stability ARI:                {metrics['stability_ari']:.4f}")
    print(f"Mean membership confidence:   {metrics['average_membership_confidence']:.4f}")
    print()
    print("Cluster profiles:")
    print(cluster_profiles.round(4).to_string(index=False))
    print()
    print(f"Saved model:    {MODEL_PATH}")
    print(f"Saved scaler:   {SCALER_PATH}")
    print(f"Saved metrics:  {METRICS_PATH}")
    print(f"Saved profiles: {PROFILE_PATH}")

    return metrics, cluster_profiles


if __name__ == "__main__":
    train_final_model()
