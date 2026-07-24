<p align="center">
<a href="./README.md">🇨🇳 中文</a> | <a href="./README_EN.md">🇺🇸 English</a>

# ai_project_prototype

A reusable AI project template.

Backend: **FastAPI**  
Frontend: **Streamlit**

---



# Project Reuse Workflow

```text
Copy the template
    ↓
Rename the project
    ↓
Delete .venv
    ↓
Run uv sync
    ↓
Select the new Python Interpreter
```

Create a new project by copying the template:

```text
D:\ai_projects\
└── new_project
```

Navigate to the project directory:

```powershell
cd D:\ai_projects\new_project
```

---



# 1. Remove the Existing Virtual Environment

Delete the `.venv` directory while keeping the rest of the project files.

```powershell
Remove-Item .venv -Recurse -Force
```

The `.venv` directory is disposable. Running `uv sync` will automatically recreate it.

---



# 2. Rename the Project

Edit the following files:

```toml
# pyproject.toml

[project]
name = "new_project"

# uv.lock

[manifest]
members = [
    "new_project",
    ...
]

[[package]]
name = "new_project"
```

Also verify that the Python version specified in `.python-version` matches your local Python installation.

```text
.python-version      # Python 3.12
```

---



# 3. Recreate the Environment

Run:

```powershell
uv sync
```

This command will:

- Create a new `.venv`
- Install all dependencies from `uv.lock`
- Synchronize the virtual environment with the lockfile

If `.venv` does not exist, `uv sync` will create it automatically.

---



# 4. Verify the Environment

Check the Python version:

```powershell
uv run python --version
```

Example:

```text
Python 3.12.11
```

List installed packages:

```powershell
uv pip list
```

Verify that all required dependencies have been installed successfully.

---



# 5. Select the Python Interpreter in Cursor

Open the Command Palette:

```text
Ctrl + Shift + P
```

Select:

```text
Python: Select Interpreter
```

Then choose:

```text
new_project\.venv\Scripts\python.exe
```

The project is now ready for development.