# Codex Medical AI Review Generator

一个可在 **GPT Codex** 中直接运行的医学人工智能综述自动化项目：
- 自动从 arXiv 检索文献（真实在线来源）
- 自动生成结构化 `Markdown` 综述草稿
- **不生成图片**，但在文中插入明确的“图片插入位置 + caption 建议”
- 所有参考文献都链接到对应 arXiv 页面与 PDF

## 目录结构

```text
codex-medical-review/
├── README.md
├── requirements.txt
├── scripts/
│   └── generate_review.py
└── assets/
    └── review_template.md
```

## 快速开始

```bash
cd codex-medical-review
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_review.py \
  --topic "medical image segmentation transformer" \
  --max-results 25 \
  --start-year 2021 \
  --output ../manuscript_draft.md
```

> `requirements.txt` 目前无第三方硬依赖（标准库即可运行）。

运行后会在指定路径生成 Markdown 综述草稿。

## 参数说明

- `--topic`：检索主题（建议英文关键词，提升 arXiv 命中率）
- `--max-results`：最多纳入的文献数量（默认 30）
- `--start-year`：只保留该年份及之后的论文（默认 2020）
- `--output`：输出 markdown 文件路径（默认 `manuscript_draft.md`）
- `--input-feed`：可选，本地 arXiv Atom XML 文件（用于离线/受限网络环境）

## 输出内容特性

- 自动写入：
  - 标题、Key Points、摘要、方法分类、挑战与未来方向
  - 文献综述主干（按时间排序）
- 自动插入图片占位（仅文本说明，不绘图）：
  - `Figure 1`：任务分类总览图（建议 caption）
  - `Figure 2`：方法演化时间线（建议 caption）
  - `Figure 3`：典型模型框架对比（建议 caption）
- 参考文献：
  - 每条带 `[R#]` 编号
  - 包含标题、作者、年份、arXiv ID、abs 链接、pdf 链接

## 在 GPT Codex 中使用建议

1. 先运行脚本生成首稿；
2. 再让 Codex 基于同一份参考文献进行章节扩写；
3. 如需更严格真实性，可在扩写时限制“不得新增未在 References 中出现的文献编号”。

## 注意事项

- 该项目依赖 arXiv API 的在线可访问性。
- 生成的正文为“可编辑初稿”，可继续由 Codex 改写为投稿风格。
- 为避免引用失真，脚本只根据 arXiv 返回元数据构建 References，不自动伪造页码/DOI。


## 离线演示（无外网）

```bash
python scripts/generate_review.py \
  --topic "medical image segmentation" \
  --input-feed assets/sample_arxiv_feed.xml \
  --start-year 2020 \
  --output sample_review.md
```

> `assets/sample_arxiv_feed.xml` 仅用于离线功能验证，不代表真实检索结果。
