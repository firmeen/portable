from __future__ import annotations

import argparse
import os
import platform
import sys

from .catalog import PROGRAMS, PROGRAM_BY_ID
from .config import APP_NAME, APP_VERSION, LOG_FILE, Paths, SOFTWARE_ROOT
from .core.environment import (
    add_user_path, program_path_status, validate_program_paths,
    verify_commands, verify_user_path,
)
from .core.planner import resolve_install_plan
from .logging_utils import LOGGER, log
from .models import InstallResult, Priority, Program
from .ui import confirm_installation, interactive_menu


def validate_environment(*, interactive: bool = False) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows is required")

    architecture = platform.machine().lower()
    if architecture not in {"amd64", "x86_64", "x64"}:
        raise RuntimeError(f"Windows x64 is required. Detected: {platform.machine()}")

    if sys.version_info < (3, 10):
        raise RuntimeError(
            f"Python 3.10+ is required. Detected: {platform.python_version()}"
        )

    if interactive and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        raise RuntimeError("Interactive terminal is required")

    missing_path_contract = [program.id for program in PROGRAMS if not program.path_entries or not program.commands]
    if missing_path_contract:
        raise RuntimeError(
            "Permanent PATH metadata is missing for: "
            + ", ".join(missing_path_contract)
        )

    Paths().ensure()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="installer.py",
        description="Portable developer-tool installer for Windows without admin access.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {APP_VERSION}")
    parser.add_argument("--list", action="store_true", help="List available programs and exit")
    parser.add_argument(
        "--install",
        nargs="+",
        metavar="ID",
        help="Install one or more program IDs without opening the menu",
    )
    parser.add_argument(
        "--preset",
        choices=("essential", "recommended", "everything"),
        help="Install a predefined set of tools",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show the dependency plan without installing")
    parser.add_argument("--yes", action="store_true", help="Skip the final confirmation prompt")
    parser.add_argument("--repair-path", action="store_true", help="Repair User PATH for all installed tools without downloading")
    parser.add_argument("--no-color", action="store_true", help="Disable colors in the interactive menu")
    return parser


def list_programs() -> None:
    print(f"{APP_NAME} {APP_VERSION}\n")
    for ecosystem in dict.fromkeys(program.ecosystem for program in PROGRAMS):
        print(ecosystem)
        for program in PROGRAMS:
            if program.ecosystem != ecosystem:
                continue
            status = program_path_status(program, SOFTWARE_ROOT).lower()
            print(
                f"  {program.id:<12} {program.priority.value:<4} "
                f"{program.name:<22} {status}"
            )
        print()


def preset_ids(name: str) -> list[str]:
    if name == "essential":
        return [p.id for p in PROGRAMS if p.priority == Priority.CORE]
    if name == "recommended":
        return [p.id for p in PROGRAMS if p.priority != Priority.OPTIONAL]
    return [p.id for p in PROGRAMS]


def validate_ids(ids: list[str]) -> list[str]:
    unknown = [program_id for program_id in ids if program_id not in PROGRAM_BY_ID]
    if unknown:
        raise RuntimeError(
            "Unknown program ID(s): " + ", ".join(unknown) + ". Use --list to see valid IDs."
        )
    seen: set[str] = set()
    ordered: list[str] = []
    for program_id in ids:
        if program_id in seen:
            continue
        seen.add(program_id)
        ordered.append(program_id)
    return ordered


def plan_lines(plan: list[str], requested: set[str]) -> list[str]:
    lines: list[str] = []
    for index, program_id in enumerate(plan, 1):
        program = PROGRAM_BY_ID[program_id]
        source = "selected" if program_id in requested else "dependency"
        lines.append(f"{index:>2}. {program.name:<24} ({source})")
    return lines


def _register_permanent_path(program: Program) -> list[str]:
    paths = validate_program_paths(program, SOFTWARE_ROOT)
    add_user_path(*paths)
    return verify_commands(program, SOFTWARE_ROOT)


def repair_permanent_paths() -> int:
    """Repair all complete local tools in catalog order, without downloads."""
    ready: list[tuple[Program, tuple]] = []
    failures = 0
    before: dict[str, bool] = {}
    print("\nPERMANENT PATH AUDIT")
    for program in PROGRAMS:
        if not program.installed():
            if program_path_status(program, SOFTWARE_ROOT) == "INCOMPLETE":
                log("INCOMPLETE", program.name)
                failures += 1
            else:
                log("SKIPPED", f"{program.name}: not installed")
            continue
        try:
            paths = validate_program_paths(program, SOFTWARE_ROOT)
            try:
                verify_user_path(*paths)
                before[program.id] = True
            except RuntimeError:
                before[program.id] = False
            ready.append((program, paths))
        except (OSError, RuntimeError) as exc:
            log("FAILED", f"{program.name}: {exc}")
            failures += 1

    if ready:
        add_user_path(*(path for _, paths in ready for path in paths))
    for program, _ in ready:
        conflicts = verify_commands(program, SOFTWARE_ROOT)
        status = "ALREADY SET" if before[program.id] else "REPAIRED"
        if conflicts:
            log("CONFLICT", f"{program.name}: {status}; " + "; ".join(conflicts))
        else:
            log(status, program.name)
    print("PATH audit complete. Open a fresh terminal to use the new User PATH.")
    return 1 if failures else 0


def install_selected(selected: list[str]) -> int:
    plan, requested = resolve_install_plan(selected, PROGRAM_BY_ID)
    results: list[InstallResult] = []
    failed_ids: set[str] = set()

    print("=" * 86)
    print(f"{APP_NAME} v{APP_VERSION}")
    print("=" * 86)
    print(f"Install location : {SOFTWARE_ROOT}")
    print(f"Requested        : {len(requested)}")
    print(f"Install plan     : {len(plan)}")
    print()

    # Existing dependencies can be omitted by the planner. Refresh their PATH
    # (and every other installed tool) before running any installer.
    repair_permanent_paths()

    for position, program_id in enumerate(plan, 1):
        program = PROGRAM_BY_ID[program_id]
        failed_dependencies = [dep for dep in program.dependencies if dep in failed_ids]
        source = "REQUESTED" if program_id in requested else "DEPENDENCY"
        print("-" * 86)
        print(f"[{position}/{len(plan)}] {program.name} [{source}]")
        print("-" * 86)

        if failed_dependencies:
            detail = "Dependency failed: " + ", ".join(failed_dependencies)
            log("SKIPPED", detail)
            failed_ids.add(program_id)
            results.append(
                InstallResult(program_id, program.name, False, "SKIPPED", detail, program_id in requested)
            )
            print()
            continue

        try:
            detail = program.installer()
            conflicts = _register_permanent_path(program)
            detail = f"{detail} | User PATH: permanent"
            if conflicts:
                log("CONFLICT", f"{program.name}: " + "; ".join(conflicts))
                detail += " | PATH CONFLICT: " + "; ".join(conflicts)
            log("SUCCESS", f"{program.name}: {detail}")
            results.append(
                InstallResult(program_id, program.name, True, "OK", detail, program_id in requested)
            )
        except KeyboardInterrupt:
            log("CANCELLED", "Installation interrupted by user")
            raise
        except Exception as exc:
            failed_ids.add(program_id)
            log("FAILED", f"{program.name}: {exc}")
            results.append(
                InstallResult(program_id, program.name, False, "FAILED", str(exc), program_id in requested)
            )
        print()

    # Restore deterministic catalog precedence across all complete tools.
    # Report conflicts again after the final ordering is established.
    repair_permanent_paths()
    print("\n" + "=" * 86)
    print("INSTALLATION SUMMARY")
    print("=" * 86)
    failures = 0
    for result in results:
        source = "selected" if result.requested else "dependency"
        print(f"[{result.status:<7}] {result.name:<24} {source:<10} {result.detail}")
        if not result.success:
            failures += 1

    print(f"\nSuccessful : {len(results) - failures}")
    print(f"Failed     : {failures}")
    print(f"Log        : {LOG_FILE}")
    print("\nEvery successful tool is registered in permanent User PATH.")
    print("Open a new PowerShell window after installation to inherit the updated User PATH.")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        if args.repair_path:
            if args.list or args.install or args.preset or args.dry_run:
                raise RuntimeError("--repair-path must be used on its own")
            validate_environment(interactive=False)
            return repair_permanent_paths()

        if args.list:
            validate_environment(interactive=False)
            list_programs()
            return 0

        if args.install and args.preset:
            raise RuntimeError("Use either --install or --preset, not both")

        if args.install:
            validate_environment(interactive=False)
            selected = validate_ids(args.install)
        elif args.preset:
            validate_environment(interactive=False)
            selected = preset_ids(args.preset)
        else:
            validate_environment(interactive=True)
            selected = interactive_menu(PROGRAMS, color=not args.no_color)

        plan, requested = resolve_install_plan(selected, PROGRAM_BY_ID)
        lines = plan_lines(plan, requested)

        if args.dry_run:
            print("Installation plan (dry run)\n")
            print("\n".join(lines))
            return 0

        if not args.yes and not confirm_installation(lines):
            print("Cancelled safely. Nothing was installed.")
            return 130

        return install_selected(selected)

    except KeyboardInterrupt:
        print("\nCancelled safely.")
        LOGGER.info("User cancelled installer")
        return 130
    except Exception as exc:
        print(f"\n[FATAL] {exc}")
        print(f"See log for details: {LOG_FILE}")
        LOGGER.exception("Fatal installer error")
        return 1
