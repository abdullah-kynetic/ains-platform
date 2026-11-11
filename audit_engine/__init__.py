"""Stage 3 AI analysis orchestration: extraction, safety screens, rubric, adapter calls.

Everything here produces DRAFTS for a human auditor. Nothing here approves a finding, signs a
report or releases anything to a client. Model calls only ever go through the authenticated
adapter service (``ai_adapter``); this package holds no provider URL, key or SDK.
"""
