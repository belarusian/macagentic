import os
from pathlib import Path

import yaml
from minisweagent import package_dir
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.litellm_model import LitellmModel

SYSTEM_PROMPT = """You are an interactive coding assistant with access to a bash tool.
Answer the user's current message directly. Use bash only when it materially helps
answer the request; simple questions should not use tools. After using tools,
provide a final response without a tool call so control returns to the user.
"""


class ChatModel(LitellmModel):
    """Allow normal assistant responses as well as optional bash tool calls."""

    def _parse_actions(self, response) -> list[dict]:
        if not response.choices[0].message.tool_calls:
            return []
        return super()._parse_actions(response)


class Control:
    """Owns agent lifecycle and will coordinate additional workers later."""

    def __init__(self, workspace: Path, model_name: str | None = None) -> None:
        self.workspace = workspace.resolve()
        self.model_name = model_name or os.getenv("MSWEA_MODEL_NAME", "openai/gpt-5-mini")
        config = yaml.safe_load(
            (Path(package_dir) / "config" / "mini.yaml").read_text()
        )
        self.model = ChatModel(**(config["model"] | {"model_name": self.model_name}))
        self.environment = LocalEnvironment(
            **(config["environment"] | {"cwd": str(self.workspace)})
        )

    def start(self, first_message: str) -> None:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        user_message = first_message

        while True:
            messages.append({"role": "user", "content": user_message})
            self._run_agent_turn(messages)

            try:
                user_message = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return

            if user_message.lower() in {"/exit", "/quit"}:
                return
            if not user_message:
                continue

    def _run_agent_turn(self, messages: list[dict]) -> None:
        for _ in range(20):
            response = self.model.query(messages)
            messages.append(response)

            if content := response.get("content"):
                print(f"\nAgent: {content}")

            actions = response["extra"]["actions"]
            if not actions:
                return

            outputs = []
            for action in actions:
                output = self.environment.execute(action)
                outputs.append(output)

            messages.extend(
                self.model.format_observation_messages(response, outputs)
            )

        raise RuntimeError("Agent exceeded 20 consecutive tool-call rounds.")
