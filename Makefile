.PHONY: install test clean format lint help

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## 清理缓存并安装到本地
	uv cache clean claw-cron --force
	uv tool install . --force
	@echo "✅ 安装完成，版本信息："
	@claw-cron -v

test: ## 运行测试
	uv run pytest

clean: ## 清理构建产物
	rm -rf dist/ build/ src/*.egg-info
	uv cache clean claw-cron

format: ## 格式化代码
	uv run ruff format .

lint: ## 代码检查
	uv run ruff check .
	uv run pyright
