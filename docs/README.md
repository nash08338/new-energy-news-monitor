# 全球能源新闻监控系统

自动监控全球新能源（光伏、储能、充电桩）新闻，生成图片报告。

## 功能

- 多源 RSS/API 抓取（SolarQuarter、Electrive、PVMagazine、EnergyStorageNews 等）
- DeepSeek AI 分类整理，按区域生成摘要
- Playwright 生成图片报告
- GitHub Actions 手动触发（workflow_dispatch）

## 报告输出

- 图片：`docs/images/overview_*.png`（总览图）
- 压缩包：`docs/images/regions_*.zip`（区域图）
- 新闻库：`docs/news_master.csv`

## 本地运行

```bash
pip install -r requirements.txt
python -m news_monitor.main
```

部署：GitHub Secrets 配置 DEEPSEEK_API_KEY → Actions 手动触发 `RSS 新闻抓取`
