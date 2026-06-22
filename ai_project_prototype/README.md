# ai_projects

## ai_project_prototype

可复用的 AI 项目原型

后端 FastAPI + 前端 Streamlit



## 项目复用流程

```text
复制模板 → 修改项目名 → 删除 .venv → uv sync → 重新选择解释器
```

复制出一个新项目：

```text
D:\ai_projects\
└── 新项目
```

进入项目：

```powershell
cd D:\ai_projects\新项目
```

------

## 1. 删除旧环境

删除 .venv/ 保留剩余内容

```powershell
Remove-Item .venv -Recurse -Force
```

 `.venv` 是可再生的。`uv sync` 会自动重新创建。([Astral Docs](https://docs.astral.sh/uv/reference/cli/?utm_source=chatgpt.com))

------

## 2. 修改项目名称

编辑：

```toml
# pyproject.toml
[project]
name = "新项目"

# uv.lock
[manifest]
members = [
    "新项目",
	...
]
[[package]]
name = "新项目"
```

确认 . python-version 内 Python 版本是否与当前 Python 版本一致

```text
.python-version			# Python 3.12
```

------

## 3. 重新生成环境

执行：

```powershell
uv sync
```

- 创建新的 `.venv`
- 根据 `uv.lock` 安装依赖
- 更新环境与 lockfile 同步

如果 `.venv` 不存在，`uv sync` 会自动创建它。

------

## 4. 验证环境

检查：

```powershell
uv run python --version			# Python 3.12.11
```

```powershell
uv pip list
```

确认依赖是否都已安装

------

## 5. Cursor 重新选择解释器

按：

```text
Ctrl + Shift + P
```

选择：

```text
Python: Select Interpreter
```

选择：

```text
新项目\.venv\Scripts\python.exe
```

------



