"""Kien AML independent-testing engine.

Pure, deterministic workflow logic: test steps, evidence collection, rule checks and scoring.
No model calls, no network, no secrets. Model-assisted checks live behind ai_adapter/ and
return the same Observation type. Everything here works on synthetic firms only.
"""
