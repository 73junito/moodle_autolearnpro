import importlib.util
import sys
import types
from pathlib import Path


def load_module_from_path(path: str):
    spec = importlib.util.spec_from_file_location("automotive_lab_sim", path)
    mod = importlib.util.module_from_spec(spec)
    # Ensure the import machinery can find our fake requests module if present
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_simulation_state_reset_and_add_action():
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / "stable-diffusion-webui" / "extensions" / "automotive-lab-sim" / "scripts" / "automotive_lab_sim.py"

    # Ensure we load with a minimal requests module so import-time checks pass
    fake_requests = types.ModuleType("requests")

    def _post(*args, **kwargs):
        class _R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"message": {"content": "ok"}}

        return _R()

    fake_requests.post = _post
    sys.modules["requests"] = fake_requests

    mod = load_module_from_path(str(mod_path))

    scenario = mod.SimulationScenario(
        title="T1",
        vehicle="Test Car",
        symptom_summary="Does something",
        hidden_fault="Nothing",
    )
    state = mod.SimulationState()
    state.reset(scenario)

    assert state.scenario is scenario
    assert state.history == []
    assert not state.solved

    state.add_action("Check battery", "Voltage low")
    assert len(state.history) == 1
    assert state.history[0]["action"] == "Check battery"


def test_call_ollama_simulation_uses_requests_and_returns_content():
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / "stable-diffusion-webui" / "extensions" / "automotive-lab-sim" / "scripts" / "automotive_lab_sim.py"

    # Provide a fake requests module that returns a predictable JSON payload
    fake_requests = types.ModuleType("requests")

    def fake_post(url, json=None, timeout=None):
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"message": {"content": "Simulated result"}}

        return Resp()

    fake_requests.post = fake_post
    sys.modules["requests"] = fake_requests

    mod = load_module_from_path(str(mod_path))

    scenario = mod.SimulationScenario(
        title="T2",
        vehicle="Test Car",
        symptom_summary="Weird noise",
        hidden_fault="Loose clamp",
    )
    state = mod.SimulationState()

    result = mod.call_ollama_simulation(scenario, state, "Inspect clamp", request_hint=False)
    assert isinstance(result, str)
    assert "Simulated result" in result
