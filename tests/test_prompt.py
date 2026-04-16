# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for prompt module - InquirerPy interactive prompts."""

from unittest.mock import MagicMock, patch

import pytest

from claw_cron.prompt import prompt_confirm, prompt_cron, prompt_multiselect, prompt_select, prompt_text


class TestPromptText:
    """Tests for prompt_text function."""

    @patch("claw_cron.prompt.inquirer")
    def test_returns_user_input(self, mock_inquirer: MagicMock) -> None:
        """prompt_text returns user input from inquirer."""
        mock_inquirer.text.return_value.execute.return_value = "test_input"
        result = prompt_text("Enter name")
        assert result == "test_input"

    @patch("claw_cron.prompt.inquirer")
    def test_returns_default_when_provided(self, mock_inquirer: MagicMock) -> None:
        """prompt_text passes default value to inquirer."""
        mock_inquirer.text.return_value.execute.return_value = "default_value"
        result = prompt_text("Enter name", default="default_value")
        assert result == "default_value"
        # Verify default was passed to inquirer
        call_kwargs = mock_inquirer.text.call_args[1]
        assert call_kwargs.get("default") == "default_value"


class TestPromptConfirm:
    """Tests for prompt_confirm function."""

    @patch("claw_cron.prompt.inquirer")
    def test_returns_true(self, mock_inquirer: MagicMock) -> None:
        """prompt_confirm returns True for yes."""
        mock_inquirer.confirm.return_value.execute.return_value = True
        result = prompt_confirm("Continue?")
        assert result is True

    @patch("claw_cron.prompt.inquirer")
    def test_returns_false(self, mock_inquirer: MagicMock) -> None:
        """prompt_confirm returns False for no."""
        mock_inquirer.confirm.return_value.execute.return_value = False
        result = prompt_confirm("Continue?", default=True)
        assert result is False


class TestPromptSelect:
    """Tests for prompt_select function."""

    @patch("claw_cron.prompt.inquirer")
    def test_returns_selected_choice(self, mock_inquirer: MagicMock) -> None:
        """prompt_select returns the selected choice."""
        mock_inquirer.select.return_value.execute.return_value = "option_a"
        result = prompt_select("Choose one", choices=["option_a", "option_b"])
        assert result == "option_a"

    @patch("claw_cron.prompt.inquirer")
    def test_passes_default_to_inquirer(self, mock_inquirer: MagicMock) -> None:
        """prompt_select passes default choice to inquirer."""
        mock_inquirer.select.return_value.execute.return_value = "option_a"
        prompt_select("Choose one", choices=["option_a", "option_b"], default="option_a")
        call_kwargs = mock_inquirer.select.call_args[1]
        assert call_kwargs.get("default") == "option_a"


class TestPromptMultiselect:
    """Tests for prompt_multiselect function."""

    @patch("claw_cron.prompt.inquirer")
    def test_returns_selected_choices(self, mock_inquirer: MagicMock) -> None:
        """prompt_multiselect returns list of selected choices."""
        mock_inquirer.checkbox.return_value.execute.return_value = ["a", "c"]
        result = prompt_multiselect("Choose many", choices=["a", "b", "c"])
        assert result == ["a", "c"]

    @patch("claw_cron.prompt.inquirer")
    def test_returns_empty_list_when_none_selected(self, mock_inquirer: MagicMock) -> None:
        """prompt_multiselect returns empty list when nothing selected."""
        mock_inquirer.checkbox.return_value.execute.return_value = []
        result = prompt_multiselect("Choose many", choices=["a", "b", "c"])
        assert result == []


class TestPromptCron:
    """Tests for prompt_cron function."""

    @patch("claw_cron.prompt.inquirer")
    def test_returns_cron_expression_from_preset(self, mock_inquirer: MagicMock) -> None:
        """prompt_cron returns correct cron expression for preset selection."""
        # User selects "每小时整点" preset
        mock_inquirer.select.return_value.execute.return_value = "0 * * * *"
        result = prompt_cron()
        assert result == "0 * * * *"

    @patch("claw_cron.prompt.inquirer")
    def test_displays_presets_with_descriptions(self, mock_inquirer: MagicMock) -> None:
        """prompt_cron displays presets with human-readable descriptions."""
        mock_inquirer.select.return_value.execute.return_value = "* * * * *"
        prompt_cron()

        # Verify select was called with choices
        call_args = mock_inquirer.select.call_args
        assert call_args is not None
        choices = call_args[1].get("choices", [])
        # Should have 9 options (8 presets + 1 custom)
        assert len(choices) == 9

    @patch("claw_cron.prompt.inquirer")
    def test_custom_option_prompts_for_input(self, mock_inquirer: MagicMock) -> None:
        """prompt_cron allows custom cron expression input."""
        # User selects "自定义"
        mock_inquirer.select.return_value.execute.return_value = "custom"
        mock_inquirer.text.return_value.execute.return_value = "30 14 * * 5"

        with patch("claw_cron.prompt.prompt_text") as mock_text:
            mock_text.return_value = "30 14 * * 5"
            result = prompt_cron()
            assert result == "30 14 * * 5"

    @patch("claw_cron.prompt.inquirer")
    def test_all_presets_have_correct_expressions(self, mock_inquirer: MagicMock) -> None:
        """prompt_cron has all 8 preset cron expressions."""
        preset_crons = {
            "* * * * *": "每分钟",
            "0 * * * *": "每小时整点",
            "0 8 * * *": "每天早上8点",
            "0 12 * * *": "每天中午12点",
            "0 18 * * *": "每天晚上6点",
            "0 9 * * 1": "每周一早上9点",
            "0 9 * * 1-5": "工作日早上9点",
            "0 0 1 * *": "每月1号",
        }

        for cron_expr, _ in preset_crons.items():
            mock_inquirer.select.return_value.execute.return_value = cron_expr
            result = prompt_cron()
            assert result == cron_expr
