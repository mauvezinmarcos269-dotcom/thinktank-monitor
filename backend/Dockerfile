FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统库（如 OCR 和 PDF 处理所需）
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 poetry
RUN pip install --no-cache-dir poetry

# 复制项目依赖文件
COPY pyproject.toml poetry.lock ./

# 将 Poetry 依赖导出为 requirements.txt 并安装（不在镜像内保留 poetry 虚拟环境，减小体积）
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && pip install --no-cache-dir -r requirements.txt

# 单独安装可能带来构建问题的 AI/OCR 库 (可选)
# RUN pip install --no-cache-dir paddlepaddle paddleocr

# 复制项目代码
COPY ./app ./app

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]