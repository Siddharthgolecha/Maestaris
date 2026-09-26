from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_worker_prompt_forbids_schedule_mutation():
    text = (ROOT / "prompts" / "worker-pool.md").read_text()
    assert "this worker role is not authorized to create, update" in text
    assert "Do not call schedule mutation tools" in text
    assert "Schedule mutation is outside worker authority" in text


def test_root_contract_assigns_scheduler_mutation_to_orchestrator_or_user():
    text = (ROOT / "AGENTS.md").read_text()
    assert "Worker dispatchers and named workers are **not scheduler administrators**" in text
    assert "the orchestrator while reconciling `scheduler_bootstrap` desired topology" in text


def test_orchestrator_repairs_unexpected_disabled_required_schedule():
    text = (ROOT / "prompts" / "orchestrator.md").read_text()
    assert "unexpectedly disabled or paused as topology drift" in text
    assert "re-enable/update" in text


def test_scheduled_execution_defaults_to_autonomous_when_capable():
    worker = (ROOT / "prompts" / "worker-pool.md").read_text()
    root = (ROOT / "AGENTS.md").read_text()
    assert "normal scheduled mode is **autonomous when write-capable**" in worker
    assert "Pinning is a fallback/override, not a prerequisite" in worker
    assert "default mode is **autonomous when write-capable**" in root
    assert "A runtime-wide write denial is not a task-scientific `BLOCKED` result" in root


def test_review_is_persistent_queue_drain():
    orchestrator = (ROOT / "prompts" / "orchestrator.md").read_text()
    root = (ROOT / "AGENTS.md").read_text()
    assert "reviewer is a persistent queue-drainer" in orchestrator
    assert "Review is a queue, not a one-shot pinned job" in root
