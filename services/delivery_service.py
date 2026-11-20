"""环节 4：执行交付 —— 任务拆解 + 交付样例。"""
from __future__ import annotations

from llm import prompts
from llm.client import LLMClient

DEFAULT_TASKS = [
    {
        "task_id": "task_001",
        "title": "确认目标受众与产品卖点",
        "owner_role": "策略",
        "window": "第 1–2 天",
        "deliverable": "受众画像、卖点表",
        "status": "已完成（模拟）",
    },
    {
        "task_id": "task_002",
        "title": "制定英文内容选题",
        "owner_role": "内容运营",
        "window": "第 3–4 天",
        "deliverable": "选题表",
        "status": "已完成（模拟）",
    },
    {
        "task_id": "task_003",
        "title": "撰写英文内容",
        "owner_role": "内容运营",
        "window": "第 5–10 天",
        "deliverable": "英文内容初稿",
        "status": "进行中（模拟）",
    },
    {
        "task_id": "task_004",
        "title": "发布并记录数据",
        "owner_role": "运营",
        "window": "第 11–25 天",
        "deliverable": "发布记录",
        "status": "待执行（模拟）",
    },
    {
        "task_id": "task_005",
        "title": "汇总数据并复盘",
        "owner_role": "运营 / 分析",
        "window": "第 26–30 天",
        "deliverable": "月度复盘报告",
        "status": "待执行（模拟）",
    },
]

FALLBACK_POST = (
    "Teams lose time when important knowledge is scattered across documents and conversations. "
    "An AI-powered knowledge assistant can help teams find relevant information faster and keep work moving. "
    "If your team is exploring better ways to manage internal knowledge, here's a practical use case to consider: "
    "start with the three documents your team searches for most often, connect them to one assistant, "
    "and measure how often people find answers without asking a colleague.\n\n"
    "Curious how other small teams structure this? We put together a short checklist — comment \"checklist\" "
    "and we'll share it."
)

FALLBACK_TOPICS = [
    {"title": "Why scattered knowledge slows small teams down", "angle": "知识分散带来的时间成本，用具体工作场景切入"},
    {"title": "5 document workflows you can automate with AI", "angle": "文档审阅、周报、FAQ 等可自动化的流程清单"},
    {"title": "A practical guide to building a team knowledge base", "angle": "从 0 到 1 搭建知识库的步骤与常见误区"},
    {"title": "How to evaluate an AI assistant before rolling it out", "angle": "评估维度：准确性、权限、集成与团队接受度"},
]


def create_delivery_tasks(proposal: dict) -> list[dict]:
    """把方案拆成执行任务（Demo 使用固定模板，可按方案阶段调整）。"""
    tasks = []
    for task in DEFAULT_TASKS:
        tasks.append(
            {
                **task,
                "task_id": task["task_id"],
                "proposal_id": proposal.get("proposal_id", "proposal_001"),
            }
        )
    return tasks


def _fallback_sample(lead: dict) -> dict:
    company = lead.get("company_name", "客户")
    return {
        "linkedin_post": FALLBACK_POST,
        "topic_plan": FALLBACK_TOPICS,
        "notes": (
            f"以上内容为 {company} 的演示交付样例：未使用客户真实数据，"
            "发布前需由客户确认产品卖点、可公开案例与 CTA 指向的落地页。"
        ),
        "generated_by": "template",
    }


def generate_deliverable_sample(proposal: dict, lead: dict, llm: LLMClient | None = None) -> dict:
    """生成一条可预览的 LinkedIn 内容草稿与选题表。"""
    sample = _fallback_sample(lead)
    if not (llm and llm.configured):
        return sample

    data = llm.complete_json(prompts.deliverable_prompt(lead, proposal))
    if not data:
        return sample

    if data.get("linkedin_post"):
        sample["linkedin_post"] = str(data["linkedin_post"]).strip()
    topics = []
    for item in data.get("topic_plan") or []:
        if isinstance(item, dict) and item.get("title"):
            topics.append({"title": str(item["title"]), "angle": str(item.get("angle", ""))})
        elif isinstance(item, str) and item.strip():
            topics.append({"title": item.strip(), "angle": ""})
    if topics:
        sample["topic_plan"] = topics
    if data.get("notes"):
        sample["notes"] = str(data["notes"])
    sample["generated_by"] = "llm"
    return sample
