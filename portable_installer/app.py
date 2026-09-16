from __future__ import annotations

import argparse
import os
import platform
import sys

from .catalog import PROGRAMS, PROGRAM_BY_ID
from .config import APP_NAME, APP_VERSION, LOG_FILE, Paths, SOFTWARE_ROOT
from .core.environment import add_user_path
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

    missing_path_contract = [program.id for program in PROGRAMS if not program.path_entries]
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
    parser.add_argument("--no-color", action="store_true", help="Disable colors in the interactive menu")
    return parser


def list_programs() -> None:
    print(f"{APP_NAME} {APP_VERSION}\n")
    for ecosystem in dict.fromkeys(program.ecosystem for program in PROGRAMS):
        print(ecosystem)
        for program in PROGRAMS:
            if program.ecosystem != ecosystem:
                continue
            status = "installed" if program.installed() else "available"
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


def _register_permanent_path(program: Program) -> None:
    paths = tuple(SOFTWARE_ROOT / relative for relative in program.path_entries)
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(
            "Installer completed but permanent PATH target is missing: "
            + ", ".join(missing)
        )
    add_user_path(*paths)


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
            _register_permanent_path(program)
            detail = f"{detail} | User PATH: permanent"
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
