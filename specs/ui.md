# macOS UI

## Core Principle

**The UI is a passive renderer for the agent.**

The agent must run identically with or without the UI. It writes user and
assistant text to a plain Markdown stream. When `--ui` is active, the UI reads
that stream and renders it. Without `--ui`, the same agent uses terminal input
and output.

The agent must never import, own, inspect, or otherwise depend on UI code.

There are only two permitted exceptions:

1. After writing text, the agent may trigger an optional repaint callback.
2. When blocked, the agent may ask the UI for permission or clarification.

If no UI is attached, repaint is a no-op and permission or clarification uses
the terminal.

## Transcript

Each UI tab owns an in-memory, file-like Markdown stream. It is not a file on
the macOS filesystem and is not persisted.

The stream contains only display text in order:

- user text
- assistant text

It never contains tool calls, tool output, model payloads, reasoning metadata,
agent steps, status events, or debug records.

The UI renders the stream as one Markdown document. It does not reconstruct
messages, query the agent, or maintain a second conversation representation.

## Starting

The default command remains headless:

```sh
python -m macagentic
```

The UI is opt-in:

```sh
python -m macagentic --ui
make runui
```

PyObjC must not be imported on the headless path.

## Window

The UI follows the macLLM layout:

- native Cocoa UI implemented with PyObjC
- fixed 640-point content width
- 48-point top bar
- 24-point tab strip
- scrollable transcript
- 90-point multiline input
- rounded floating panel
- height grows with content up to 90% of the screen

As in macLLM, the logical window width is 648 points and the transparent Cocoa
frame adds 12 points on each side, producing a 672-point outer frame. The empty
window is 174 points high before the same frame margin, producing a 198-point
outer frame.

The top-left uses the llama logo copied from macLLM. The top bar may show the
selected model, but does not show sources, tokens, steps, activity, or debug
controls.

The Cocoa event loop stays on the main thread. Agent work runs outside the main
thread. Repaint requests from agent threads are dispatched asynchronously to
the main thread.

## Tabs

Tabs are session-only. Closing the application discards all tabs and streams.

Tabs match macLLM behavior:

- newest tab appears on the left
- up to five tabs are visible
- tabs can be created, selected, and closed
- each tab preserves its unfinished input draft
- each tab has an independent agent conversation
- agent work may continue in a background tab
- input submitted while a tab is running is queued for that tab

Tab titles are a short truncation of the first user request. A running tab may
show a visual running indicator. These are UI-local details and are not part of
the transcript.

## Input

- Return submits
- Shift-Return inserts a newline
- Escape closes the window
- Command-N creates a tab
- Command-W closes the active tab
- Command-Return interrupts and then submits the current input
- Control-C interrupts without submitting input

Normal UI input enters the same control path used by terminal input. The UI
must not alter agent behavior.

Permission and clarification use two narrow optional callbacks. They are not a
general UI API, event bus, broker, or plugin surface.

## Markdown

Assistant and user text are rendered with the Markdown renderer adapted from
macLLM. It supports:

- headings and paragraphs
- bold, italics, inline code, links, and bare text
- ordered and unordered lists
- tables
- fenced and indented code
- blockquotes
- copy links for code blocks and blockquotes
- collapse and expand for long blocks
- keyboard focus and copy for blocks

The renderer displays exactly the text in the transcript stream.

## Interrupts

Interrupts are cooperative. Each running tab has a cancel flag owned by the
agent control layer.

Cancellation is checked before and after model calls and tool execution.
Subprocess process groups should be terminated where possible. Python worker
threads must never be killed asynchronously.

An in-flight model call may not be cancellable. In that case its eventual
result is discarded and never written to the transcript. A run identifier
prevents output from an interrupted run from appearing after a newer run.

The UI invokes the same interrupt operation as terminal Control-C. The UI does
not add synthetic transcript text. If `Interrupted.` should appear, the control
layer writes it through the normal transcript path.

## Screenshot Instrumentation

The following macLLM instrumentation is copied or adapted:

- Quartz capture of a visible window by title
- a screenshot command-line entry point
- `--screenshot` capture after an initial task finishes
- `make debug-render QUERY="..."` for one-command debugging
- an in-process Cocoa test driver
- a test harness that manually advances the Cocoa run loop

Screenshot scenarios include:

- empty window
- short answer
- long Markdown response
- code and blockquote controls
- multiple tabs
- permission prompt
- clarification prompt
- interrupted run

## Acceptance

The UI satisfies this spec only if:

- deleting all UI code does not change headless agent behavior
- `python -m macagentic` does not import PyObjC
- the agent never holds a UI object
- the UI reads only the active transcript text
- hidden tool activity cannot appear in the rendered transcript
- closing the window does not stop background agent work
- the same permission, clarification, and interrupt semantics work headlessly

## Attribution

The layout, llama logo, Markdown behavior, and screenshot instrumentation are
adapted from [appenz/macLLM](https://github.com/appenz/macLLM), licensed under
Apache-2.0. Copied source files retain attribution in their module docstrings.
