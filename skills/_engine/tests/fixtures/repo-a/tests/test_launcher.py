import scripts.run_risk


def test_notebook_path():
    assert scripts.run_risk.NOTEBOOK == "src/RiskWriter.scala"
