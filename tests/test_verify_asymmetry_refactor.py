import hashlib
import json
import pickle
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "verify_asymmetry_refactor.py"


def copy_script(tmp_path):
    script = tmp_path / "tests" / SCRIPT.name
    script.parent.mkdir()
    shutil.copy(SCRIPT, script)
    return script


def test_missing_baseline_is_reported(tmp_path):
    script = copy_script(tmp_path)
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert "SKIP asymmetry verification: baseline not found" in result.stdout


def test_missing_cohort_is_reported(tmp_path, monkeypatch, capsys):
    from fuzzy_audiogram import combined_data

    script = copy_script(tmp_path)
    baseline = tmp_path / "archive" / "predictions_PRE_asymmetry_refactor.pkl"
    baseline.parent.mkdir()
    baseline.touch()
    monkeypatch.setattr(combined_data, "CYCLES", [("test", str(tmp_path / "missing"), str(tmp_path / "missing2"))])
    monkeypatch.setattr(sys, "path", list(sys.path))

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(script), run_name="__main__")
    assert exc.value.code == 0
    assert "SKIP asymmetry verification: NHANES files not found" in capsys.readouterr().out


@pytest.mark.parametrize("scores, expected_md5, succeeds", [
    ([1.0], None, False),
    ([2.0], "baseline", False),
    ([1.0, 2.0], "baseline", False),
    ([1.0], "baseline", True),
])
def test_comparison_enforces_baseline(tmp_path, monkeypatch, scores, expected_md5, succeeds):
    from fuzzy_audiogram import combined_data, core

    script = copy_script(tmp_path)
    baseline = tmp_path / "archive" / "predictions_PRE_asymmetry_refactor.pkl"
    baseline.parent.mkdir()
    baseline.write_bytes(pickle.dumps({"fai": [1.0]}))
    metrics = tmp_path / "data" / "output_participant" / "metrics_participant.json"
    metrics.parent.mkdir(parents=True)
    metrics.write_text(json.dumps({"mf_params": {}, "label_thresholds": []}))

    aux = tmp_path / "aux.xpt"
    demo = tmp_path / "demo.xpt"
    aux.touch()
    demo.touch()
    monkeypatch.setattr(combined_data, "CYCLES", [("test", "/nonexistent/aux.xpt", "/nonexistent/demo.xpt")])

    def load():
        assert combined_data.CYCLES == [("test", aux, demo)]
        return None

    monkeypatch.setattr(combined_data, "load_combined_nhanes", load)
    monkeypatch.setattr(combined_data, "extract_combined_audiometry", lambda raw: None)
    monkeypatch.setattr(combined_data, "clean_ears", lambda audio: [(i, "", "", []) for i in range(5)])
    monkeypatch.setattr(core, "SEVERITY_MF_PARAMS", core.SEVERITY_MF_PARAMS)
    monkeypatch.setattr(core, "SEVERITY_LABEL_THRESHOLDS", core.SEVERITY_LABEL_THRESHOLDS)
    monkeypatch.setattr(core, "classify_audiogram", lambda left, right: {"fai_score": 1.0})
    monkeypatch.setattr(core, "_interpret_severity_score", lambda score: "normal")
    pipeline = SimpleNamespace(
        build_fis_with_params=lambda params: (SimpleNamespace(rules=[], consequents=[]), None),
        classify_ears_batched=lambda system, rows: [{"fai_score": score} for score in scores],
    )
    monkeypatch.setitem(sys.modules, "pipeline_participant", pipeline)
    monkeypatch.setattr(sys, "path", list(sys.path))
    if expected_md5:
        original_md5 = hashlib.md5
        baseline_hash = original_md5(np.asarray([1.0], float).tobytes()).hexdigest()
        monkeypatch.setattr(hashlib, "md5", lambda data: SimpleNamespace(hexdigest=lambda:
            "7e75859bc305053884a3841dd6a4dfca"
            if original_md5(data).hexdigest() == baseline_hash else "different"))

    if succeeds:
        runpy.run_path(str(script), run_name="__main__")
    else:
        with pytest.raises(SystemExit, match="FAIL: asymmetry verification"):
            runpy.run_path(str(script), run_name="__main__")
