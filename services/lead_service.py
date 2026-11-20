"""环节 1：潜在客户分析 —— 规则评分 + AI 解释。"""
from __future__ import annotations

from llm import prompts
from llm.client import LLMClient

HIGH_THRESHOLD = 80
MEDIUM_THRESHOLD = 60

ENGLISH_CONTENT_SCORE = {"none": 8, "minimal": 5, "moderate": 3, "strong": 0}
CONTENT_ACTIVITY_SCORE = {"low": 10, "medium": 5, "high": 0}
BUDGET_SCORE = {"explicit": 10, "estimated": 6, "unknown": 0}

DIMENSION_LABELS = {
    "target_market": "目标市场明确度",
    "product_fit": "产品与服务匹配度",
    "marketing_gap": "海外营销缺口",
    "signals": "近期出海信号",
    "budget": "预算 / 合作可能性",
}


def _score_target_market(targets: list[str]) -> tuple[int, str]:
    named = [t for t in targets if str(t).strip().lower() not in {"", "global", "worldwide", "unknown"}]
    if len(named) >= 2:
        return 25, f"明确提到 {len(named)} 个目标市场（{'、'.join(named)}）"
    if len(named) == 1:
        return 18, f"只提到 1 个具体目标市场（{named[0]}）"
    if targets:
        return 10, "只给出「全球」这类宽泛目标，缺少具体市场"
    return 0, "没有明确的目标市场"


def _score_product_fit(industry: str) -> tuple[int, str]:
    normalized = (industry or "").lower()
    if "ai" in normalized and ("saas" in normalized or "software" in normalized):
        return 25, f"行业为 {industry}，与 AI SaaS 目标客户高度匹配"
    if "saas" in normalized or "software" in normalized:
        return 15, f"行业为 {industry}，属于可服务范围但非 AI 原生"
    if "ai" in normalized:
        return 12, f"行业为 {industry}，AI 相关但服务匹配度一般"
    if "hardware" in normalized or "device" in normalized:
        return 8, f"行业为 {industry}，硬件类客户与内容营销服务匹配度较低"
    return 5, f"行业为 {industry}，与当前服务能力匹配度低"


def _score_gap(lead: dict) -> tuple[int, str]:
    score = ENGLISH_CONTENT_SCORE.get(lead.get("english_content", ""), 5)
    if not lead.get("overseas_social"):
        score += 7
    score += CONTENT_ACTIVITY_SCORE.get(lead.get("content_activity", ""), 5)
    score = min(25, score)
    details = []
    if score >= 18:
        details.append("英文内容与海外社媒基础薄弱")
    elif score >= 10:
        details.append("海外内容体系仍在建设中")
    else:
        details.append("海外内容基础相对完善，缺口有限")
    gaps = lead.get("marketing_gaps") or []
    if gaps:
        details.append("资料记录的缺口：" + "、".join(gaps))
    return score, "；".join(details)


def _score_signals(signals: list[str]) -> tuple[int, str]:
    score = min(15, 4 * len(signals or []))
    if score:
        return score, "已观察到出海信号：" + "、".join(signals)
    return 0, "暂未观察到近期出海动作"


def _score_budget(status: str) -> tuple[int, str]:
    score = BUDGET_SCORE.get(status, 0)
    label = {
        "explicit": "已有明确预算线索",
        "estimated": "有预算假设但未确认",
        "unknown": "预算未知（不默认给高分）",
    }.get(status, "预算信息缺失")
    return score, label


def analyze_lead(lead: dict) -> dict:
    """计算客户匹配分，并给出可解释的评分依据。"""
    target_score, target_reason = _score_target_market(lead.get("target_markets") or [])
    fit_score, fit_reason = _score_product_fit(lead.get("industry", ""))
    gap_score, gap_reason = _score_gap(lead)
    signal_score, signal_reason = _score_signals(lead.get("signals") or [])
    budget_score, budget_reason = _score_budget(lead.get("budget_status", "unknown"))

    dimensions = {
        "target_market": {"score": target_score, "max": 25, "reason": target_reason},
        "product_fit": {"score": fit_score, "max": 25, "reason": fit_reason},
        "marketing_gap": {"score": gap_score, "max": 25, "reason": gap_reason},
        "signals": {"score": signal_score, "max": 15, "reason": signal_reason},
        "budget": {"score": budget_score, "max": 10, "reason": budget_reason},
    }
    total = sum(item["score"] for item in dimensions.values())
    if total >= HIGH_THRESHOLD:
        priority, priority_label = "high", "高优先级"
    elif total >= MEDIUM_THRESHOLD:
        priority, priority_label = "medium", "中优先级"
    else:
        priority, priority_label = "low", "低优先级"

    reasons = [item["reason"] for item in dimensions.values() if item["score"] > 0]
    gaps = lead.get("marketing_gaps") or []
    pain_points = [f"可能存在的缺口：{gap}" for gap in gaps] or ["资料不足，需在首次沟通中确认痛点"]
    questions = [
        f"目前进入 {', '.join(lead.get('target_markets') or ['目标市场'])} 的节奏和目标是什么？",
        "现有英文官网、内容与社媒数据大致处于什么水平？",
        "这一轮试点的预算范围、决策人和审批流程是怎样的？",
    ]

    facts = [
        f"企业类型：{lead.get('industry', '未知')}",
        f"当前市场：{lead.get('current_market', '未知')}",
        f"目标市场：{', '.join(lead.get('target_markets') or []) or '未说明'}",
    ]
    to_verify = [lead.get("budget_note", "预算未知")] + (lead.get("signals") or [])

    return {
        "lead_id": lead.get("id"),
        "company_name": lead.get("company_name"),
        "score": total,
        "priority": priority,
        "priority_label": priority_label,
        "dimensions": dimensions,
        "reasons": reasons,
        "pain_points": pain_points,
        "questions": questions,
        "facts": facts,
        "to_verify": to_verify,
        "is_demo_data": True,
    }


def explain_lead(lead: dict, analysis: dict, llm: LLMClient | None = None) -> str:
    """生成中文跟进判断；模型不可用时使用规则文本兜底。"""
    if llm and llm.configured:
        text = llm.complete(prompts.lead_explanation_prompt(lead, analysis))
        if text:
            return text

    conclusion = (
        f"**结论：建议{ '优先跟进' if analysis['priority'] == 'high' else ('保持关注' if analysis['priority'] == 'medium' else '暂缓跟进') }（{analysis['score']} 分 / {analysis['priority_label']}）**"
    )
    reasons = "\n".join(f"- {reason}" for reason in analysis["reasons"])
    pains = "\n".join(f"- {item}" for item in analysis["pain_points"])
    questions = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(analysis["questions"]))
    return (
        f"{conclusion}\n\n**评分依据**\n{reasons}\n\n"
        f"**可能存在的海外营销痛点**\n{pains}\n\n"
        f"**首次沟通值得验证的问题**\n{questions}\n\n"
        "> 以上为基于模拟资料的规则判断，关键信息需在沟通中确认。"
    )
