import argparse

from macagentic.ui.screenshot import capture_window_by_title


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture the macAgentic window")
    parser.add_argument("--title", default="macAgentic")
    parser.add_argument("--output", default="./debug_screenshot.png")
    args = parser.parse_args()
    if not capture_window_by_title(args.title, args.output):
        raise SystemExit(f"No visible window matching {args.title!r}")
    print(f"Screenshot saved to {args.output}")


if __name__ == "__main__":
    main()
