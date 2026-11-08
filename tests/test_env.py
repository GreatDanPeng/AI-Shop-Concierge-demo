"""Tests for the .env loader. It must never override the real environment or leak values."""
import logging
from pathlib import Path

import pytest

import app
from app.env import DEFAULT_ENV_PATH, load_env_file, parse_env


# ---------------------------------------------------------------- parsing
def test_plain_pairs_comments_and_blank_lines():
    text = "# a comment\n\nA=1\n  B = two  \n#C=3\n"
    assert parse_env(text) == {"A": "1", "B": "two"}


def test_export_prefix_is_accepted():
    assert parse_env("export A=1\nexport   B=2\n") == {"A": "1", "B": "2"}


def test_quotes_are_removed_and_inner_text_is_kept():
    text = "A='single  spaced'\nB=\"double # not a comment\"\nC='it=has=equals'\n"
    assert parse_env(text) == {"A": "single  spaced", "B": "double # not a comment",
                               "C": "it=has=equals"}


def test_an_unquoted_value_keeps_equals_signs_and_hashes_without_a_space_before_them():
    assert parse_env("A=abc=def\nB=abc#def\n") == {"A": "abc=def", "B": "abc#def"}


def test_an_inline_comment_after_a_space_is_dropped_for_unquoted_values():
    assert parse_env("A=value # trailing note\n") == {"A": "value"}


@pytest.mark.parametrize("line", ["no equals sign", "1BAD=x", "BAD KEY=x", "=novalue", "-X=1", "A.B=1"])
def test_malformed_lines_are_ignored(line):
    assert parse_env(f"{line}\nGOOD=1\n") == {"GOOD": "1"}


def test_windows_line_endings_and_a_byte_order_mark(tmp_path):
    path = tmp_path / ".env"
    path.write_bytes(b"\xef\xbb\xbfA=1\r\nB=2\r\n")
    environ = {}
    assert load_env_file(path, environ=environ) == ["A", "B"]
    assert environ == {"A": "1", "B": "2"}


def test_the_last_line_without_a_newline_is_read(tmp_path):
    path = tmp_path / ".env"
    path.write_text("A=1\nOPENROUTER_API_KEY=abc", encoding="utf-8")
    environ = {}
    load_env_file(path, environ=environ)
    assert environ["OPENROUTER_API_KEY"] == "abc"


# ---------------------------------------------------------------- loading into the environment
def test_it_sets_new_variables_and_returns_their_names_in_file_order(tmp_path):
    path = tmp_path / ".env"
    path.write_text("B=2\nA=1\n", encoding="utf-8")
    environ = {}
    assert load_env_file(path, environ=environ) == ["B", "A"]
    assert environ == {"B": "2", "A": "1"}


def test_it_never_overrides_a_variable_that_is_already_set(tmp_path):
    path = tmp_path / ".env"
    path.write_text("A=from-file\nB=from-file\n", encoding="utf-8")
    environ = {"A": "from-shell"}
    assert load_env_file(path, environ=environ) == ["B"]
    assert environ == {"A": "from-shell", "B": "from-file"}


def test_a_blank_existing_variable_counts_as_unset(tmp_path):
    path = tmp_path / ".env"
    path.write_text("A=from-file\n", encoding="utf-8")
    environ = {"A": "   "}
    assert load_env_file(path, environ=environ) == ["A"]
    assert environ["A"] == "from-file"


def test_empty_values_are_not_set(tmp_path):
    path = tmp_path / ".env"
    path.write_text("A=\nB=''\nC=   \nD=1\n", encoding="utf-8")
    environ = {}
    assert load_env_file(path, environ=environ) == ["D"]
    assert environ == {"D": "1"}


def test_a_missing_file_is_not_an_error(tmp_path):
    environ = {"KEEP": "1"}
    assert load_env_file(tmp_path / "nope.env", environ=environ) == []
    assert environ == {"KEEP": "1"}


def test_the_real_environment_is_used_by_default(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("CONCIERGE_TEST_ONLY_VAR=hello\n", encoding="utf-8")
    monkeypatch.delenv("CONCIERGE_TEST_ONLY_VAR", raising=False)
    assert load_env_file(path) == ["CONCIERGE_TEST_ONLY_VAR"]
    import os
    assert os.environ["CONCIERGE_TEST_ONLY_VAR"] == "hello"
    monkeypatch.delenv("CONCIERGE_TEST_ONLY_VAR")  # leave nothing behind


def test_the_default_path_is_the_project_root_not_the_working_directory():
    assert DEFAULT_ENV_PATH == Path(app.__file__).resolve().parent.parent / ".env"


# ---------------------------------------------------------------- secrets stay secret
def test_values_are_never_printed_or_logged(tmp_path, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    secret = "MARKER-SECRET-9f2c71"
    path = tmp_path / ".env"
    path.write_text(f"OPENROUTER_API_KEY={secret}\nBROKEN LINE {secret}\n", encoding="utf-8")
    load_env_file(path, environ={})
    out = capsys.readouterr()
    assert secret not in caplog.text + out.out + out.err
