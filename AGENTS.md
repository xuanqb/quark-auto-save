# AGENTS

## 提交规范

- 提交信息统一用 `type: 中文说明`，`type` 取英文小写，说明直接描述结果，例如 `fix: 修复夸克重命名日期解析`。
- 常用类型：`feat` 新功能、`fix` 缺陷修复、`chore` 杂项维护（不写 `chroe`）、`docs` 文档、`test` 测试、`refactor` 不改变外部行为的重构。

## 交付流程

- 需求完成并通过必要验证后，默认提交并推送到当前分支对应的远端，不要让已完成改动长期停留在未提交状态。
- 用户明确要求暂停、只改不提交或只提交不推送，以及远端阻塞推送时除外。
- 提交前运行与改动相关的测试（见下方 Python 环境约定）。验证无法执行或推送失败时，在回复里说明原因和当前状态。

## 代码注释约定

- 新增注释用中文，只在代码不够直观、需要补充上下文时添加，不写"给变量赋值"这类重复代码字面的低信息量注释。
- 不要求把已有英文注释批量改成中文，按新增或修改范围自然维护。

## Python 环境约定

- 本项目默认使用仓库内 `.venv`，执行 Python、pip 用 `.venv/bin/python`、`.venv/bin/pip`。
- 不要默认使用系统 `python`、`python3` 或全局 `pip`，除非用户明确说明。
- 测试是 `unittest` 用例，用 `.venv/bin/python -m unittest <模块名>` 运行。`.venv` 中没有 pytest，不要引入新测试框架。
- `test_balanced.py` 是打印式的对比脚本，不是自动化用例，不要当作测试套件调用。
- 运行依赖见 `requirements.txt`：flask、apscheduler、requests、treelib。

## 后台文案偏好

- 后台页面（`app/templates/`）按偏后端工具风格处理，文案保持克制：单用户自用页面用短标题、短说明，不主动加大段引导性描述。
- 只有在确实影响理解或操作风险时才补充额外说明。

## 配置文件与凭据

- `quark_config.json` 和 `app/config/quark_config.json` 已在 `.gitignore` 中忽略，内含 cookie、Emby apikey、webui 密码等真实凭据。
- 不要用 `git add -f` 强制添加，不要把真实凭据写进提交内容、测试用例或文档示例；需要示例时一律用占位符。
- 这两个文件是程序运行所必需的本地文件，调整忽略规则前先确认不影响运行。

## 上游同步

- 本仓库是 `Cp0204/quark-auto-save` 的 fork，通过 `.github/workflows/UpstreamSync.yml` 同步上游。
- 修改 `quark_auto_save.py`、`app/`、`notify.py` 等上游文件时改动尽量收敛，避免与上游更新产生大范围冲突。
- 本地自有内容（如 `hermes-skill/`）与上游文件分开存放，不要混写进上游文件。
