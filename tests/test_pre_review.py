from maestaris_orchestration.dispatcher import terminal_review_gate


def base_evidence(**overrides):
    evidence = dict(
        completion={"implementation": True, "tests": True},
        changed_paths=["maestaris_orchestration/pre_review.py", "tests/test_pre_review.py"],
        allowed_paths=["maestaris_orchestration", "tests"],
        head_sha="head",
        ci_available=True,
        ci_head_sha="head",
        ci_success=True,
        base_sha="main",
        current_main_sha="main",
    )
    evidence.update(overrides)
    return evidence


def test_dispatcher_terminal_gate_accepts_complete_exact_head_fresh_work():
    decision = terminal_review_gate(**base_evidence())
    assert decision.ready
    assert decision.blockers == ()


def test_known_incomplete_completion_bullet_blocks_review():
    decision = terminal_review_gate(**base_evidence(completion={"implementation": True, "docs": False}))
    assert not decision.ready
    assert "completion:docs" in decision.blockers


def test_cumulative_unrelated_diff_is_surfaced():
    decision = terminal_review_gate(**base_evidence(changed_paths=["maestaris_orchestration/pre_review.py", "unrelated/rewrite.txt"]))
    assert not decision.ready
    assert "scope:unrelated/rewrite.txt" in decision.blockers


def test_stale_ci_cannot_claim_exact_head_success():
    decision = terminal_review_gate(**base_evidence(ci_head_sha="old-head"))
    assert not decision.ready
    assert "ci:not-exact-head" in decision.blockers


def test_disjoint_stale_main_change_does_not_force_refresh():
    decision = terminal_review_gate(
        **base_evidence(
            base_sha="old-main",
            main_changed_paths=["docs/unrelated.md", "README.md"],
            mergeable=True,
        )
    )
    assert decision.ready
    assert not decision.needs_refresh
    assert decision.blockers == ()


def test_overlapping_stale_branch_requires_refresh_when_safe():
    decision = terminal_review_gate(
        **base_evidence(
            base_sha="old-main",
            main_changed_paths=["maestaris_orchestration/pre_review.py"],
            mergeable=True,
            refresh_mechanical_safe=True,
        )
    )
    assert not decision.ready
    assert decision.needs_refresh
    assert "integration:refresh-required" in decision.blockers


def test_unknown_stale_delta_remains_fail_closed():
    decision = terminal_review_gate(**base_evidence(base_sha="old-main", mergeable=True))
    assert not decision.ready
    assert "integration:stale-unverified" in decision.blockers


def test_nonmergeable_stale_branch_is_blocked():
    decision = terminal_review_gate(
        **base_evidence(base_sha="old-main", main_changed_paths=[], mergeable=False)
    )
    assert not decision.ready
    assert "integration:not-mergeable" in decision.blockers


def test_semantic_conflict_is_not_hidden_by_disjoint_paths():
    decision = terminal_review_gate(
        **base_evidence(
            base_sha="old-main",
            main_changed_paths=["docs/unrelated.md"],
            mergeable=True,
            refresh_mechanical_safe=True,
            semantic_conflict=True,
        )
    )
    assert not decision.ready
    assert not decision.needs_refresh
    assert "integration:semantic-conflict" in decision.blockers
