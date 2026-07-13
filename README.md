# macAgentic

An agent harness powered by [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent).

Run in the terminal:

```sh
make run
```

The harness maintains one conversation and alternates between `You:` and
`Agent:` turns. The agent can run bash commands when needed, but answers simple
questions directly. Press Control-C to interrupt the current run and return to
the prompt; enter `/exit` or `/quit` to stop.

Start the optional native PyObjC UI:

```sh
make runui
# equivalent to:
uv run --frozen python -m macagentic --ui
```

The UI is a passive renderer over the agent's in-memory Markdown output. The
agent does not depend on the UI, and the headless path does not import PyObjC.
Press Option-Space globally to hide or reopen the UI.

Pass `--tooloutput` to either mode to include bash commands and their output:

```sh
make run ARGS="--tooloutput"
make runui ARGS="--tooloutput"
```

Run with an inline task or a task file from `tasks/`:

```sh
make run ARGS='"Fix the failing tests"'
make run ARGS="--task-file tasks/example.md"
make runui ARGS="--task-file tasks/example.md"
```

Append custom system instructions without changing the default prompt:

```sh
make run ARGS="--instructions path/to/instructions.md"
make runui ARGS="--instructions path/to/instructions.md"
```

The base prompt lives in `macagentic/agent/prompts/default.md`. With no
`--instructions` argument, loading it preserves the existing behavior.

Project defaults are loaded from `config/config.toml`. Override any value in
`~/.config/macagentic/config.toml`; user values win recursively. Supported
values are `model`, `openai_api_key`, and `custom_prompt`.

Capture a completed UI render for debugging:

```sh
make debug-render QUERY="Show a Markdown table"
```

Use `--model` for a one-run model override. `OPENAI_API_KEY` in `.env` remains
supported when `openai_api_key` is not set in TOML.
