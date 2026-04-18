## PLAN

- remind 不传参数时，应该使用交互式，让用户把必传参数补充上。
- 调研下，找个功能齐全、漂亮、最受欢迎的模块，做交互式界面。
- 检查现在用到交互式的程序，都换上这个模块
- 新增命令，专门实现添加 command 类型的定时任务。同 remind 一样，要有命令行和交互式两种方式实现。

### 0.2.0

- 版本升到 0.2.0
- channels 增加邮件、feishu
- channels add 时，交互界面使用列表，让用户上下键选择添加的方式，同时列表要展示该通道是否已经配置
- 调研邮件、feishu怎么对接

### 0.2.1

- `src/claw_cron/__about__.py:__version__` 升级到 "0.2.1"
- channels capture 增加支持 feishu，跟 add 一样交互式，列表让用户选择增加哪个频道的联系人
- channels 增加微信支持
- channels add 验证频道成功后，需要询问用户是否直接觉醒 capture 操作添加联系人，同意后直接进行获取 openid 操作，不同意再退出

### 0.3.0

- `src/claw_cron/__about__.py:__version__` 升级到 "0.3.0"
- 我想在 command 定时任务增加上下文机制，script 中可以获取系统的上下文内容。然后 script 中也可以传递信息给 command。具体应用场景是：我想做一个定时任务脚本，脚本做签到检查，如果用户一直没签到，则定时任务需要给用户发通知，但是如果签到了。script 传递给 command 一个上下文的值，或者设置一个状态，command 定时任务就不用发送通知。就这个实际场景，调研探讨下这个上下文怎么设计和实现。

### 0.3.1

- `src/claw_cron/__about__.py:__version__` 升级到 "0.3.1"
- 增加 update 命令，必传路径参数为 `name`，支持修改的字段 cron/enabled/message/script/prompt

### 0.3.2

- `src/claw_cron/__about__.py:__version__` 升级到 "0.3.2"
- 修改 contacts 保存方式
    - 如果通道进行 capture 时，alias 没有修改，会覆盖掉其他通道的联系人
    - 应该允许，不同频道有相同联系人名称的存在
- 检查所有用到 contacts 的地方，修改读取和写入操作

## TODO

- [x] 参照 `~/Projects/mlx-cli/Makefile` 创建 Makefile
