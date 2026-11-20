# AI 出海营销助手 Demo

面向海外营销服务商的流程 Demo，串起五个环节：

**客户分析 → 客户联系 → 方案撰写 → 执行交付 → 数据复盘**

全部使用模拟数据；AI 生成内容仅作演示，不会向外部发送。

## 运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

然后打开 http://localhost:8501。

## 模型增强（可选）

默认使用规则评分与模板文案，无需任何 API 即可完整演示。若需要大模型增强：

- 在侧边栏「模型设置」中勾选启用，填写 API Key、Base URL（默认 `https://api.openai.com/v1`）和模型名；
- 或设置环境变量 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。

模型调用失败时会自动回退到规则 / 模板结果。

## 目录结构

```text
├── app.py                    # Streamlit 页面入口（五环节流程）
├── data/
│   ├── leads.json            # 5 家模拟 AI 企业
│   └── campaign_metrics.json # 模拟营销数据（含分内容数据）
├── services/
│   ├── lead_service.py       # 规则评分 + 推荐理由
│   ├── contact_service.py    # 邮件 / LinkedIn 文案与跟进计划
│   ├── proposal_service.py   # 30 天试点方案
│   ├── delivery_service.py   # 任务拆解 + 交付样例
│   └── review_service.py     # 指标计算 + 复盘建议
└── llm/
    ├── client.py             # OpenAI 兼容接口，失败自动兜底
    └── prompts.py            # 各环节提示词
```

## 评分规则（Demo）

| 维度 | 分值 |
|---|---:|
| 目标市场明确度 | 0–25 |
| 产品与服务匹配度 | 0–25 |
| 海外营销缺口 | 0–25 |
| 近期出海信号 | 0–15 |
| 预算 / 合作可能性 | 0–10 |

≥80 高优先级，60–79 中优先级，<60 低优先级。评分由规则计算，LLM 仅负责解释与文案。

## 演示说明

- NovaMind AI 为虚构客户，评分 86 分，用于串起完整流程。
- 邮件、方案、任务和复盘数据均为模拟内容，页面中已明确标注。
- 邮件与 LinkedIn 内容允许人工编辑，Demo 不包含真实发送、CRM 或爬虫能力。
