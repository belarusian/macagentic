# macAgentic

An agent harness powered by [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent).

Run interactively:

```sh
make run
```

The harness maintains one conversation and alternates between `You:` and
`Agent:` turns. The agent can run bash commands when needed, but answers simple
questions directly. Enter `/exit`, `/quit`, or press Control-C to stop.

Run with a task or spec:

```sh
make run ARGS='"Fix the failing tests"'
make run ARGS="--spec specs/example.md"
```

Set `MSWEA_MODEL_NAME` in `.env` to select a different LiteLLM model.
