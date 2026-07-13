from pathlib import Path
import threading

import pytest

from macagentic.agent.transcript import Transcript
from macagentic.ui.testing import UITestDriver


class FakeControl:
    def __init__(self, _workspace, **kwargs):
        self.transcript = kwargs.get("transcript") or Transcript()
        self.interrupted = False

    def run_turn(self, text: str) -> None:
        self.transcript.write(f"**You:** {text}\n\n")
        self.transcript.write("# Agent reply\n\nRendered **Markdown**.\n")

    def interrupt(self) -> None:
        self.interrupted = True


@pytest.mark.uitest
def test_ui_passively_renders_transcript(monkeypatch) -> None:
    monkeypatch.setattr("macagentic.ui.core.Control", FakeControl)
    from macagentic.ui.core import MacAgenticUI

    ui = MacAgenticUI(Path.cwd())
    ui.start(dont_run_app=True)
    driver = UITestDriver(ui)

    assert ui.window.frame().size.width == 672
    assert ui.window.frame().size.height == 198
    assert ui.app.applicationIconImage().size().width > 0

    driver.type_text("copy me")
    ui.input_field.setSelectedRange_((0, 7))
    driver.press_cmd("c")
    assert driver.clipboard() == "copy me"
    ui.input_field.setString_("")
    driver.press_cmd("v")
    assert driver.input_text() == "copy me"
    ui.input_field.setString_("")

    driver.type_text("hello")
    driver.press_return()
    assert driver.wait_for(lambda: "Agent reply" in driver.conversation_text())
    assert "Rendered Markdown" in driver.conversation_text()
    assert driver.tab_count() == 1

    release = threading.Event()
    running = threading.Thread(target=release.wait)
    running.start()
    ui.active_tab.thread = running
    ui._handle_console_interrupt(None, None)
    assert ui.active_tab.control.interrupted
    release.set()
    running.join()
    ui.active_tab.thread = None

    ui.close_window()
    assert ui.window is None
    ui.app_delegate.applicationShouldHandleReopen_hasVisibleWindows_(
        ui.app,
        False,
    )
    assert ui.window is not None

    ui.hotkey_pressed()
    assert ui.window is None
    ui.hotkey_pressed()
    assert ui.window is not None
    ui.close_window()
