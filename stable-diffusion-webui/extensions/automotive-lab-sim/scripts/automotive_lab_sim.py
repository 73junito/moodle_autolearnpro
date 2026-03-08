"""Automotive Lab Simulation WebUI extension.

Provides a compact simulation engine for automotive troubleshooting exercises.
This extension uses a local Ollama LLM (via HTTP) to generate realistic
test results. The file includes lightweight fallbacks so editors without
the WebUI dependencies can open it safely.
"""

# Pylint: allow long descriptive strings and compact UI builders in this
# file; the UI wiring tends to produce long lines and many small locals.
# Also allow the optional-import module variables to remain lowercase.
# pylint: disable=C0301,R0914,R0915,C0103

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import importlib
import time
# Optional third-party modules (fallback to None for editors that lack them)
try:
    gr = importlib.import_module("gradio")
except (ImportError, ModuleNotFoundError):
    gr = None

try:
    requests = importlib.import_module("requests")
except (ImportError, ModuleNotFoundError):
    requests = None

try:
    torch = importlib.import_module("torch")
except (ImportError, ModuleNotFoundError):
    torch = None

try:
    scripts = importlib.import_module("modules.scripts")
except (ImportError, ModuleNotFoundError):
    # Minimal local stub so the file can be linted/edited outside WebUI.
    class _StubScripts:
        """Local stub for the host `modules.scripts` API when not present.

        This provides a minimal `Script` base class with the attributes
        the extension expects so editors and linters can import the file
        without requiring the full WebUI runtime.
        """

        class Script:  # type: ignore
            """Minimal Script base stub exposing `AlwaysVisible` attribute."""

            AlwaysVisible = True

    scripts = _StubScripts()

# Configuration
OLLAMA_ENDPOINT = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3"


def detect_cuda_info() -> str:
    """Report a short summary describing CUDA availability.

    Uses ``torch`` if present; otherwise returns a readable failure string.
    """
    if torch is None:
        return "CUDA: detection failed (torch not available)"
    try:
        cuda_available = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU only"
        return f"CUDA: {'available' if cuda_available else 'not available'} ({device_name})"
    except (AttributeError, RuntimeError, OSError):
        return "CUDA: detection failed (torch error)"


@dataclass
class SimulationScenario:
    """Describe an automotive troubleshooting scenario.

    Attributes:
        title: short display title
        vehicle: make/model/engine string
        symptom_summary: customer complaint or observed symptoms
        hidden_fault: the true cause (kept internal)
        notes: optional instructor notes
    """

    title: str
    vehicle: str
    symptom_summary: str
    hidden_fault: str
    notes: str = ""


@dataclass
class SimulationState:
    """Runtime state for an active simulation instance."""

    scenario: Optional[SimulationScenario] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    solved: bool = False
    started_at: float = field(default_factory=time.time)

    def reset(self, scenario: SimulationScenario) -> None:
        """Reset the simulation for a new scenario."""
        self.scenario = scenario
        self.history = []
        self.solved = False
        self.started_at = time.time()

    def add_action(self, action: str, result: str) -> None:
        """Record a performed action and the LLM's result."""
        self.history.append({"action": action, "result": result, "timestamp": time.time()})


def get_predefined_scenarios() -> Dict[str, SimulationScenario]:
    """Return a small set of example scenarios keyed by identifier."""
    return {
        "no_start_weak_battery": SimulationScenario(
            title="No-Start – Weak Battery",
            vehicle="2012 Honda Accord 2.4L",
            symptom_summary="Customer states: 'Car won't start, just clicking noise.'",
            hidden_fault="Weak battery with corroded terminals",
            notes="Classic no-start due to low battery voltage and poor terminal contact.",
        ),
        "misfire_ignition_coil": SimulationScenario(
            title="Engine Misfire – Ignition Coil",
            vehicle="2018 Ford F150 3.5L EcoBoost",
            symptom_summary="Customer states: 'Engine misfire and rough idle, check engine light on.'",
            hidden_fault="Single cylinder misfire caused by faulty ignition coil",
            notes="Common modern misfire scenario.",
        ),
        "overheating_cooling_system": SimulationScenario(
            title="Overheating – Cooling System",
            vehicle="2010 Toyota Camry 2.5L",
            symptom_summary="Customer states: 'Temperature gauge climbs in traffic, coolant smell.'",
            hidden_fault="Sticking thermostat and low coolant level",
            notes="Overheating under load/idle with coolant loss.",
        ),
    }


SYSTEM_PROMPT = (
    "You are an Automotive Lab Simulation Engine for students.\n"
    "You are given: a vehicle, a symptom summary, a hidden fault, and the student's previous actions.\n"
    "When the student performs a diagnostic action, respond with realistic test results.\n"
    "Do NOT reveal the hidden fault directly. Keep responses concise, technical, and educational."
)


def call_ollama_simulation(
    scenario: SimulationScenario,
    state: SimulationState,
    student_action: str,
    request_hint: bool = False,
) -> str:
    """Compose a prompt and call the local Ollama LLM to simulate results.

    Returns a short text response or an error message.
    """
    history_text = ""
    for step in state.history:
        history_text += f"- Action: {step['action']}\n  Result: {step['result']}\n"

    user_prompt = (
        f"Vehicle: {scenario.vehicle}\n"
        f"Symptoms: {scenario.symptom_summary}\n"
        f"Hidden fault (do NOT reveal directly): {scenario.hidden_fault}\n\n"
        f"Student action: {student_action}\n"
        f"Requesting hint: {'yes' if request_hint else 'no'}\n\n"
        f"Previous steps:\n{history_text if history_text else 'None yet.'}\n\n"
        "Respond with either a test result/observation or a short hint. Do NOT mention that you are an AI."
    )

    if requests is None:
        return "LLM unavailable (requests package not installed)."

    try:
        resp = requests.post(
            OLLAMA_ENDPOINT,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        return content or "No response from LLM."
    except requests.exceptions.RequestException as exc:
        return f"Error calling LLM (request): {exc}"
    except (ValueError, KeyError) as exc:
        return f"LLM response parse error: {exc}"


class Script(scripts.Script):
    """Extension script integrating the Automotive Lab simulation into WebUI."""

    def title(self) -> str:
        """Return the extension title shown in the UI list."""
        return "Automotive Lab Simulation Plugin"

    def show(self, _is_img2img: bool) -> bool:
        """Indicate whether the extension UI should be visible.

        The argument is provided by the host but not used here.
        """
        return scripts.Script.AlwaysVisible

    def ui(self, _is_img2img: bool):
        """Build and return the Gradio UI components for the extension."""

        scenarios = get_predefined_scenarios()
        scenario_keys = list(scenarios.keys())
        scenario_labels = [scenarios[k].title for k in scenario_keys]

        sim_state = gr.State(SimulationState()) if gr is not None else None

        with gr.Group():
            gr.Markdown("## Automotive Lab Simulation Plugin 🚗🔧")
            gr.Markdown(
                "Simulate vehicle problems, choose diagnostic steps, and see realistic results."
            )

            cuda_info = gr.Markdown(value=detect_cuda_info()) if gr is not None else None

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

        # Wire handlers (only if gradio is present)
        if gr is not None:
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
