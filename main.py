import argparse
from pathlib import Path

from dotenv import load_dotenv

from control import Control


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the macAgentic harness")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("task", nargs="?", help="Task for the agent")
    source.add_argument("--spec", type=Path, help="Read the task from a spec file")
    parser.add_argument("--model", help="LiteLLM model name")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    if args.spec:
        task = args.spec.read_text().strip()
    else:
        task = args.task or input("Task: ").strip()

    if not task:
        raise SystemExit("A task or non-empty spec is required.")

    Control(Path.cwd(), model_name=args.model).start(task)


if __name__ == "__main__":
    main()
