"""各环节的提示词模板。

原则：只允许使用输入资料中明确提供的信息，不编造客户成绩或业务事实。
"""
from __future__ import annotations

import json


def _dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def lead_explanation_prompt(lead: dict, analysis: dict) -> str:
    return f"""请基于下面的客户资料和规则评分结果，用中文写一段简短的跟进判断（Markdown，不超过 250 字）。

客户资料：
{_dump(lead)}

规则评分：
{_dump({k: v for k, v in analysis.items() if k != "reasons"})}

要求：
1. 明确给出「建议优先跟进 / 建议暂缓」的结论，并说明 2–3 个理由，理由必须能对应到资料。
2. 指出 2 个最可能的海外营销痛点，使用审慎表达（例如「可能」「值得验证」）。
3. 列出 3 个首次沟通时需要向客户确认的问题。
4. 不要编造客户成绩、客户名称、融资金额或真实数据。"""


def contact_prompt(lead: dict, analysis: dict, channel: str, goal: str) -> str:
    return f"""你是一名 B2B 海外营销顾问。
请根据下面的客户资料，生成一封简洁、专业、个性化的首次联系内容。

客户资料：
{_dump(lead)}

规则评分与推荐理由：
{_dump({"score": analysis.get("score"), "priority": analysis.get("priority"), "reasons": analysis.get("reasons")})}

联系渠道：{channel}
沟通目标：{goal}

要求：
1. 只使用客户资料中明确提供的信息，不编造客户成绩或业务事实。
2. 点出一个与海外营销有关的潜在问题，但使用审慎表达。
3. 简要说明我们可以提供的服务价值（英文内容、LinkedIn 运营、SEO、线索获取）。
4. 给出一个低门槛的下一步行动，例如预约 20 分钟沟通。
5. 输出 JSON，字段为：subject（邮件主题，若渠道为 LinkedIn 可写一句开场）、body（正文，英文）、follow_up_plan（字符串数组，每项包含时间点和动作）、notes（给销售的人工检查提示，中文）。"""


def proposal_prompt(lead: dict, customer_reply: str) -> str:
    return f"""你是一名海外营销服务商的方案负责人。请根据客户资料和客户回复，整理一份一页式「30 天试点方案」。

客户资料：
{_dump(lead)}

客户回复（模拟）：
{customer_reply}

要求：
1. 只使用资料中明确的信息，不承诺具体曝光量或线索数量。
2. 输出 JSON，字段为：
   title, target_market, duration, current_state, objectives（字符串数组）,
   audience_hypothesis（字符串数组）, services（字符串数组）, workstream（字符串数组）,
   deliverables（字符串数组）, metrics（字符串数组）, open_questions（字符串数组）。
3. 全部用中文表述，服务名称可保留英文术语。"""


def deliverable_prompt(lead: dict, proposal: dict) -> str:
    return f"""你是海外内容运营。请根据客户资料和试点方案，生成一个可预览的交付样例。

客户资料：
{_dump(lead)}

试点方案：
{_dump(proposal)}

要求：
1. 输出 JSON，字段为：
   linkedin_post（一条英文 LinkedIn 内容草稿，80–120 词，包含明确 CTA）,
   topic_plan（数组，每项含 title 与 angle，共 4 条英文选题）,
   notes（中文说明：内容中哪些卖点仍需客户确认）。
2. 不要编造客户数据、客户案例或效果承诺。"""


def review_prompt(metrics: dict, computed: dict) -> str:
    return f"""你是海外营销数据分析师。请根据本轮的模拟营销数据，输出中文复盘。

模拟指标：
{_dump(metrics)}

已计算的指标与对比：
{_dump(computed)}

要求：
1. 输出 JSON，字段为：
   summary（字符串数组，3 条本轮结论）,
   issues（字符串数组，2–3 个问题或风险）,
   next_actions（字符串数组，3–5 条下一轮可执行动作）,
   feedback_to_next_round（字符串数组，2–3 条应反馈到下一轮方案/选题的内容）。
2. 必须引用具体数字或具体内容主题。
3. 明确这是模拟数据，不能描述为真实业绩。"""
