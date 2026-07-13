import os
import signal
import threading
from pathlib import Path

from macagentic.agent.control import Control, load_system_prompt
from macagentic.agent.transcript import Transcript

EXPECTED_DEFAULT_PROMPT = """You are an interactive coding assistant with access to a bash tool.
Answer the user's current message directly. Use bash only when it materially helps
answer the request; simple questions should not use tools. After using tools,
provide a final response without a tool call so control returns to the user.

You have direct access to the local filesystem through bash. When the user asks
you to inspect, search, or summarize local files, use bash to do the work
yourself. Never claim that you cannot access those files or ask the user to run
commands for you. Do not modify files unless the user requests a change.
"""


class FakeModel:
    def query(self, _messages):
        return {
            "role": "assistant",
            "content": "The answer is **2**.",
            "extra": {"actions": []},
        }


class SignallingModel:
    def query(self, _messages):
        os.kill(os.getpid(), signal.SIGINT)


class BlockingModel:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def query(self, _messages):
        self.started.set()
        self.release.wait()
        return {
            "role": "assistant",
            "content": "Late response",
            "extra": {"actions": []},
        }


class ToolModel:
    def __init__(self) -> None:
        self.calls = 0

    def query(self, _messages):
        self.calls += 1
        if self.calls == 1:
            return {
                "role": "assistant",
                "content": None,
                "extra": {
                    "actions": [{"command": "printf 'hello\\n'"}],
                },
            }
        return {
            "role": "assistant",
            "content": "Done.",
            "extra": {"actions": []},
        }

    def format_observation_messages(self, _response, _outputs):
        return [{"role": "tool", "content": "hello"}]


class FakeEnvironment:
    def execute(self, _action):
        return {
            "output": "hello\n",
            "returncode": 0,
            "exception_info": "",
        }

    def interrupt(self):
        return


def test_default_prompt_is_unchanged() -> None:
    assert load_system_prompt() == EXPECTED_DEFAULT_PROMPT


def test_custom_instructions_are_appended_to_default_prompt() -> None:
    prompt = load_system_prompt("Always answer briefly.")

    assert prompt.startswith(EXPECTED_DEFAULT_PROMPT.rstrip())
    assert prompt.endswith(
        "## Custom Instructions\n\nAlways answer briefly.\n"
    )


def test_control_writes_only_conversation_text() -> None:
    transcript = Transcript()
    outputs = []
    control = Control(
        Path.cwd(),
        transcript=transcript,
        on_output=outputs.append,
    )
    control.model = FakeModel()

    control.run_turn("What is 1+1?")

    assert transcript.getvalue() == (
        "**You:** What is 1+1?\n\nThe answer is **2**.\n\n"
    )
    assert outputs == ["The answer is **2**."]
    assert "tool" not in transcript.getvalue().lower()


def test_console_ctrl_c_interrupts_and_returns_to_prompt(
    monkeypatch,
    capsys,
) -> None:
    transcript = Transcript()
    control = Control(Path.cwd(), transcript=transcript)
    control.model = SignallingModel()
    monkeypatch.setattr("builtins.input", lambda _prompt: "/exit")

    control.start("Long-running request")

    assert "Interrupted." in capsys.readouterr().out
    assert transcript.getvalue().endswith("Interrupted.\n\n")


def test_interrupt_releases_turn_blocked_on_model_query() -> None:
    control = Control(Path.cwd())
    model = BlockingModel()
    control.model = model
    turn = threading.Thread(target=control.run_turn, args=("Wait",))
    turn.start()
    assert model.started.wait(1)

    control.interrupt()
    turn.join(1)
    model.release.set()

    assert not turn.is_alive()
    assert "Late response" not in control.transcript.getvalue()


def test_tool_output_is_visible_only_when_enabled() -> None:
    hidden = Control(Path.cwd())
    hidden.model = ToolModel()
    hidden.environment = FakeEnvironment()
    hidden.run_turn("Run it")
    assert "**Tool:**" not in hidden.transcript.getvalue()

    visible = []
    control = Control(
        Path.cwd(),
        show_tool_output=True,
        on_tool_output=visible.append,
    )
    control.model = ToolModel()
    control.environment = FakeEnvironment()

    control.run_turn("Run it")

    assert "**Tool:** `printf 'hello\\n'` (exit 0)" in control.transcript.getvalue()
    assert "```text\nhello\n```" in control.transcript.getvalue()
    assert visible and visible[0].startswith("**Tool:**")
