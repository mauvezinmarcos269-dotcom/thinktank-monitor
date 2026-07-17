# ThinkTank Monitor

ThinkTank Monitor 是一个面向智库研究报告的实时监测、采集、翻译和分析平台。

系统主要用于：

- 接入国内外智库、研究机构和政府机构网站
- 自动采集研究报告、政策简报和评论文章
- 对报告进行去重、归档和全文保存
- 调用大语言模型生成翻译和分析评论
- 支持按照标题、来源、发布时间和分析状态检索报告
- 为教师和管理员提供统一的监测仪表盘

## 技术栈

### 后端

- Python
- FastAPI
- SQLAlchemy Async
- PostgreSQL
- Redis
- Celery
- MinIO
- JWT

### 前端

- Next.js
- React
- TypeScript

## 项目结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── docker-compose.yml
├── Makefile
└── README.md