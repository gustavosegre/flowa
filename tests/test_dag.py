import pytest
from flowa.core.pipeline import Step
from flowa.core.dag import build_execution_order


def names(order):
    return [s.name for s in order]


def test_single_step():
    steps = [Step(name="a", run="echo a")]
    assert names(build_execution_order(steps)) == ["a"]


def test_linear_chain():
    steps = [
        Step(name="a", run="echo a"),
        Step(name="b", run="echo b", depends_on=["a"]),
        Step(name="c", run="echo c", depends_on=["b"]),
    ]
    assert names(build_execution_order(steps)) == ["a", "b", "c"]


def test_parallel_steps():
    steps = [
        Step(name="a", run="echo a"),
        Step(name="b", run="echo b", depends_on=["a"]),
        Step(name="c", run="echo c", depends_on=["a"]),
        Step(name="d", run="echo d", depends_on=["b", "c"]),
    ]
    order = names(build_execution_order(steps))
    assert order[0] == "a"
    assert set(order[1:3]) == {"b", "c"}
    assert order[3] == "d"


def test_no_dependencies():
    steps = [
        Step(name="x", run="echo x"),
        Step(name="y", run="echo y"),
        Step(name="z", run="echo z"),
    ]
    order = names(build_execution_order(steps))
    assert set(order) == {"x", "y", "z"}


def test_cycle_raises():
    steps = [
        Step(name="a", run="echo a", depends_on=["b"]),
        Step(name="b", run="echo b", depends_on=["a"]),
    ]
    with pytest.raises(Exception, match="Cycle detected"):
        build_execution_order(steps)


def test_empty_pipeline():
    assert build_execution_order([]) == []
