## Projects

版本号修改位置 `src/claw_cron/__about__.py:__version__`

## TODO

- [ ] 版本升级到 "0.3.3"
    - 需求细节
        - chat 命令增加 `--agent` `-a` 参数，支持 codebuddy，默认使用 codebuddy
        - chat 命令增加 `--model` `-m` 参数，用来选择模型，默认使用 minimax-m2.5
        - codebuddy 参考文档 
            - https://www.codebuddy.cn/docs/cli/sdk
            - https://www.codebuddy.cn/docs/cli/sdk-python
            - https://www.codebuddy.cn/docs/cli/sdk-custom-tools
        - 需要将 list command context delete remind update 内置方法，集成到自定义工具中，让 agent 可以调用
        - 内置工具要使用渐进式批量，系统提示词中给名称和描述，然后给获取工具的方法，让 agent 使用
        - agent 对话日志要根据 session 单独保存，方便调试和对话恢复
        - chat 对话过程要显示每轮的 tokens 消耗具体情况，输出、输入、缓存
        - CODEBUDDY_INTERNET_ENVIRONMENT 没有设置，默认使用 internal
        - CODEBUDDY_API_KEY 没有设置，友好提示用户，不要抛异常
