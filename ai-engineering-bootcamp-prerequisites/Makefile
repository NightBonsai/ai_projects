# 项目构建快捷入口
# Powershell 终端执行 make run-docker-compose
# 会自动运行以下两条指令
# 今后启动项目需要终端执行 docker compose up 
run-docker-compose:
	uv sync
	docker compose up --build

clean-notebook-outputs:
	jupyter nbconvert --clear-output --inplace notebooks/*/*.ipynb

