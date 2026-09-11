"""Loading and cleaning the real student-profile dataset used by Project 2.

The unsupervised model deliberately uses only attributes that have direct
counterparts in the deployed Smart Academic Matchmaker system:

    Age             -> Preferences.age
    Current CGPA    -> Preferences.gpa
    Academic Year   -> Preferences.academic_year

The source dataset stores Current Semester rather than Academic Year.  The
conversion used here groups three consecutive semesters into one academic
year (1-3 -> year 1, 4-6 -> year 2, ... 13-15 -> year 5).

No collaboration target is created and no synthetic students are generated.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = BASE_DIR / "data" / "real_student_profiles_source.csv"

SOURCE_COLUMNS = [
    "Age",
    "Current CGPA",
    "Current Semester",
]

MODEL_FEATURES = [
    "age",
    "gpa",
    "academic_year",
]


def load_real_student_profiles(dataset_path: str | Path | None = None):
    """Load, validate, and clean the real student-profile data.

    Returns
    -------
    profiles : pandas.DataFrame
        Clean model-ready columns: age, gpa, academic_year.
    audit : dict
        Counts describing what happened during cleaning.

    Notes
    -----
    * GPA values of 0 are retained.  In the source data these occur mostly
      for first-semester students with zero completed credits, so treating
      them as automatically missing would be an unsupported assumption.
    * Semester values above 15 cannot map to the application's year range
      1..5 under the 3-semesters-per-year conversion and are therefore
      excluded rather than clipped or guessed.
    """

    path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH

    df = pd.read_csv(path)
    original_rows = len(df)

    missing_columns = [column for column in SOURCE_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(
            "Real dataset is missing required columns: "
            + ", ".join(missing_columns)
        )

    work = df[SOURCE_COLUMNS].copy()

    # Convert to numeric explicitly; malformed values become NaN and are
    # counted in the audit rather than silently coerced into made-up values.
    for column in SOURCE_COLUMNS:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    numeric_invalid_rows = int(work.isna().any(axis=1).sum())
    work = work.dropna().copy()

    # These are direct validity limits, not statistical outlier trimming.
    invalid_age = ~work["Age"].between(18, 100)
    invalid_gpa = ~work["Current CGPA"].between(0, 4)
    invalid_semester = ~work["Current Semester"].between(1, 15)

    invalid_range_mask = invalid_age | invalid_gpa | invalid_semester
    invalid_range_rows = int(invalid_range_mask.sum())

    # Keep separate semester audit because it is the only filter expected
    # to remove rows in the supplied source file.
    semester_out_of_application_range_rows = int(invalid_semester.sum())

    work = work.loc[~invalid_range_mask].copy()

    # Three semesters correspond to one application academic year.
    work["Academic Year"] = (
        ((work["Current Semester"].astype(int) - 1) // 3) + 1
    )

    profiles = pd.DataFrame({
        "age": work["Age"].astype(float),
        "gpa": work["Current CGPA"].astype(float),
        "academic_year": work["Academic Year"].astype(float),
    }).reset_index(drop=True)

    audit = {
        "source_path": str(path),
        "source_rows": int(original_rows),
        "numeric_invalid_rows": numeric_invalid_rows,
        "invalid_range_rows": invalid_range_rows,
        "semester_out_of_application_range_rows": semester_out_of_application_range_rows,
        "usable_rows": int(len(profiles)),
        "dropped_rows_total": int(original_rows - len(profiles)),
        "features": MODEL_FEATURES,
    }

    return profiles, audit
