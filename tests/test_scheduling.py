from zerion_orchestration.scheduling import scheduling_decision


def task(task_id, priority="P1", deps=(), age=0, eligible=True):
    return {
        "task_id": task_id,
        "priority": priority,
        "depends_on": list(deps),
        "age": age,
        "eligible": eligible,
    }


def test_priority_always_outranks_inferred_unblocking_value():
    tasks = [
        task("p0", "P0", age=9),
        task("root", "P1", age=0),
        task("a", "P1", deps=("root",)),
        task("b", "P1", deps=("root",)),
        task("c", "P1", deps=("root",)),
    ]
    decision = scheduling_decision(tasks)
    assert decision.task_id == "p0"
    assert decision.ranked[:2] == ("p0", "root")
    assert "priority=P0 first" in decision.explanation


def test_chain_prefers_root_that_unlocks_longer_critical_path():
    tasks = [
        task("short", age=0),
        task("long", age=10),
        task("long-2", deps=("long",)),
        task("long-3", deps=("long-2",)),
    ]
    decision = scheduling_decision(tasks)
    assert decision.task_id == "long"
    assert decision.blocked == ("long-2", "long-3")
    assert "critical_depth=2" in decision.explanation


def test_diamond_counts_unique_downstream_tasks():
    tasks = [
        task("diamond", age=5),
        task("left", deps=("diamond",)),
        task("right", deps=("diamond",)),
        task("join", deps=("left", "right")),
        task("independent", age=0),
    ]
    decision = scheduling_decision(tasks)
    assert decision.task_id == "diamond"
    assert "unblocks=3" in decision.explanation


def test_cycle_and_unresolved_dependencies_are_blocked_and_explained():
    tasks = [
        task("a", deps=("b",)),
        task("b", deps=("a",)),
        task("missing", deps=("external",)),
        task("ok"),
    ]
    decision = scheduling_decision(tasks)
    assert decision.task_id == "ok"
    assert decision.cycles == (("a", "b"),)
    assert decision.blocked == ("a", "b", "missing")


def test_completed_dependency_makes_child_eligible():
    decision = scheduling_decision(
        [task("child", deps=("done",)), task("other", age=2)],
        completed={"done"},
    )
    assert decision.task_id == "child"


def test_blocked_caller_eligibility_and_age_then_id_tie_break():
    tasks = [
        task("blocked", age=-1, eligible=False),
        task("older", age=1),
        task("newer", age=2),
    ]
    decision = scheduling_decision(tasks)
    assert decision.task_id == "older"
    assert decision.blocked == ("blocked",)

    tied = scheduling_decision([task("b", age=1), task("a", age=1)])
    assert tied.ranked == ("a", "b")


def test_independent_tasks_are_deterministic():
    tasks = [task("z", age=3), task("x", age=1), task("y", age=2)]
    assert scheduling_decision(tasks).ranked == ("x", "y", "z")
