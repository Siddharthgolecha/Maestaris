from zerion_orchestration.admission import admission_decision


def test_unconfigured_repository_preserves_legacy_admission():
    assert admission_decision({"task_id": "a"}, []).admitted


def test_named_resource_limit_is_never_exceeded():
    active = [{"task_id": "a", "resources": {"gpu": 1}}]
    decision = admission_decision(
        {"task_id": "b", "resources": {"gpu": 1}},
        active,
        resource_limits={"gpu": 1},
    )
    assert not decision.admitted


def test_expired_resource_lease_recovers_when_removed_from_active_projection():
    task = {"task_id": "b", "resources": {"gpu": 1}}
    assert admission_decision(task, [], resource_limits={"gpu": 1}).admitted


def test_unknown_named_resource_fails_closed():
    decision = admission_decision(
        {"task_id": "b", "resources": {"deployment": 1}},
        [],
        resource_limits={"gpu": 1},
    )
    assert not decision.admitted


def test_same_priority_fair_share_limit_blocks_monopoly():
    active = [{"task_id": "a", "priority": "P1", "fair_share_group": "alpha"}]
    decision = admission_decision(
        {"task_id": "b", "priority": "P1", "fair_share_group": "alpha"},
        active,
        fair_share_limits={"alpha": 1},
    )
    assert not decision.admitted


def test_fair_share_does_not_compare_across_priority_classes():
    active = [{"task_id": "a", "priority": "P1", "fair_share_group": "alpha"}]
    decision = admission_decision(
        {"task_id": "p0", "priority": "P0", "fair_share_group": "alpha"},
        active,
        fair_share_limits={"alpha": 1},
    )
    assert decision.admitted


def test_independent_groups_do_not_consume_each_others_share():
    active = [{"task_id": "a", "priority": "P1", "fair_share_group": "alpha"}]
    decision = admission_decision(
        {"task_id": "b", "priority": "P1", "fair_share_group": "beta"},
        active,
        fair_share_limits={"alpha": 1, "beta": 1},
    )
    assert decision.admitted
