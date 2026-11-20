"""环节 3：方案撰写 —— 把客户回复整理成一页式试点方案。"""
from __future__ import annotations

from llm import prompts
from llm.client import LLMClient

LIST_FIELDS = [
    "objectives",
    "audience_hypothesis",
    "services",
    "workstream",
    "deliverables",
    "metrics",
    "open_questions",
]


def _as_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _target_market(lead: dict) -> str:
    for market in lead.get("target_markets") or []:
        if str(market).strip().lower() not in {"global", "worldwide", "unknown"}:
            return market
    return "US"


def _fallback_proposal(lead: dict, customer_reply: str) -> dict:
    company = lead.get("company_name", "客户")
    market = _target_market(lead)
    services = [
        "受众与竞品内容分析",
        "英文内容选题与撰写",
        f"{market} 市场 LinkedIn 内容运营",
        "英文 SEO 内容基础建设",
        "线索收集与初步筛选",
    ]
    return {
        "proposal_id": "proposal_001",
        "lead_id": lead.get("id"),
        "title": f"{company} 海外内容营销 30 天试点方案",
        "target_market": market,
        "duration": "30 天",
        "current_state": (
            f"客户当前市场为 {lead.get('current_market', '未知')}，目标市场为 "
            f"{'、'.join(lead.get('target_markets') or []) or '待确认'}；"
            f"已知缺口包括 {'、'.join(lead.get('marketing_gaps') or ['暂未记录'])}。"
            f"客户回复要点：{customer_reply.strip()}"
        ),
        "objectives": [
            f"验证 {market} 市场的英文内容方向",
            "在一个月内提升英文内容的曝光与互动",
            "获得一批可人工筛选的初步潜在客户",
        ],
        "audience_hypothesis": [
            "美国中小团队中负责运营、知识与文档协作的管理者",
            "正在评估 AI 文档 / 知识助手的团队负责人",
            "关注团队效率与知识沉淀的运营与 HR 角色",
        ],
        "services": services,
        "workstream": [
            "第 1–4 天：受众与竞品分析，确认产品卖点与内容基调",
            "第 5–10 天：完成 4 篇英文内容选题与初稿",
            "第 11–25 天：在 LinkedIn 与英文官网 / Blog 发布并互动",
            "第 26–30 天：汇总数据、复盘并给出下一轮建议",
        ],
        "deliverables": [
            "英文内容选题表（4 条）",
            "4 篇英文内容（LinkedIn + Blog）",
            "发布记录与互动记录",
            "线索汇总表",
            "月度复盘报告",
        ],
        "metrics": [
            "内容曝光量",
            "互动率（互动 / 曝光）",
            "官网访问量（内容渠道）",
            "潜在线索数与有效线索数",
        ],
        "open_questions": [
            "目标客户画像与优先级（团队规模、行业、决策角色）",
            "产品卖点与可公开引用的客户案例",
            "现有官网数据与转化路径",
            "试点预算范围与审批流程",
        ],
        "status": "draft",
        "generated_by": "template",
        "is_demo_data": True,
    }


def generate_proposal(lead: dict, customer_reply: str, llm: LLMClient | None = None) -> dict:
    """根据客户回复生成方案；规则模板始终可用，模型仅做增强。"""
    proposal = _fallback_proposal(lead, customer_reply)
    if not (llm and llm.configured):
        return proposal

    data = llm.complete_json(prompts.proposal_prompt(lead, customer_reply))
    if not data:
        return proposal

    for key in ("title", "target_market", "duration", "current_state"):
        if data.get(key):
            proposal[key] = str(data[key])
    for key in LIST_FIELDS:
        values = _as_str_list(data.get(key))
        if values:
            proposal[key] = values
    proposal["generated_by"] = "llm"
    return proposal


def render_proposal_markdown(proposal: dict) -> str:
    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- 待补充"

    return f"""### {proposal['title']}

**目标市场：** {proposal['target_market']}　|　**执行周期：** {proposal['duration']}

**1. 客户现状与核心目标**

{proposal['current_state']}

{bullets(proposal['objectives'])}

**2. 目标市场与受众假设**

{bullets(proposal['audience_hypothesis'])}

**3. 服务范围**

{bullets(proposal['services'])}

**4. 执行节奏**

{bullets(proposal['workstream'])}

**5. 交付物**

{bullets(proposal['deliverables'])}

**6. 效果衡量指标**

{bullets(proposal['metrics'])}

**7. 待客户确认的问题**

{bullets(proposal['open_questions'])}

> 以上为模拟试点方案，不构成对实际曝光量、访问量或线索数量的保证。
"""
