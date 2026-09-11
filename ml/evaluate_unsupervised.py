"""Compare candidate unsupervised profile models on real student data.

This is model-selection/evaluation code.  It does NOT use a collaboration
label, because the real source dataset has no measured collaboration target.

We compare:
    * K-Means: hard cluster membership baseline
    * Gaussian Mixture Model (spherical covariance): soft membership model

For each K in 2..6 we report held-out internal clustering metrics and a
stability score across random initializations.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

try:
    from ml.real_data import load_real_student_profiles
except ModuleNotFoundError:
    from real_data import load_real_student_profiles


BASE_DIR = Path(__file__).resolve().parent
RESULTS_PATH = BASE_DIR / "unsupervised_model_comparison.csv"
RANDOM_STATE = 42
K_VALUES = range(2, 7)
STABILITY_SEEDS = [0, 1, 2, 3, 4, 42]


def _cluster_metrics(X, labels):
    unique = np.unique(labels)
    if len(unique) < 2:
        return {
            "silhouette": np.nan,
            "davies_bouldin": np.nan,
            "calinski_harabasz": np.nan,
        }

    return {
        "silhouette": float(silhouette_score(X, labels)),
        "davies_bouldin": float(davies_bouldin_score(X, labels)),
        "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
    }


def _mean_pairwise_ari(label_sets):
    scores = [
        adjusted_rand_score(a, b)
        for a, b in combinations(label_sets, 2)
    ]
    return float(np.mean(scores)) if scores else 1.0


def _stability_kmeans(X_scaled, k):
    labels = []
    for seed in STABILITY_SEEDS:
        model = KMeans(
            n_clusters=k,
            random_state=seed,
            n_init=20,
        )
        labels.append(model.fit_predict(X_scaled))
    return _mean_pairwise_ari(labels)


def _stability_gmm(X_scaled, k):
    labels = []
    for seed in STABILITY_SEEDS:
        model = GaussianMixture(
            n_components=k,
            covariance_type="spherical",
            random_state=seed,
            n_init=10,
            max_iter=1000,
            reg_covar=1e-6,
        )
        labels.append(model.fit_predict(X_scaled))
    return _mean_pairwise_ari(labels)


def evaluate_models():
    profiles, audit = load_real_student_profiles()

    X_train, X_test = train_test_split(
        profiles,
        test_size=0.20,
        random_state=RANDOM_STATE,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Stability is measured on the full cleaned dataset after one common
    # scaling transform so only the clustering initialization changes.
    full_scaler = StandardScaler()
    X_full_scaled = full_scaler.fit_transform(profiles)

    rows = []

    for k in K_VALUES:
        kmeans = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=20,
        )
        kmeans.fit(X_train_scaled)
        labels = kmeans.predict(X_test_scaled)
        metrics = _cluster_metrics(X_test_scaled, labels)
        counts = np.bincount(labels, minlength=k)

        rows.append({
            "model": "KMeans",
            "k": k,
            **metrics,
            "smallest_test_cluster": int(counts.min()),
            "smallest_test_cluster_pct": float(counts.min() / len(labels) * 100),
            "stability_ari": _stability_kmeans(X_full_scaled, k),
            "heldout_log_likelihood": np.nan,
        })

        gmm = GaussianMixture(
            n_components=k,
            covariance_type="spherical",
            random_state=RANDOM_STATE,
            n_init=10,
            max_iter=1000,
            reg_covar=1e-6,
        )
        gmm.fit(X_train_scaled)
        labels = gmm.predict(X_test_scaled)
        metrics = _cluster_metrics(X_test_scaled, labels)
        counts = np.bincount(labels, minlength=k)

        rows.append({
            "model": "GMM-spherical",
            "k": k,
            **metrics,
            "smallest_test_cluster": int(counts.min()),
            "smallest_test_cluster_pct": float(counts.min() / len(labels) * 100),
            "stability_ari": _stability_gmm(X_full_scaled, k),
            "heldout_log_likelihood": float(gmm.score(X_test_scaled)),
        })

    results = pd.DataFrame(rows)
    results.to_csv(RESULTS_PATH, index=False)

    print("=" * 88)
    print("UNSUPERVISED MODEL COMPARISON - REAL STUDENT PROFILES")
    print("=" * 88)
    print(f"Source rows:       {audit['source_rows']}")
    print(f"Usable rows:       {audit['usable_rows']}")
    print(f"Dropped rows:      {audit['dropped_rows_total']}")
    print("Features:          age, gpa, academic_year")
    print("Train/test split:  80% / 20% (for held-out internal validation)")
    print()

    display_columns = [
        "model",
        "k",
        "silhouette",
        "davies_bouldin",
        "calinski_harabasz",
        "smallest_test_cluster_pct",
        "stability_ari",
        "heldout_log_likelihood",
    ]

    print(results[display_columns].round(4).to_string(index=False))
    print()
    print("Interpretation:")
    print("  Silhouette:          higher is better.")
    print("  Davies-Bouldin:      lower is better.")
    print("  Calinski-Harabasz:   higher is better.")
    print("  Stability ARI:       closer to 1 means repeated fits reproduce the structure.")
    print()
    print("Model choice used by the application: GMM-spherical with K=3.")
    print("Why: K=2 mainly isolates the small no-established-GPA group and leaves")
    print("most established students in one broad cluster. K=3 preserves that real")
    print("special case while also separating earlier/mid and later academic profiles.")
    print("GMM is preferred over K-Means for deployment because its soft membership")
    print("probabilities allow a graded profile-similarity score rather than a hard")
    print("same-cluster/different-cluster decision.")
    print()
    print(f"Saved comparison to: {RESULTS_PATH}")

    return results


if __name__ == "__main__":
    evaluate_models()
