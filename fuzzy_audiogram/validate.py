"""
validate.py — Validation and comparator models for fuzzy audiogram
classification.

Provides crisp classification reference, metric computation, ML model
training (XGBoost, Random Forest), and a full validation pipeline
comparing fuzzy vs crisp vs ML approaches.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd


def crisp_classify(pta):
    """Classify hearing loss severity using standard clinical thresholds
    (Goodman / Clark / WHO guidelines).

    Parameters
    ----------
    pta : float
        Pure Tone Average (dB HL), typically PTA-4
        (average of 500, 1000, 2000, 4000 Hz).

    Returns
    -------
    str
        One of: 'Normal', 'Mild', 'Moderate', 'Moderately Severe',
        'Severe', 'Profound'.
    """
    if pta <= 25:
        return 'Normal'
    elif pta <= 40:
        return 'Mild'
    elif pta <= 55:
        return 'Moderate'
    elif pta <= 70:
        return 'Moderately Severe'
    elif pta <= 90:
        return 'Severe'
    else:
        return 'Profound'


def _crisp_score(pta):
    """Convert PTA to a numeric severity score (0-5) for metric
    computation."""
    if pta <= 25:
        return 0
    elif pta <= 40:
        return 1
    elif pta <= 55:
        return 2
    elif pta <= 70:
        return 3
    elif pta <= 90:
        return 4
    else:
        return 5


def _fuzzy_score_to_numeric(label):
    """Map a fuzzy label string to numeric for metric computation."""
    mapping = {
        'Normal': 0,
        'Mild': 1,
        'Moderate': 2,
        'Moderately Severe': 3,
        'Severe': 4,
        'Profound': 5,
    }
    return mapping.get(label, np.nan)


def compute_metrics(y_true_score, y_pred_fuzzy_label, y_pred_crisp_label):
    """Compute comparison metrics between fuzzy, crisp, and ground truth
    classifications.

    Parameters
    ----------
    y_true_score : array-like
        Ground truth numeric severity scores (0-5).
    y_pred_fuzzy_label : array-like of str
        Predicted fuzzy labels.
    y_pred_crisp_label : array-like of str
        Predicted crisp labels.

    Returns
    -------
    dict
        Keys: spearman_rho, weighted_kappa, mae, icc, accuracy
        for both fuzzy and crisp predictors.
    """
    from scipy.stats import spearmanr
    from sklearn.metrics import cohen_kappa_score, mean_absolute_error, \
        accuracy_score
    from sklearn.metrics import r2_score

    y_true = np.array(y_true_score, dtype=float)
    y_fuzzy = np.array([_fuzzy_score_to_numeric(str(l))
                        for l in y_pred_fuzzy_label], dtype=float)
    y_crisp = np.array([_crisp_score(_label_to_pta_midpoint(str(l)))
                        if _label_to_pta_midpoint(str(l)) is not None
                        else np.nan
                        for l in y_pred_crisp_label], dtype=float)

    # Crisp labels are labels — convert to numeric score
    y_crisp_num = np.array([_fuzzy_score_to_numeric(str(l))
                            for l in y_pred_crisp_label], dtype=float)
    y_fuzzy_num = y_fuzzy  # already numeric

    valid_f = ~np.isnan(y_true) & ~np.isnan(y_fuzzy_num)
    valid_c = ~np.isnan(y_true) & ~np.isnan(y_crisp_num)

    result = {}

    if valid_f.sum() > 1:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            rho_f, _ = spearmanr(y_true[valid_f], y_fuzzy_num[valid_f])
        result['fuzzy_spearman_rho'] = round(float(rho_f), 4)
        result['fuzzy_weighted_kappa'] = round(float(
            cohen_kappa_score(y_true[valid_f].astype(int),
                              y_fuzzy_num[valid_f].astype(int),
                              weights='quadratic')), 4)
        result['fuzzy_mae'] = round(float(mean_absolute_error(
            y_true[valid_f], y_fuzzy_num[valid_f])), 4)
        result['fuzzy_r2'] = round(float(r2_score(
            y_true[valid_f], y_fuzzy_num[valid_f])), 4)
        result['fuzzy_accuracy_exact'] = round(float(
            accuracy_score(y_true[valid_f].astype(int),
                           y_fuzzy_num[valid_f].astype(int))), 4)
        result['fuzzy_accuracy_adjacent'] = round(float(
            np.mean(np.abs(y_true[valid_f] - y_fuzzy_num[valid_f]) <= 1)), 4)
    else:
        result.update({
            'fuzzy_spearman_rho': np.nan, 'fuzzy_weighted_kappa': np.nan,
            'fuzzy_mae': np.nan, 'fuzzy_r2': np.nan,
            'fuzzy_accuracy_exact': np.nan, 'fuzzy_accuracy_adjacent': np.nan,
        })

    if valid_c.sum() > 1:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            rho_c, _ = spearmanr(y_true[valid_c], y_crisp_num[valid_c])
        result['crisp_spearman_rho'] = round(float(rho_c), 4)
        result['crisp_weighted_kappa'] = round(float(
            cohen_kappa_score(y_true[valid_c].astype(int),
                              y_crisp_num[valid_c].astype(int),
                              weights='quadratic')), 4)
        result['crisp_mae'] = round(float(mean_absolute_error(
            y_true[valid_c], y_crisp_num[valid_c])), 4)
        result['crisp_r2'] = round(float(r2_score(
            y_true[valid_c], y_crisp_num[valid_c])), 4)
        result['crisp_accuracy_exact'] = round(float(
            accuracy_score(y_true[valid_c].astype(int),
                           y_crisp_num[valid_c].astype(int))), 4)
        result['crisp_accuracy_adjacent'] = round(float(
            np.mean(np.abs(y_true[valid_c] - y_crisp_num[valid_c]) <= 1)), 4)
    else:
        result.update({
            'crisp_spearman_rho': np.nan, 'crisp_weighted_kappa': np.nan,
            'crisp_mae': np.nan, 'crisp_r2': np.nan,
            'crisp_accuracy_exact': np.nan, 'crisp_accuracy_adjacent': np.nan,
        })

    return result


def _label_to_pta_midpoint(label):
    """Convert a human-readable severity label to a PTA midpoint for
    numeric conversion."""
    mapping = {
        'Normal': 12.5,
        'Mild': 33,
        'Moderate': 48,
        'Moderately Severe': 63,
        'Severe': 80.5,
        'Profound': 105,
    }
    return mapping.get(label)


def train_xgboost(X_train, y_train, **kwargs):
    """Train an XGBoost regressor for PTA / FAI prediction.

    Parameters
    ----------
    X_train : pd.DataFrame or np.ndarray
        Training features.
    y_train : array-like
        Training targets (continuous, e.g. FAI scores or PTA).
    **kwargs : dict
        Additional keyword arguments passed to XGBRegressor.

    Returns
    -------
    xgboost.XGBRegressor
        Trained XGBoost model.
    """
    from xgboost import XGBRegressor

    params = {
        'n_estimators': 200,
        'max_depth': 6,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'verbosity': 0,
    }
    params.update(kwargs)

    model = XGBRegressor(**params)
    model.fit(X_train, y_train)
    return model


def train_random_forest(X_train, y_train, **kwargs):
    """Train a Random Forest regressor for PTA / FAI prediction.

    Parameters
    ----------
    X_train : pd.DataFrame or np.ndarray
        Training features.
    y_train : array-like
        Training targets.
    **kwargs : dict
        Additional keyword arguments passed to RandomForestRegressor.

    Returns
    -------
    sklearn.ensemble.RandomForestRegressor
        Trained Random Forest model.
    """
    from sklearn.ensemble import RandomForestRegressor

    params = {
        'n_estimators': 200,
        'max_depth': 10,
        'min_samples_split': 5,
        'min_samples_leaf': 2,
        'random_state': 42,
        'n_jobs': -1,
    }
    params.update(kwargs)

    model = RandomForestRegressor(**params)
    model.fit(X_train, y_train)
    return model


def run_validation(df, feature_cols, target_col, test_size=0.2,
                   random_state=42):
    """Run a full validation comparing fuzzy, crisp, XGBoost, and
    Random Forest classification on a dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset containing feature columns, target column, and
        computed PTA.
    feature_cols : list of str
        Names of feature columns for ML models.
    target_col : str
        Name of the target column (ground truth severity).
    test_size : float
        Proportion of data for test split (default 0.2).
    random_state : int
        Random seed for train/test split.

    Returns
    -------
    dict
        Full comparison results with metrics for all four methods.
    """
    from sklearn.model_selection import train_test_split
    from .core import classify_audiogram, compute_audiogram_features, \
        FREQUENCIES_HZ
    from .validate import crisp_classify

    # Prepare data
    df = df.dropna(subset=[target_col]).copy()
    X = df[feature_cols].values
    y = df[target_col].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state,
    )

    # Train ML models
    xgb_model = train_xgboost(X_train, y_train)
    rf_model = train_random_forest(X_train, y_train)

    # Predictions
    y_pred_xgb = xgb_model.predict(X_test)
    y_pred_rf = rf_model.predict(X_test)

    # Fuzzy classification on test set
    fuzzy_labels = []
    crisp_labels = []
    ml_xgb_labels = []
    ml_rf_labels = []

    for i in range(len(X_test)):
        # We need threshold data - assume feature_cols map to thresholds
        # If the feature columns match the 8-frequency threshold format
        thresholds = X_test[i, :8] if X_test.shape[1] >= 8 else X_test[i]
        result = classify_audiogram(thresholds)
        fuzzy_labels.append(result['fai_label'])
        crisp_labels.append(crisp_classify(result['pt4a']))

        pta_pred_xgb = y_pred_xgb[i]
        pta_pred_rf = y_pred_rf[i]
        ml_xgb_labels.append(crisp_classify(pta_pred_xgb))
        ml_rf_labels.append(crisp_classify(pta_pred_rf))

    # Ground truth numeric scores
    y_true_num = np.array([_crisp_score(v) for v in y_test])

    # Compute metrics for all methods
    metrics_fuzzy = compute_metrics(y_true_num, fuzzy_labels, crisp_labels)

    # Additional ML metrics
    from sklearn.metrics import mean_absolute_error, r2_score
    result = {
        'n_train': len(X_train),
        'n_test': len(X_test),
        'feature_count': len(feature_cols),
        'xgb_mae': round(float(mean_absolute_error(y_test, y_pred_xgb)), 4),
        'rf_mae': round(float(mean_absolute_error(y_test, y_pred_rf)), 4),
        'xgb_r2': round(float(r2_score(y_test, y_pred_xgb)), 4),
        'rf_r2': round(float(r2_score(y_test, y_pred_rf)), 4),
    }
    result.update(metrics_fuzzy)

    return result
