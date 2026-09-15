from __future__ import annotations

import ctypes
import os
import shutil
import sys
from dataclasses import dataclass

from .catalog import ECOSYSTEM_ORDER
from .config import APP_NAME, APP_VERSION, SOFTWARE_ROOT
from .models import Priority, Program

ESC = "\x1b["
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
GREEN = f"{ESC}32m"
YELLOW = f"{ESC}33m"
MAGENTA = f"{ESC}35m"
CYAN = f"{ESC}36m"
CLEAR_SCREEN = f"{ESC}2J"
CLEAR_LINE = f"{ESC}2K"
HOME = f"{ESC}H"
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
ALT_SCREEN_ON = f"{ESC}?1049h"
ALT_SCREEN_OFF = f"{ESC}?1049l"
INSTALL_TARGET = "__INSTALL__"


def enable_virtual_terminal() -> bool:
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


def style(text: str, code: str, enabled: bool) -> str:
    return f"{code}{text}{RESET}" if enabled else text


class TerminalRenderer:
    """Diff-based renderer that avoids full-screen flicker on every key press."""

    def __init__(self, *, color: bool = True) -> None:
        self.ansi = False
        self.color_requested = color
        self.previous_lines: list[str] = []
        self.previous_size: tuple[int, int] | None = None

    @property
    def color(self) -> bool:
        return self.ansi and self.color_requested

    def __enter__(self) -> "TerminalRenderer":
        self.ansi = enable_virtual_terminal()
        if self.ansi:
            sys.stdout.write(ALT_SCREEN_ON + HIDE_CURSOR + CLEAR_SCREEN + HOME)
            sys.stdout.flush()
        else:
            os.system("cls")
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.ansi:
            sys.stdout.write(RESET + SHOW_CURSOR + ALT_SCREEN_OFF)
            sys.stdout.flush()

    def paint(self, lines: list[str]) -> None:
        if not self.ansi:
            os.system("cls")
            print("\n".join(lines))
            return

        terminal = shutil.get_terminal_size(fallback=(110, 40))
        size = (terminal.columns, terminal.lines)
        if size != self.previous_size:
            sys.stdout.write(CLEAR_SCREEN + HOME)
            self.previous_lines = []
            self.previous_size = size

        total = max(len(lines), len(self.previous_lines))
        output: list[str] = []
        for index in range(total):
            new_line = lines[index] if index < len(lines) else ""
            old_line = self.previous_lines[index] if index < len(self.previous_lines) else None
            if new_line == old_line:
                continue
            output.append(f"{ESC}{index + 1};1H{CLEAR_LINE}{new_line}")

        if output:
            sys.stdout.write("".join(output))
            sys.stdout.flush()
        self.previous_lines = lines.copy()


@dataclass(frozen=True)
class MenuRow:
    text: str
    target: str | None = None


def _priority_label(priority: Priority, color: bool) -> str:
    if priority == Priority.CORE:
        return style("ESSENTIAL", BOLD + GREEN, color)
    if priority == Priority.RECOMMENDED:
        return style("RECOMMEND", CYAN, color)
    return style("OPTIONAL ", DIM, color)


def _status_label(program: Program, color: bool) -> str:
    if program.installed():
        return style("INSTALLED", GREEN, color)
    return style("AVAILABLE", DIM, color)


def _menu_rows(
    programs: list[Program],
    active: str,
    selected: set[str],
    *,
    color: bool,
) -> list[MenuRow]:
    rows: list[MenuRow] = []
    for group_index, ecosystem in enumerate(ECOSYSTEM_ORDER):
        grouped = [p for p in programs if p.ecosystem == ecosystem]
        if not grouped:
            continue
        if group_index:
            rows.append(MenuRow(""))
        rows.append(MenuRow(style(f"  {ecosystem}", BOLD + MAGENTA, color)))

        for program in grouped:
            active_row = program.id == active
            selected_row = program.id in selected
            pointer = ">" if active_row else " "
            checkbox = "[x]" if selected_row else "[ ]"
            line = (
                f" {pointer} {checkbox} "
                f"[{_priority_label(program.priority, color)}] "
                f"{program.name:<22} "
                f"{program.description:<27} "
                f"{_status_label(program, color)}"
            )
            if active_row:
                line = style(line, BOLD + CYAN, color)
            rows.append(MenuRow(line, program.id))

    rows.append(MenuRow(""))
    install_active = active == INSTALL_TARGET
    prefix = " > " if install_active else "   "
    install_line = f"{prefix}[ INSTALL SELECTED : {len(selected)} ]"
    if install_active:
        install_line = style(
            install_line,
            BOLD + (GREEN if selected else YELLOW),
            color,
        )
    rows.append(MenuRow(install_line, INSTALL_TARGET))
    return rows


def _frame(
    programs: list[Program],
    active: str,
    selected: set[str],
    scroll: int,
    *,
    color: bool,
) -> tuple[list[str], int]:
    terminal = shutil.get_terminal_size(fallback=(110, 40))
    height = max(terminal.lines, 20)
    rows = _menu_rows(programs, active, selected, color=color)
    active_row = next((i for i, row in enumerate(rows) if row.target == active), 0)

    header = [
        "=" * 96,
        "  " + style(APP_NAME, BOLD + CYAN, color) + f"   v{APP_VERSION}",
        "=" * 96,
        f"  Install location : {SOFTWARE_ROOT}",
        "  Select           : ENTER or SPACE     Move: UP/DOWN     Install: I",
        "  Quick setup      : 1 Essentials      2 Recommended      3 Everything",
        "  Clear selection  : C                 Exit: Q / ESC / CTRL+C",
        "",
    ]
    footer_height = 4
    body_height = max(6, height - len(header) - footer_height)
    margin = 2

    if active_row < scroll + margin:
        scroll = max(0, active_row - margin)
    if active_row >= scroll + body_height - margin:
        scroll = active_row - body_height + margin + 1
    scroll = max(0, min(scroll, max(0, len(rows) - body_height)))

    visible = rows[scroll : scroll + body_height]
    body = [row.text for row in visible]
    body.extend([""] * (body_height - len(body)))

    above = scroll > 0
    below = scroll + body_height < len(rows)
    more = "More items above / below" if above and below else "More items above" if above else "More items below" if below else ""
    footer = [
        "",
        "-" * 96,
        f"  Selected: {len(selected):<5} {more}",
        "-" * 96,
    ]
    return header + body + footer, scroll


def _preset(programs: list[Program], mode: str) -> set[str]:
    if mode == "essential":
        return {p.id for p in programs if p.priority == Priority.CORE}
    if mode == "recommended":
        return {p.id for p in programs if p.priority != Priority.OPTIONAL}
    if mode == "everything":
        return {p.id for p in programs}
    return set()


def interactive_menu(programs: list[Program], *, color: bool = True) -> list[str]:
    if os.name != "nt":
        raise RuntimeError("Interactive menu currently requires Windows")

    import msvcrt

    targets = [program.id for program in programs] + [INSTALL_TARGET]
    cursor = 0
    selected: set[str] = set()
    scroll = 0

    with TerminalRenderer(color=color) as terminal:
        while True:
            active = targets[cursor]
            frame, scroll = _frame(
                programs,
                active,
                selected,
                scroll,
                color=terminal.color,
            )
            terminal.paint(frame)
            key = msvcrt.getwch()

            if key == "\x03":
                raise KeyboardInterrupt

            if key in {"\x00", "\xe0"}:
                extended = msvcrt.getwch()
                if extended == "H":
                    cursor = (cursor - 1) % len(targets)
                elif extended == "P":
                    cursor = (cursor + 1) % len(targets)
                elif extended == "G":
                    cursor = 0
                elif extended == "O":
                    cursor = len(targets) - 1
                elif extended == "I":
                    cursor = max(0, cursor - 5)
                elif extended == "Q":
                    cursor = min(len(targets) - 1, cursor + 5)
                continue

            if key.lower() == "q" or key == "\x1b":
                raise KeyboardInterrupt
            if key == "1":
                selected = _preset(programs, "essential")
                continue
            if key == "2":
                selected = _preset(programs, "recommended")
                continue
            if key == "3":
                selected = _preset(programs, "everything")
                continue
            if key.lower() == "c":
                selected.clear()
                continue
            if key.lower() == "i":
                cursor = len(targets) - 1
                continue

            if key == " " and active != INSTALL_TARGET:
                selected.symmetric_difference_update({active})
                continue

            if key == "\r":
                if active == INSTALL_TARGET:
                    if selected:
                        return [p.id for p in programs if p.id in selected]
                    continue
                selected.symmetric_difference_update({active})
                cursor = min(cursor + 1, len(targets) - 1)


def confirm_installation(lines: list[str]) -> bool:
    print("\nInstallation plan")
    print("=" * 72)
    for line in lines:
        print(f"  {line}")
    print("=" * 72)
    try:
        answer = input("Proceed with installation? [Y/n]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False
    return answer in {"", "y", "yes"}
