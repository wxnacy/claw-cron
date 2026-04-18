# Quick Task 260418-lmf: update notify support and interactive mode

**Date:** 2026-04-18
**Status:** Complete

## Tasks

### Task 1: storage notify helpers
- **Files:** `src/claw_cron/storage.py`
- **Action:** 新增 `get_notify_list`, `notify_add`, `notify_remove`, `notify_update`, `notify_clear`
- **Done:** ✅

### Task 2: update CLI notify options
- **Files:** `src/claw_cron/cmd/update.py`
- **Action:** 新增 `--notify-add/remove/channel/recipient/when/clear` options
- **Done:** ✅

### Task 3: update interactive mode
- **Files:** `src/claw_cron/cmd/update.py`
- **Action:** 无参数时进入交互式，select 循环选字段修改，notify 子流程支持增删改清空
- **Done:** ✅

### Task 4: fix interactive checkbox unresponsive
- **Files:** `src/claw_cron/cmd/update.py`
- **Action:** InquirerPy checkbox 空格键在此环境失效，改用 select 循环彻底绕开
- **Done:** ✅
