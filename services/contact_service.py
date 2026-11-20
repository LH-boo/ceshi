"""环节 2：潜在客户联系 —— 个性化首次联系内容 + 跟进计划。"""
from __future__ import annotations

from llm import prompts
from llm.client import LLMClient


def _markets_text(lead: dict) -> str:
    markets = lead.get("target_markets") or []
    if not markets:
        return "your target markets"
    if len(markets) == 1:
        return markets[0]
    return ", ".join(markets[:-1]) + " and " + markets[-1]


def _fallback_follow_up(channel: str) -> list[dict]:
    return [
        {"day": "第 1 天", "channel": channel, "action": "发送首次联系内容，并记录发送时间。"},
        {"day": "第 4 天", "channel": channel, "action": "若无回复，发送简短跟进，补充一个具体的内容选题建议。"},
        {"day": "第 9 天", "channel": channel, "action": "再次联系，附上一份简短的市场内容选题示例（1 页）。"},
        {"day": "随时", "channel": channel, "action": "若对方明确拒绝或要求停止联系，立即停止跟进并记录原因。"},
    ]


def _fallback_email(lead: dict, analysis: dict, goal: str) -> dict:
    company = lead.get("company_name", "your team")
    markets = _markets_text(lead)
    product = lead.get("product", "your product")
    gaps = lead.get("marketing_gaps") or []
    gap_text = gaps[0] if gaps else "your overseas content presence"
    subject = f"Exploring {company}'s growth in {markets}"
    body = (
        f"Hi there,\n\n"
        f"I came across {company} and your work on {product}. From what's publicly available, "
        f"it looks like {markets} is an active focus for you, and that {gap_text} may still be a work in progress.\n\n"
        f"We help AI SaaS teams at exactly this stage with:\n"
        f"- English content and SEO foundations\n"
        f"- LinkedIn content operations\n"
        f"- A lightweight lead capture and follow-up process\n\n"
        f"If it's useful, I'd be happy to share a few specific content angles for {markets} "
        f"and hear how you're approaching the market. Would a 20-minute call next week work for you? "
        f"No deck required.\n\n"
        f"Best regards,\n"
        f"[Your name]\n"
        f"[Company]"
    )
    return {
        "subject": subject,
        "body": body,
        "follow_up_plan": _fallback_follow_up("Email"),
        "notes": "模板生成的演示邮件：仅使用了客户资料中的市场与产品信息，发送前需人工检查，Demo 不会真实发送。",
    }


def _fallback_linkedin(lead: dict, analysis: dict, goal: str) -> dict:
    company = lead.get("company_name", "your team")
    markets = _markets_text(lead)
    gaps = lead.get("marketing_gaps") or []
    gap_text = gaps[0] if gaps else "your overseas content presence"
    subject = f"Quick note on {company}'s {markets} content"
    body = (
        f"Hi, I've been following {company}'s work and noticed {markets} is a focus for you. "
        f"I work with AI SaaS teams on English content, LinkedIn operations and early lead generation. "
        f"If {gap_text} is on your roadmap, I'd be glad to share two or three concrete content angles "
        f"for {markets} — happy to compare notes in a 20-minute call if useful."
    )
    return {
        "subject": subject,
        "body": body,
        "follow_up_plan": _fallback_follow_up("LinkedIn"),
        "notes": "模板生成的 LinkedIn 演示消息：发送前需人工检查，Demo 不会真实发送。",
    }


def generate_contact(
    lead: dict,
    analysis: dict,
    channel: str = "Email",
    goal: str = "预约 20 分钟需求沟通",
    llm: LLMClient | None = None,
) -> dict:
    """生成个性化联系内容；模型不可用时使用模板兜底。"""
    fallback = _fallback_linkedin(lead, analysis, goal) if channel == "LinkedIn" else _fallback_email(lead, analysis, goal)

    if llm and llm.configured:
        data = llm.complete_json(prompts.contact_prompt(lead, analysis, channel, goal))
        if data and data.get("body"):
            plan = data.get("follow_up_plan") or fallback["follow_up_plan"]
            normalized_plan = []
            for item in plan:
                if isinstance(item, dict):
                    normalized_plan.append(
                        {
                            "day": str(item.get("day", "")),
                            "channel": str(item.get("channel", channel)),
                            "action": str(item.get("action", "")),
                        }
                    )
                else:
                    normalized_plan.append({"day": "", "channel": channel, "action": str(item)})
            return {
                "subject": str(data.get("subject") or fallback["subject"]),
                "body": str(data["body"]),
                "follow_up_plan": normalized_plan or fallback["follow_up_plan"],
                "notes": str(data.get("notes") or "AI 生成内容，发送前需人工检查。"),
                "channel": channel,
                "generated_by": "llm",
            }

    fallback.update({"channel": channel, "generated_by": "template"})
    return fallback
