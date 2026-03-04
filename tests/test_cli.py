from __future__ import annotations

from importlib import import_module

parse_args = import_module("offline_mirror.cli").parse_args


def test_parse_args_no_progress_defaults_to_false() -> None:
    args = parse_args([])
    assert not args.no_progress


def test_parse_args_no_progress_flag_sets_true() -> None:
    args = parse_args(["--no-progress"])
    assert args.no_progress
