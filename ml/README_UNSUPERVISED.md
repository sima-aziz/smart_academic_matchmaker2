# Project 2 ML: Real-Data Unsupervised Academic Profiles

## What changed

The previous Logistic Regression pipeline was trained on synthetic student pairs and a synthetic `successful_collaboration` target. The final Project 2 ML pipeline no longer uses that target and no longer generates synthetic students.

The deployed ML component now learns latent academic-profile structure from real student records and returns a **profile similarity**, not a probability of collaboration success.

## Runtime features

Only fields that have direct counterparts in the deployed web/Android system are used:

- `age`
- `gpa`
- `academic_year`

`program`, `semester`, valid shared courses and section/cross-section rules remain hard eligibility constraints outside ML. Shared courses and commitment remain in the rule-based half of the hybrid score.

## Pipeline

1. Load the real profile source data.
2. Validate values and map source semester 1-15 into academic year 1-5.
3. Standardize Age, GPA and Academic Year using `StandardScaler`.
4. Compare K-Means and spherical Gaussian Mixture Models for K=2..6.
5. Train the selected spherical GMM with K=3 on all usable real students.
6. For each live user, obtain a GMM soft-membership probability vector.
7. Compare two vectors with Jensen-Shannon distance.
8. Convert distance to ML profile similarity: `ML_similarity = 1 - JS_distance`.
9. Combine with the normalized rule score:

   `Hybrid = 0.50 * RuleScore + 0.50 * ML_similarity`

## Evaluation

Because there is no real collaboration target, Accuracy / Precision / Recall / F1 / ROC-AUC are not valid metrics for this final model. Evaluation uses:

- Silhouette score (higher is better)
- Davies-Bouldin index (lower is better)
- Calinski-Harabasz index (higher is better)
- Stability using Adjusted Rand Index across repeated initializations (closer to 1 is better)
- Cluster sizes and interpretable cluster profiles
- Functional sanity tests for pairwise similarity

## Commands

From the project root:

```bash
python -m ml.evaluate_unsupervised
python -m ml.train_unsupervised_model
python -m ml.test_integration
```

Run evaluation first when changing data/model configuration. Training creates the `.pkl`, metrics JSON and cluster-profile CSV used by the application/report.
