FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 替换 Debian 12 (Bookworm) 官方源为阿里云源，避免国内网络超时报错
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装必要的系统库（处理智库 PDF 报告及图片解析的核心依赖）
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 poetry，并使用国内 PyPI 镜像源加速下载
RUN pip install --no-cache-dir poetry -i https://mirrors.aliyun.com/pypi/simple/

# 复制依赖文件并进行安装
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# 创建非 root 运行用户，降低 Web 与 worker 容器运行风险
RUN addgroup --system app \
    && adduser --system --ingroup app app

# 复制项目代码
COPY --chown=app:app . .

USER app

EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
