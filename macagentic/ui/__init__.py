from pathlib import Path


def run_ui(
    workspace: Path,
    *,
    model_name: str | None = None,
    initial_task: str | None = None,
    screenshot_path: Path | None = None,
    custom_instructions: str | None = None,
    tool_instructions: str | None = None,
    show_tool_output: bool = False,
) -> None:
    from macagentic.ui.core import MacAgenticUI

    MacAgenticUI(
        workspace,
        model_name=model_name,
        initial_task=initial_task,
        screenshot_path=screenshot_path,
        custom_instructions=custom_instructions,
        tool_instructions=tool_instructions,
        show_tool_output=show_tool_output,
    ).start()


__all__ = ["run_ui"]
