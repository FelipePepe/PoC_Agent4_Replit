from core.registry import AGENT_NAMES


def test_agent_registry_exposes_expected_agent_names() -> None:
    assert AGENT_NAMES == ('supervisor', 'planner', 'editor', 'verifier', 'searcher')
