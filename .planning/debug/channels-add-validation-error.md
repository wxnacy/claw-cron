---
status: resolved
trigger: "重复执行 channels add 会报错 Channel type (qqbot): qqbot\nError: Validation failed: invalid appid or secret"
created: "2026-04-16T16:00:00.000Z"
updated: "2026-04-16T16:20:00.000Z"
---

# Debug Session: channels-add-validation-error

## Symptoms

**Expected behavior:** 重复添加相同的 QQ 通道时，应该更新现有配置
**Actual behavior:** 第一次添加成功，第二次执行时报验证错误
**Error messages:** Error: Validation failed: invalid appid or secret
**Timeline:** 在第一次成功添加后立即发生
**Reproduction:** 使用相同的参数执行两次 channels add 命令

## Current Focus

**hypothesis:** The validation error is caused by invalid credentials - the app_id and client_secret don't match. The user is using app_id 1903747347 with a client_secret that belongs to a different app (1903711110).
**test:** Direct API call confirms QQ Bot API returns error code 100016 "invalid appid or secret" for these credentials.
**expecting:** Expected behavior - invalid credentials should fail validation.
**next_action:** Document root cause and close investigation
**reasoning_checkpoint:** The user's symptom description "重复执行 channels add 会报错" (repeating channels add causes error) was misleading. The actual issue is using invalid credentials, which would fail on BOTH first and subsequent runs.
**tdd_checkpoint:** null

## Eliminated

- hypothesis: QQ Bot API rate limiting on repeated auth requests | reason: Testing shows the API accepts 5 consecutive requests with valid credentials within seconds
- hypothesis: Click interactive prompt handling issue | reason: Error occurs even with CLI flags, no prompt involved
- hypothesis: Code bug in validation logic | reason: Validation logic is correct and works with valid credentials

## Evidence

- timestamp: 2026-04-16T16:05:00.000Z | observation: Found validation logic in channels.py lines 74-86. Validation makes direct API call to https://bots.qq.com/app/getAppAccessToken with JSON payload using camelCase (appId, clientSecret).
- timestamp: 2026-04-16T16:05:30.000Z | observation: Config file exists at ~/.config/claw-cron/config.yaml with qqbot channel configured. app_id='1903711110' (quoted), client_secret=FRRFrHVWKwLXWJuI (unquoted).
- timestamp: 2026-04-16T16:06:00.000Z | observation: Validation is stateless - each call makes a fresh HTTP request. No caching or reuse of existing tokens during validation phase.
- timestamp: 2026-04-16T16:10:00.000Z | observation: User reports error occurs in both interactive and CLI flag modes, 100% reproducible, with same credentials. However, my testing shows the command works fine for 5 consecutive runs.
- timestamp: 2026-04-16T16:11:00.000Z | observation: No recent changes to validation logic in channels.py. The code has remained stable since initial implementation.
- timestamp: 2026-04-16T16:15:00.000Z | observation: User provided exact command: `uv run claw-cron channels add --app-id 1903747347 --client-secret FRRFrHVWKwLXWJuI`. Testing shows this app_id (1903747347) FAILS validation, while the config file has a different app_id (1903711110) that WORKS.
- timestamp: 2026-04-16T16:16:00.000Z | observation: Direct API test confirms: QQ Bot API returns error code 100016 "invalid appid or secret" for app_id=1903747347 with client_secret=FRRFrHVWKwLXWJuI. The credentials are INVALID - this is NOT a repetition issue.

## Resolution

**root_cause:** Invalid credentials - the user is attempting to use app_id 1903747347 with a client_secret that belongs to a different QQ Bot application (1903711110). The QQ Bot API correctly rejects these mismatched credentials with error code 100016 "invalid appid or secret".
**fix:** User needs to obtain the correct client_secret for app_id 1903747347 from the QQ Bot management console at q.qq.com, or use the correct app_id (1903711110) that matches the client_secret FRRFrHVWKwLXWJuI.
**verification:** Verified by testing both credentials directly against QQ Bot API:
  - app_id=1903747347 + client_secret=FRRFrHVWKwLXWJuI → Error 100016 "invalid appid or secret"
  - app_id=1903711110 + client_secret=FRRFrHVWKwLXWJuI → Success (access_token returned)
**files_changed:** []

---
