"""Native Cocoa Markdown rendering adapted from appenz/macLLM (Apache-2.0)."""

from hashlib import sha1

from Cocoa import (
    NSAttributedString,
    NSFont,
    NSFontAttributeName,
    NSFontManager,
    NSForegroundColorAttributeName,
    NSLinkAttributeName,
    NSParagraphStyleAttributeName,
)
from Foundation import NSMutableAttributedString, NSMutableParagraphStyle
from AppKit import NSTextTab
from markdown_it import MarkdownIt

FONT_SIZE = 14.0
LINE_HEIGHT = FONT_SIZE * 1.2
LIST_ITEM_SPACING = FONT_SIZE * 0.25
LIST_BASE_INDENT = 14.0
INDENT_PER_LEVEL = 16.0
BULLET_TEXT_OFFSET = 14.0
CODE_FONT_SIZE = 12.0
COLLAPSE_AFTER_LINES = 20
COLLAPSE_PREVIEW_LINES = 5


def _attributed(text, *, color, font=None, link=None, style=None):
    attrs = {
        NSForegroundColorAttributeName: color,
        NSFontAttributeName: font or NSFont.systemFontOfSize_(FONT_SIZE),
    }
    if link is not None:
        attrs[NSLinkAttributeName] = link
    if style is not None:
        attrs[NSParagraphStyleAttributeName] = style
    return NSAttributedString.alloc().initWithString_attributes_(text, attrs)


def _paragraph_style(indent=0.0):
    style = NSMutableParagraphStyle.alloc().init()
    style.setMinimumLineHeight_(LINE_HEIGHT)
    style.setMaximumLineHeight_(LINE_HEIGHT)
    style.setFirstLineHeadIndent_(indent)
    style.setHeadIndent_(indent)
    return style


class MarkdownRenderer:
    """Render Markdown into one NSAttributedString and track interactive blocks."""

    def __init__(self) -> None:
        self._parser = MarkdownIt("commonmark").enable("table")
        self._blocks: dict[str, str] = {}
        self._expanded: set[str] = set()
        self.block_ranges: list[tuple[str, int, int]] = []

    def render(self, text: str, color) -> NSMutableAttributedString:
        tokens = self._parser.parse(text.rstrip())
        result = NSMutableAttributedString.alloc().init()
        self._blocks = {}
        self.block_ranges = []

        i = 0
        need_gap = False
        after_list = False
        while i < len(tokens):
            token = tokens[i]

            if token.type in {"bullet_list_open", "ordered_list_open"}:
                if need_gap and result.length():
                    result.appendAttributedString_(
                        NSAttributedString.alloc().initWithString_("\n")
                    )
                list_text, i = self._render_list(tokens, i, color)
                result.appendAttributedString_(list_text)
                need_gap = True
                after_list = True
                continue

            if token.type in {"fence", "code_block"}:
                if need_gap and result.length():
                    result.appendAttributedString_(
                        NSAttributedString.alloc().initWithString_(
                            "\n" if after_list else "\n\n"
                        )
                    )
                after_list = False
                self._append_collapsible_block(
                    result,
                    (token.content or "").rstrip("\n"),
                    color,
                    monospace=True,
                )
                need_gap = True
                i += 1
                continue

            if token.type == "blockquote_open":
                content = []
                i += 1
                while i < len(tokens) and tokens[i].type != "blockquote_close":
                    if tokens[i].type == "inline":
                        content.append(tokens[i].content or "")
                    i += 1
                if need_gap and result.length():
                    result.appendAttributedString_(
                        NSAttributedString.alloc().initWithString_(
                            "\n" if after_list else "\n\n"
                        )
                    )
                after_list = False
                self._append_collapsible_block(
                    result,
                    "\n".join(content).strip(),
                    color.colorWithAlphaComponent_(0.75),
                    monospace=False,
                )
                need_gap = True
                i += 1
                continue

            if token.type == "table_open":
                table_text, i = self._render_table(tokens, i)
                if need_gap and result.length():
                    result.appendAttributedString_(
                        NSAttributedString.alloc().initWithString_(
                            "\n" if after_list else "\n\n"
                        )
                    )
                after_list = False
                style = _paragraph_style(8.0)
                result.appendAttributedString_(
                    _attributed(
                        table_text,
                        color=color,
                        font=NSFont.monospacedSystemFontOfSize_weight_(
                            11.5, 0.0
                        ),
                        style=style,
                    )
                )
                need_gap = True
                continue

            if token.type in {"heading_open", "paragraph_open"}:
                close_type = (
                    "heading_close"
                    if token.type == "heading_open"
                    else "paragraph_close"
                )
                if need_gap and result.length():
                    result.appendAttributedString_(
                        NSAttributedString.alloc().initWithString_(
                            "\n" if after_list else "\n\n"
                        )
                    )
                after_list = False
                heading_level = 0
                if token.type == "heading_open" and token.tag[1:].isdigit():
                    heading_level = int(token.tag[1:])
                i += 1
                while i < len(tokens) and tokens[i].type != close_type:
                    if tokens[i].type == "inline":
                        font = None
                        if heading_level:
                            size = 16.0 if heading_level == 1 else 15.0
                            font = NSFont.boldSystemFontOfSize_(size)
                        result.appendAttributedString_(
                            self._render_inline(
                                tokens[i].children or [],
                                color,
                                base_font=font,
                            )
                        )
                    i += 1
                need_gap = True
                i += 1
                continue

            i += 1

        return result

    def block_content(self, block_id: str) -> str | None:
        return self._blocks.get(block_id)

    def toggle_block(self, block_id: str) -> None:
        if block_id in self._expanded:
            self._expanded.remove(block_id)
        else:
            self._expanded.add(block_id)

    @staticmethod
    def _has_following_list_item(tokens, start: int, close_type: str) -> bool:
        while start < len(tokens) and tokens[start].type != close_type:
            if tokens[start].type == "list_item_open":
                return True
            start += 1
        return False

    @staticmethod
    def _list_item_style(indent: float, *, is_last: bool):
        content_column = indent + BULLET_TEXT_OFFSET
        style = NSMutableParagraphStyle.alloc().init()
        style.setFirstLineHeadIndent_(indent)
        style.setHeadIndent_(content_column)
        style.setTabStops_([])
        tab = NSTextTab.alloc().initWithTextAlignment_location_options_(
            0,
            content_column,
            {},
        )
        style.setTabStops_([tab])
        style.setDefaultTabInterval_(BULLET_TEXT_OFFSET)
        style.setMinimumLineHeight_(LINE_HEIGHT)
        style.setMaximumLineHeight_(LINE_HEIGHT)
        if not is_last:
            style.setParagraphSpacing_(LIST_ITEM_SPACING)
        return style

    def _render_list(self, tokens, start: int, color, depth: int = 0):
        font = NSFont.systemFontOfSize_(FONT_SIZE)
        result = NSMutableAttributedString.alloc().init()
        ordered = tokens[start].type == "ordered_list_open"
        close_type = (
            "ordered_list_close" if ordered else "bullet_list_close"
        )
        indent = LIST_BASE_INDENT + depth * INDENT_PER_LEVEL
        item_number = 0
        first_item = True
        i = start + 1

        while i < len(tokens) and tokens[i].type != close_type:
            if tokens[i].type != "list_item_open":
                i += 1
                continue

            item_number += 1
            i += 1
            if not first_item:
                result.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_("\n")
                )

            has_following = self._has_following_list_item(
                tokens,
                i + 1,
                close_type,
            )
            is_first = first_item
            style = self._list_item_style(
                indent,
                is_last=not has_following,
            )
            if depth == 0 and is_first:
                style.setParagraphSpacingBefore_(LIST_ITEM_SPACING)
            if depth == 0 and not has_following:
                style.setParagraphSpacing_(LIST_ITEM_SPACING)
            first_item = False
            item_line = NSMutableAttributedString.alloc().init()
            prefix = f"{item_number}.\t" if ordered else "•\t"
            item_line.appendAttributedString_(
                _attributed(prefix, color=color, font=font)
            )
            nested = NSMutableAttributedString.alloc().init()

            while i < len(tokens) and tokens[i].type != "list_item_close":
                if tokens[i].type == "paragraph_open":
                    i += 1
                    while (
                        i < len(tokens)
                        and tokens[i].type != "paragraph_close"
                    ):
                        if tokens[i].type == "inline":
                            item_line.appendAttributedString_(
                                self._render_inline(
                                    tokens[i].children or [],
                                    color,
                                    base_font=font,
                                )
                            )
                        i += 1
                    i += 1
                elif tokens[i].type in {
                    "bullet_list_open",
                    "ordered_list_open",
                }:
                    nested_list, i = self._render_list(
                        tokens,
                        i,
                        color,
                        depth + 1,
                    )
                    nested.appendAttributedString_(
                        NSAttributedString.alloc().initWithString_("\n")
                    )
                    nested.appendAttributedString_(nested_list)
                else:
                    i += 1

            i += 1
            item_line.addAttribute_value_range_(
                NSParagraphStyleAttributeName,
                style,
                (0, item_line.length()),
            )
            result.appendAttributedString_(item_line)
            if nested.length() > 0:
                result.appendAttributedString_(nested)

        return result, i + 1

    def _render_inline(self, children, color, base_font=None):
        result = NSMutableAttributedString.alloc().init()
        bold = False
        italic = False
        link = None
        for child in children:
            if child.type == "strong_open":
                bold = True
                continue
            if child.type == "strong_close":
                bold = False
                continue
            if child.type == "em_open":
                italic = True
                continue
            if child.type == "em_close":
                italic = False
                continue
            if child.type == "link_open":
                link = child.attrGet("href")
                continue
            if child.type == "link_close":
                link = None
                continue
            if child.type in {"softbreak", "hardbreak"}:
                result.appendAttributedString_(
                    NSAttributedString.alloc().initWithString_("\n")
                )
                continue

            content = child.content or ""
            if not content:
                continue
            if child.type == "code_inline":
                font = NSFont.monospacedSystemFontOfSize_weight_(
                    CODE_FONT_SIZE, 0.0
                )
            elif base_font is not None:
                font = base_font
            elif bold:
                font = NSFont.boldSystemFontOfSize_(FONT_SIZE)
            elif italic:
                font = NSFontManager.sharedFontManager().convertFont_toHaveTrait_(
                    NSFont.systemFontOfSize_(FONT_SIZE), 1
                )
            else:
                font = NSFont.systemFontOfSize_(FONT_SIZE)
            result.appendAttributedString_(
                _attributed(
                    content,
                    color=color,
                    font=font,
                    link=link,
                    style=_paragraph_style(),
                )
            )
        return result

    def _append_collapsible_block(
        self,
        result,
        content: str,
        color,
        *,
        monospace: bool,
    ) -> None:
        block_id = sha1(content.encode("utf-8")).hexdigest()[:12]
        self._blocks[block_id] = content
        lines = content.splitlines() or [""]
        collapsed = (
            len(lines) > COLLAPSE_AFTER_LINES
            and block_id not in self._expanded
        )
        shown = "\n".join(lines[:COLLAPSE_PREVIEW_LINES]) if collapsed else content
        start = result.length()
        font = (
            NSFont.monospacedSystemFontOfSize_weight_(CODE_FONT_SIZE, 0.0)
            if monospace
            else NSFont.systemFontOfSize_(CODE_FONT_SIZE)
        )
        result.appendAttributedString_(
            _attributed(
                shown,
                color=color,
                font=font,
                style=_paragraph_style(8.0),
            )
        )
        if len(lines) > COLLAPSE_AFTER_LINES:
            if collapsed:
                label = f"\n  ▸ {len(lines) - COLLAPSE_PREVIEW_LINES} more lines"
            else:
                label = "\n  ▾ collapse"
            result.appendAttributedString_(
                _attributed(
                    label,
                    color=color.colorWithAlphaComponent_(0.45),
                    font=NSFont.systemFontOfSize_(10.0),
                    link=f"macagentic://toggle/{block_id}",
                )
            )
        result.appendAttributedString_(
            _attributed(
                "\n  [copy]",
                color=color.colorWithAlphaComponent_(0.45),
                font=NSFont.systemFontOfSize_(10.0),
                link=f"macagentic://copy/{block_id}",
            )
        )
        self.block_ranges.append(
            (block_id, start, result.length() - start)
        )

    def _render_table(self, tokens, start: int) -> tuple[str, int]:
        rows: list[list[str]] = []
        row: list[str] | None = None
        cell_parts: list[str] | None = None
        i = start + 1
        while i < len(tokens) and tokens[i].type != "table_close":
            token = tokens[i]
            if token.type == "tr_open":
                row = []
            elif token.type == "tr_close" and row is not None:
                rows.append(row)
                row = None
            elif token.type in {"th_open", "td_open"}:
                cell_parts = []
            elif token.type in {"th_close", "td_close"}:
                if row is not None and cell_parts is not None:
                    row.append("".join(cell_parts).strip())
                cell_parts = None
            elif token.type == "inline" and cell_parts is not None:
                cell_parts.append(token.content or "")
            i += 1

        if not rows:
            return "", i + 1
        columns = max(len(row) for row in rows)
        widths = [
            max(
                len(row[column]) if column < len(row) else 0
                for row in rows
            )
            for column in range(columns)
        ]
        rendered = []
        for index, values in enumerate(rows):
            padded = [
                (values[column] if column < len(values) else "").ljust(
                    widths[column]
                )
                for column in range(columns)
            ]
            rendered.append("  ".join(padded).rstrip())
            if index == 0 and len(rows) > 1:
                rendered.append(
                    "  ".join("─" * width for width in widths).rstrip()
                )
        return "\n".join(rendered), i + 1
