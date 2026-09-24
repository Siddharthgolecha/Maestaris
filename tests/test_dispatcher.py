from maestaris_orchestration.dispatcher import dispatcher_selection


def task(task_id, priority="P1", group="", resources=None, age=0):
    return {
        "task_id": task_id,
        "priority": priority,
        "depends_on": [],
        "age": age,
        "fair_share_group": group,
        "resources": resources or {},
    }


def test_denied_candidate_yields_to_admissible_same_priority_peer():
    tasks = [task("alpha-2", group="alpha", age=1), task("beta-1", group="beta", age=2)]
    decision = dispatcher_selection(
        tasks,
        fair_share_limits={"alpha": 1, "beta": 1},
        served={"alpha": 1, "beta": 0},
        eligible_groups=("alpha", "beta"),
    )
    assert decision.task_id == "beta-1"
    assert decision.denied == ("alpha-2",)


def test_named_resource_saturation_blocks_ack_selection():
    tasks = [task("gpu-next", resources={"gpu": 1})]
    active = [task("gpu-active", resources={"gpu": 1})]
    decision = dispatcher_selection(tasks, active=active, resource_limits={"gpu": 1})
    assert decision.task_id is None
    assert decision.denied == ("gpu-next",)


def test_denied_high_priority_never_falls_through_to_lower_priority():
    tasks = [
        task("p0-gpu", priority="P0", resources={"gpu": 1}),
        task("p1-free", priority="P1"),
    ]
    active = [task("active", priority="P0", resources={"gpu": 1})]
    decision = dispatcher_selection(tasks, active=active, resource_limits={"gpu": 1})
    assert decision.task_id is None
    assert decision.denied == ("p0-gpu",)


def test_unconfigured_admission_preserves_lightweight_selection():
    tasks = [task("older", age=1), task("newer", age=2)]
    decision = dispatcher_selection(tasks)
    assert decision.task_id == "older"
    assert decision.denied == ()
