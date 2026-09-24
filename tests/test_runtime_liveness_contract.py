from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_orchestrator_prompt_preserves_recurring_schedule_liveness():
    text = (ROOT / "prompts" / "orchestrator.md").read_text()
    assert "Never disable, pause, or delete the recurring orchestrator schedule" in text
    assert "continue to another independent review candidate" in text
    assert "end only this poll and retry on the next scheduled run" in text


def test_root_agents_liveness_contract_is_role_independent():
    text = (ROOT / "AGENTS.md").read_text()
    assert "Every recurring Maestaris role" in text
    assert "orchestrator, worker dispatcher, or auditor" in text
    assert "candidate-local by default" in text
