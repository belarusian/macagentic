import pytest

Cocoa = pytest.importorskip("Cocoa", reason="Cocoa renderer requires macOS")
from Cocoa import NSColor, NSParagraphStyleAttributeName

from macagentic.ui.markdown import MarkdownRenderer


def test_markdown_renders_blocks_and_tables() -> None:
    renderer = MarkdownRenderer()
    rendered = renderer.render(
        "# Heading\n\n"
        "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
        "```python\nprint('hello')\n```\n",
        NSColor.blackColor(),
    )

    text = str(rendered.string())
    assert "Heading" in text
    assert "A" in text and "2" in text
    assert "print('hello')" in text
    assert "[copy]" in text
    assert len(renderer.block_ranges) == 1


def test_markdown_lists_use_macllm_hanging_indents_and_spacing() -> None:
    renderer = MarkdownRenderer()
    rendered = renderer.render(
        "Intro\n\n"
        "- First item with enough text to wrap onto another line in the UI\n"
        "- Second item\n\n"
        "After",
        NSColor.blackColor(),
    )

    text = str(rendered.string())
    bullet = text.index("•")
    attributes, _ = rendered.attributesAtIndex_effectiveRange_(
        bullet,
        None,
    )
    style = attributes[NSParagraphStyleAttributeName]
    second_bullet = text.index("•", bullet + 1)
    second_attributes, _ = rendered.attributesAtIndex_effectiveRange_(
        second_bullet,
        None,
    )
    second_style = second_attributes[NSParagraphStyleAttributeName]

    assert style.firstLineHeadIndent() == 14.0
    assert style.headIndent() == 28.0
    assert style.paragraphSpacing() == 3.5
    assert style.paragraphSpacingBefore() == 3.5
    assert second_style.paragraphSpacing() == 3.5
    assert "Second item\nAfter" in text
