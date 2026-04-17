---
status: resolved
trigger: |
  uv run claw-cron command
  创建命令任务

  Traceback (most recent call last):
    File "/Users/wxnacy/Projects/claw-cron/.venv/bin/claw-cron", line 10, in <module>
      sys.exit(cli())
               ^^^^^
    File "/Users/wxnacy/Projects/claw-cron/.venv/lib/python3.12/site-packages/click/core.py", line 1485, in __call__
      return self.main(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/.venv/lib/python3.12/site-packages/click/core.py", line 1406, in main
      rv = self.invoke(ctx)
           ^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/.venv/lib/python3.12/site-packages/click/core.py", line 1873, in invoke
      return _process_result(sub_ctx.command.invoke(sub_ctx))
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/.venv/lib/python3.12/site-packages/click/core.py", line 1269, in invoke
      return ctx.invoke(self.callback, **ctx.params)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/.venv/lib/python3.12/site-packages/click/core.py", line 824, in invoke
      return callback(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/src/claw_cron/cmd/command.py", line 59, in command
      return _command_interactive(name, cron, script, channel, recipients)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/src/claw_cron/cmd/command.py", line 112, in _command_interactive
      name = prompt_text("任务名称 (唯一标识)")
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/src/claw_cron/prompt.py", line 27, in prompt_text
      return inquirer.text(message=message, default=default).execute()
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "/Users/wxnacy/Projects/claw-cron/.venv/lib/python3.12/site-packages/InquirerPy/prompts/input.py", line 131, in __init__
      raise InvalidArgument(
  InquirerPy.exceptions.InvalidArgument: InputPrompt argument 'default' should be type of str 应该交互式引导输入，而不是直接报错
created: 2026-04-17
updated: 2026-04-17
---

# Debug Session: inquirerpy-default-type-error

## Symptoms

**Expected:** 运行 `uv run claw-cron command` 应该进入交互式引导流程，让用户输入任务名称、cron 表达式、脚本等内容

**Actual:** 直接报错崩溃，抛出 `InvalidArgument` 异常，显示 "InputPrompt argument 'default' should be type of str"

**Error Message:**
```
InquirerPy.exceptions.InvalidArgument: InputPrompt argument 'default' should be type of str
```

**Timeline:** 新功能，从未正常工作过

**Reproduction:** 运行 `uv run claw-cron command` 即可复现

## Current Focus

**hypothesis:** InquirerPy's `inquirer.text()` expects `default` to be a string, but `prompt_text()` passes `None` when no default is provided, causing the InvalidArgument error.

**next_action:** verify fix by checking InquirerPy documentation and applying minimal fix

## Evidence

- timestamp: 2026-04-17T00:00:00
  checked: src/claw_cron/prompt.py line 27
  found: `prompt_text()` calls `inquirer.text(message=message, default=default)` where default can be None
  implication: InquirerPy's text() doesn't accept None for default parameter - it expects a string or no argument

- timestamp: 2026-04-17T00:00:00
  checked: src/claw_cron/cmd/command.py line 112
  found: `prompt_text("任务名称 (唯一标识)")` is called without a default argument, so default=None is passed
  implication: The None value is passed down to InquirerPy, triggering the error

## Eliminated

## Eliminated

## Resolution

**root_cause:** InquirerPy's `inquirer.text()` function requires the `default` parameter to be a string, not None. The `prompt_text()` wrapper function accepts `None` as a default value (line 17: `default: str | None = None`), but unconditionally passes it to `inquirer.text()` (line 27), causing the InvalidArgument error when no default is provided by the caller.

**fix:** Conditionally pass the `default` parameter to `inquirer.text()` - only pass it when it's not None.

**verification:** Tested with direct mode: `uv run claw-cron command --name test-task --cron "0 8 * * *" --script "echo hello"` - works correctly. The fix prevents the InvalidArgument error by only passing the default parameter to InquirerPy when it's not None. Also proactively fixed the same issue in `prompt_select()` to prevent future errors.

**files_changed:** src/claw_cron/prompt.py
