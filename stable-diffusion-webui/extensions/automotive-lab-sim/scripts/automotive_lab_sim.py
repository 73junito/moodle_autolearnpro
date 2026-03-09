"""Minimal Automotive Lab Simulation module suitable for editors.

This module keeps a tiny surface area so editors and linters can import
it without requiring the full WebUI or Gradio runtime.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import importlib
import time

# Optional runtime imports used when available
try:
    gr = importlib.import_module("gradio")
except (ImportError, ModuleNotFoundError):
    gr = None

try:
    requests = importlib.import_module("requests")
    _RequestException = getattr(
        getattr(requests, "exceptions", None), "RequestException", Exception
    )
except (ImportError, ModuleNotFoundError):
    requests = None
    _RequestException = Exception

try:
    torch = importlib.import_module("torch")
except (ImportError, ModuleNotFoundError):
    torch = None
try:
    scripts = importlib.import_module("modules.scripts")
except (ImportError, ModuleNotFoundError):
    class _StubScripts:  # pylint: disable=too-few-public-methods
        """Simple stub used when the host `modules.scripts` module is
        unavailable (editor environments).
        """

        AlwaysVisible = True

        class Script:  # type: ignore # pylint: disable=too-few-public-methods
            """Minimal Script base so the module can subclass when
            `modules.scripts` is not present.
            """
            AlwaysVisible = True

    scripts = _StubScripts()


OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3"


@dataclass
class SimulationScenario:
    """Data describing a training scenario for the automotive lab.

    This is intentionally minimal and serializable for tests.
    """
    title: str
    vehicle: str
    symptom_summary: str
    hidden_fault: str
    notes: str = ""


@dataclass
class SimulationState:
    """Runtime state container for an active simulation instance."""
    scenario: Optional[SimulationScenario] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    solved: bool = False
    started_at: float = field(default_factory=time.time)

    def reset(self, scenario: SimulationScenario) -> None:
        """Reset state for a new scenario."""
        self.scenario = scenario
        self.history = []
        self.solved = False
        self.started_at = time.time()

    def add_action(self, action: str, result: str) -> None:
        """Record an action and the simulation result."""
        self.history.append({
            "action": action,
            "result": result,
            "timestamp": time.time(),
        })


def call_ollama_simulation(
    scenario: SimulationScenario,
    _state: SimulationState,
    student_action: str,
    _request_hint: bool = False,
) -> str:
    """Call a local Ollama endpoint to simulate a diagnostic response.

    This function is intentionally small and tolerant of a missing
    `requests` module so editors can import the file.
    """
    if requests is None:
        return "LLM unavailable (requests package not installed)."

    # Build a user-focused prompt and call the local Ollama HTTP API.
    history_text = ""
    for step in _state.history:
        history_text += f"- Action: {step['action']}\n  Result: {step['result']}\n"

    user_prompt = (
        f"Vehicle: {scenario.vehicle}\n"
        f"Symptoms: {scenario.symptom_summary}\n"
        f"Hidden fault (do NOT reveal directly): {scenario.hidden_fault}\n\n"
        f"Student action: {student_action}\n"
        f"Requesting hint: {'yes' if _request_hint else 'no'}\n\n"
        f"Previous steps:\n{history_text if history_text else 'None yet.'}\n\n"
        "Respond with either a test result/observation or a short hint. Do NOT mention that you are an AI."
    )

    try:
        resp = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful automotive diagnostic tutor."},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return content or "No response from LLM."
    except _RequestException as exc:
        return f"Error calling LLM (request): {exc}"
    except (ValueError, KeyError) as exc:
        return f"LLM response parse error: {exc}"

class Script(scripts.Script):
    """Lightweight Script class compatible with the host WebUI API.

    The UI surface is intentionally minimal to keep this module importable
    in non-WebUI environments (editors, linters, tests).
    """

    def title(self) -> str:
        """Return a short human-facing title for the script."""
        return "Automotive Lab Simulation Plugin"

    def show(self, _is_img2img: bool) -> bool:
<<<<<<< HEAD
        """Indicate whether the extension UI should be visible.

        The argument is provided by the host but not used here.
        """
        return scripts.Script.AlwaysVisible

    def ui(self, _is_img2img: bool):
        """Build and return the Gradio UI components for the extension."""
        if gr is None:
            raise RuntimeError(
                "gradio is required to use the Automotive Lab Simulation Plugin UI. "
                "Install it with: pip install gradio"
            )

        scenarios = get_predefined_scenarios()
        scenario_keys = list(scenarios.keys())
        scenario_labels = [scenarios[k].title for k in scenario_keys]

        sim_state = gr.State(SimulationState())

        with gr.Group():
            gr.Markdown("## Automotive Lab Simulation Plugin 🚗🔧")
            gr.Markdown(
                "Simulate vehicle problems, choose diagnostic steps, and see realistic results."
            )

            cuda_info = gr.Markdown(value=detect_cuda_info())

            with gr.Row():
                scenario_dropdown = gr.Dropdown(
                    label="Select Scenario", choices=scenario_labels, value=scenario_labels[0]
                )
                start_button = gr.Button("Start / Reset Simulation", variant="primary")

            scenario_info = gr.Markdown(label="Scenario Description")

            with gr.Row():
                action_buttons = gr.Radio(
                    label="Common Diagnostic Actions",
                    choices=[
                        "Try to start engine",
                        "Check battery voltage",
                        "Scan OBD-II codes",
                        "Inspect spark plugs",
                        "Check ignition coils",
                        "Check fuel pressure",
                        "Inspect coolant level",
                        "Check thermostat operation",
                        "Visual inspection for leaks",
                    ],
                    value="Try to start engine",
                )

            free_action = gr.Textbox(
                label="Custom diagnostic action (optional)",
                placeholder="e.g. Perform compression test on cylinder 3",
            )

            with gr.Row():
                run_action_button = gr.Button("Run Action", variant="primary")
                hint_button = gr.Button("Request Hint")
                solve_button = gr.Button("I think I know the fault")

            output_log = gr.Markdown(label="Simulation Log")
            result_box = gr.Markdown(label="Latest Result / Hint")
            status_box = gr.Markdown(label="Status / Scoring")

        def format_log(state: Optional[SimulationState]) -> str:
            if state is None or not state.history:
                return "_No actions taken yet._"
            lines: List[str] = []
            for i, step in enumerate(state.history, start=1):
                lines.append(f"**Step {i}:**\n- Action: {step['action']}\n- Result: {step['result']}\n")
            return "\n".join(lines)

        def on_start_sim(selected_label: str, _state: SimulationState):
            key = next((k for k, s in scenarios.items() if s.title == selected_label), None)
            if key is None:
                key = list(scenarios.keys())[0]
            scenario = scenarios[key]
            if _state is None:
                _state = SimulationState()
            _state.reset(scenario)
            desc = (
                f"**Scenario:** {scenario.title}\n\n"
                f"**Vehicle:** {scenario.vehicle}\n\n"
                f"**Customer Complaint:** {scenario.symptom_summary}\n\n"
                "*(Hidden fault is stored internally and not shown to the student.)*"
            )
            return desc, _state, "Simulation started. Choose a diagnostic action.", "Simulation ready."

        def on_run_action(selected_action: str, custom_action: str, _state: SimulationState):
            if _state is None or _state.scenario is None:
                return _state, "No active simulation. Start a scenario first.", format_log(_state), "Idle."
            action = custom_action.strip() if custom_action.strip() else selected_action
            if not action:
                return _state, "Please choose or enter an action.", format_log(_state), "Waiting for action."
            result = call_ollama_simulation(_state.scenario, _state, action, request_hint=False)
            _state.add_action(action, result)
            return _state, result, format_log(_state), "Simulation running."

        def on_hint(_state: SimulationState):
            if _state is None or _state.scenario is None:
                return _state, "No active simulation. Start a scenario first.", format_log(_state), "Idle."
            result = call_ollama_simulation(
                _state.scenario,
                _state,
                student_action="Requesting a hint about next best diagnostic step.",
                request_hint=True,
            )
            _state.add_action("Hint requested", result)
            return _state, result, format_log(_state), "Hint provided."

        def on_solve(_state: SimulationState):
            if _state is None or _state.scenario is None:
                return _state, "No active simulation. Start a scenario first.", format_log(_state), "Idle."
            steps = len(_state.history)
            elapsed = time.time() - _state.started_at
            minutes = elapsed / 60.0
            scenario = _state.scenario
            msg = (
                f"### Simulation Summary\n\n"
                f"**Scenario:** {scenario.title}\n"
                f"**Hidden Fault:** {scenario.hidden_fault}\n\n"
                f"**Steps taken:** {steps}\n"
                f"**Time elapsed:** {minutes:.1f} minutes\n\n"
                "Use this summary to debrief with students: discuss which actions were efficient, "
                "which were unnecessary, and how to improve the diagnostic workflow."
            )
            _state.solved = True
            return _state, msg, format_log(_state), "Simulation completed."

        # Wire handlers
        start_button.click(
            on_start_sim,
            inputs=[scenario_dropdown, sim_state],
            outputs=[scenario_info, sim_state, result_box, status_box],
        )
        run_action_button.click(
            on_run_action,
            inputs=[action_buttons, free_action, sim_state],
            outputs=[sim_state, result_box, output_log, status_box],
        )
        hint_button.click(
            on_hint,
            inputs=[sim_state],
            outputs=[sim_state, result_box, output_log, status_box],
        )
        solve_button.click(
            on_solve,
            inputs=[sim_state],
            outputs=[sim_state, result_box, output_log, status_box],
        )

        return [
            scenario_dropdown,
            start_button,
            scenario_info,
            action_buttons,
            free_action,
            run_action_button,
            hint_button,
            solve_button,
            output_log,
            result_box,
            status_box,
            cuda_info,
        ]
=======
        """Whether the script should be shown in the current UI mode."""
        return scripts.AlwaysVisible

    def ui(self, _is_img2img: bool):
        """Return a minimal UI description; empty when Gradio is absent."""
        # Minimal UI surface so file imports cleanly in non-WebUI envs.
        return []
>>>>>>> 39fa505 (WIP: save tracked changes before syncing main)
