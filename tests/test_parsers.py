"""Tests for JSON and table parsers."""

import pytest

from src.parsers.json_parser import parse_json, strip_json_comments, ParseError
from src.parsers.table_parser import parse_table, TableParseError
from tests.fixtures.mock_responses import bootstrap, activity_groups


class TestStripJsonComments:
    def test_single_line_comments(self):
        text = '{"key": "value"} // this is a comment'
        result = strip_json_comments(text)
        assert "//" not in result
        assert '"key": "value"' in result

    def test_block_comments(self):
        text = '{"key": /* comment */ "value"}'
        result = strip_json_comments(text)
        assert "/* comment */" not in result

    def test_no_strip_inside_strings(self):
        text = '{"url": "http://example.com"}'
        result = strip_json_comments(text)
        assert "http://example.com" in result

    def test_escaped_quotes_preserved(self):
        text = r'{"quote": "She said \"hello\" to them"}'
        result = strip_json_comments(text)
        assert r"\"hello\"" in result


class TestParseJson:
    def test_valid_json(self):
        result = parse_json('{"name": "test", "value": 42}')
        assert result["name"] == "test"
        assert result["value"] == 42

    def test_json_with_surrounding_text(self):
        result = parse_json('Here is the JSON: {"name": "test"} end')
        assert result["name"] == "test"

    def test_json_with_comments(self):
        result = parse_json("""
        {
            "name": "test", // this is a name
            "value": 42 // this is a value
        }
        """)
        assert result["name"] == "test"

    def test_bootstrap_response(self):
        result = parse_json(bootstrap())
        assert result["name"] == "Rust Riders"
        assert len(result["keywords"]) == 10
        assert result["structure"] == "hierarchy"
        assert result["races"]["human"] == 0.9

    def test_activity_groups_response(self):
        result = parse_json(activity_groups())
        assert "groups" in result
        assert len(result["groups"]) == 2
        assert result["groups"][0]["name"] == "The Mechanic Gang"

    def test_single_quoted_json(self):
        result = parse_json("{'name': 'test', 'value': 42}")
        assert result["name"] == "test"

    def test_no_json_raises(self):
        with pytest.raises(ParseError):
            parse_json("no json here at all")

    def test_malformed_json_fallback(self):
        # Python dict syntax with trailing comma
        result = parse_json("{'name': 'test', 'value': 42,}")
        assert result["name"] == "test"

    def test_json_with_escaped_quotes(self):
        raw = r'{"quote": "No metal is truly lost, just waiting to be found.", "motto": "She said \"hello\" to them"}'
        result = parse_json(raw)
        assert result["quote"] == "No metal is truly lost, just waiting to be found."
        assert result["motto"] == 'She said "hello" to them'

    def test_json_with_stray_escaped_quotes(self):
        """LLM returns backslash-escaped quotes as value delimiters."""
        raw = r'{"quote": \"No metal is truly lost, just waiting to be found.\", "name": \"Grimjaw\"}'
        result = parse_json(raw)
        assert result["quote"] == "No metal is truly lost, just waiting to be found."
        assert result["name"] == "Grimjaw"


class TestParseTable:
    def test_basic_table(self):
        table = """
| name | age | race |
|------|-----|------|
| Alice | 25 | human |
| Bob | 30 | elf |
"""
        result = parse_table(table)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == 25
        assert result[1]["race"] == "elf"

    def test_table_with_json_values(self):
        table = """
| name | origin |
|------|--------|
| Group A | {"local": 0.9, "foreign": 0.1} |
"""
        result = parse_table(table)
        assert result[0]["name"] == "Group A"
        assert isinstance(result[0]["origin"], dict)
        assert result[0]["origin"]["local"] == 0.9

    def test_table_with_list_values(self):
        table = """
| name | keywords |
|------|----------|
| Group A | [one, two, three] |
"""
        result = parse_table(table)
        assert isinstance(result[0]["keywords"], list)

    def test_too_few_rows_raises(self):
        with pytest.raises(TableParseError):
            parse_table("| name |\n")

    def test_float_conversion(self):
        table = """
| name | score |
|------|-------|
| Test | 3.14 |
"""
        result = parse_table(table)
        assert result[0]["score"] == 3.14
