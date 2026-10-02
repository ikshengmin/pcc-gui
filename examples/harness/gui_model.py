"""PCC Harness GUI state derived from the session event log."""

from harness_runtime import HarnessRuntime


class HarnessGuiState:
    """Small first-shell state owner shared by headless and native GUI paths."""

    def __init__(self) -> None:
        self.runtime = HarnessRuntime()
        self.closed = False
        self.submitting_agent = None

    @property
    def agent(self):
        """Never retain a replaced session's agent as the GUI source of truth."""
        return self.runtime.agent

    @property
    def phase(self) -> str:
        return "active" if self.runtime.session.count() != 0 else "hero"

    @property
    def status(self) -> str:
        if self.closed:
            return "Closed"
        if self.is_submitting():
            return "Running"
        reason = self.runtime.session.projection().last_turn_reason
        if reason != "" and reason != "completed":
            return reason
        return "Ready"

    def is_submitting(self) -> bool:
        return (
            self.submitting_agent is self.runtime.agent
            or self.runtime.session.active_turn != 0
        )

    def can_submit(self, text: str) -> bool:
        # Pinned input/machine.ts:460-476 suppresses locked and blank sends,
        # but passes the original draft, not its trimmed value, to the sink.
        return not self.closed and not self.is_submitting() and text.strip() != ""

    def new_session(self) -> None:
        if self.closed:
            raise RuntimeError("Harness GUI is closed")
        self.runtime.new_session("main")

    def submit(self, text: str) -> str:
        """Submit an explicit draft synchronously through the current agent.

        This is a state/runtime seam, not a native text-input or scheduling
        implementation. Reading the current session after the call prevents a
        replaced agent's eventual result from becoming the visible transcript.
        """
        if not self.can_submit(text):
            return ""
        agent = self.runtime.agent
        self.submitting_agent = agent
        try:
            return agent.run_turn(text)
        finally:
            if self.submitting_agent is agent:
                self.submitting_agent = None

    def submit_sample(self) -> str:
        """Compatibility fixture until the canonical editable composer is wired."""
        return self.submit("hello from pcc gui")

    def transcript(self):
        return self.runtime.session.derive_model_history()

    def render_model(self):
        """Return the canonical projection consumed by the drawing path."""
        return self.runtime.session.projection()

    def dispose(self) -> None:
        """Release runtime ownership once, including when teardown raises."""
        if self.closed:
            return
        self.closed = True
        self.runtime.dispose()

    def visible_regions(self):
        return [
            "sidebar",
            "session-navigation",
            "trajectory",
            "composer",
            "status",
            "settings",
        ]

    def visible_labels(self):
        labels = [
            "deepseek",
            "New Session",
            "Workspaces",
            "pcc",
            "Sessions",
            "Settings",
            self.status,
        ]
        if self.phase == "hero":
            labels += [
                "DeepSeek Harness",
                "Preview",
                "Choose workspace",
                "What can I help you build?",
            ]
        else:
            labels += [
                self.render_model().title,
                "Chat",
                "Trajectory",
            ]
            for message in self.render_model().messages:
                labels.append(message.content)
        return labels
