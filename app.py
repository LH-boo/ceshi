"""AI 出海营销助手 Demo（Streamlit）。

五个环节：客户分析 → 客户联系 → 方案撰写 → 执行交付 → 数据复盘。
全部使用模拟数据；模型未配置时自动使用规则 / 模板结果，Demo 仍可完整演示。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from llm.client import LLMClient, build_client
from services.contact_service import generate_contact
from services.delivery_service import create_delivery_tasks, generate_deliverable_sample
from services.lead_service import DIMENSION_LABELS, analyze_lead, explain_lead
from services.proposal_service import generate_proposal, render_proposal_markdown
from services.review_service import review_campaign

BASE_DIR = Path(__file__).resolve().parent
STEPS = ["① 客户分析", "② 客户联系", "③ 方案撰写", "④ 执行交付", "⑤ 数据复盘"]
TASK_STATUS_OPTIONS = ["待执行（模拟）", "进行中（模拟）", "已完成（模拟）"]
DEFAULT_REPLY = (
    "我们希望先验证美国市场，希望在一个月内提升英文内容曝光，并获得一批有价值的潜在客户。"
    "目前团队没有专职海外内容运营人员，希望先做一个小规模试点。"
)


@st.cache_data
def load_leads() -> list[dict]:
    return json.loads((BASE_DIR / "data" / "leads.json").read_text(encoding="utf-8"))


@st.cache_data
def load_metrics() -> dict:
    return json.loads((BASE_DIR / "data" / "campaign_metrics.json").read_text(encoding="utf-8"))


def init_state() -> None:
    defaults = {
        "step": STEPS[0],
        "selected_lead_id": None,
        "contact": None,
        "proposal": None,
        "tasks": None,
        "sample": None,
        "review": None,
        "next_round_feedback": [],
        "customer_reply": DEFAULT_REPLY,
        "explanations": {},
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def goto(index: int) -> None:
    st.session_state.step = STEPS[index]
    st.rerun()


def _set_step(index: int) -> None:
    st.session_state.step = STEPS[index]


def current_lead() -> dict | None:
    selected = st.session_state.get("selected_lead_id")
    if not selected:
        return None
    return next((lead for lead in load_leads() if lead["id"] == selected), None)


def get_llm() -> LLMClient | None:
    if not st.session_state.get("use_llm"):
        return None
    return build_client(
        st.session_state.get("api_key", ""),
        st.session_state.get("base_url", ""),
        st.session_state.get("model", ""),
    )


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_sidebar() -> LLMClient | None:
    st.sidebar.title("AI 出海营销助手")
    st.sidebar.caption("模拟数据 Demo · 不连接真实客户与发送系统")

    st.sidebar.markdown("**演示流程**")
    current_step = st.session_state.step
    for index, label in enumerate(STEPS):
        st.sidebar.button(
            label,
            key=f"nav_{index}",
            use_container_width=True,
            type="primary" if label == current_step else "secondary",
            on_click=_set_step,
            args=(index,),
        )

    with st.sidebar.expander("模型设置（可选）", expanded=False):
        st.checkbox("启用大模型增强", key="use_llm")
        st.text_input("API Key", type="password", key="api_key")
        st.text_input("Base URL", value="https://api.openai.com/v1", key="base_url")
        st.text_input("模型名", value="gpt-4o-mini", key="model")
        st.caption("未启用或调用失败时，自动使用规则 / 模板结果。")

    llm = get_llm()
    if llm and not llm.api_key:
        st.sidebar.warning("已启用模型但未填写 API Key，将使用规则 / 模板结果。")
    elif llm:
        st.sidebar.success(f"模型已启用：{llm.model}")
    else:
        st.sidebar.info("当前为规则 / 模板模式（无模型调用）。")

    if st.sidebar.button("重置演示流程"):
        for key in [
            "selected_lead_id",
            "lead_selector",
            "contact",
            "proposal",
            "tasks",
            "sample",
            "review",
            "next_round_feedback",
            "explanations",
            "customer_reply",
        ]:
            st.session_state.pop(key, None)
        st.session_state.step = STEPS[0]
        st.rerun()

    with st.sidebar.expander("关于本 Demo"):
        st.markdown(
            "流程：客户分析 → 客户联系 → 方案撰写 → 执行交付 → 数据复盘。\n\n"
            "- 客户评分由明确规则计算，AI 只做解释。\n"
            "- 邮件、方案、任务、复盘均为模拟内容，不会对外发送。\n"
            "- 关键信息需人工核验，不把模型推测当成事实。"
        )
    return llm


def step_lead_analysis(llm: LLMClient | None) -> None:
    st.subheader("① 潜在客户分析：优先跟进谁，为什么？")
    st.caption("评分由规则计算（市场 25 + 匹配度 25 + 缺口 25 + 信号 15 + 预算 10），AI 负责解释。")

    leads = load_leads()
    overview = pd.DataFrame(
        [
            {
                "企业": lead["company_name"],
                "行业": lead["industry"],
                "当前市场": lead["current_market"],
                "目标市场": "、".join(lead["target_markets"]) or "未说明",
                "评分": analyze_lead(lead)["score"],
                "优先级": analyze_lead(lead)["priority_label"],
            }
            for lead in leads
        ]
    )
    st.dataframe(overview, hide_index=True, use_container_width=True)

    names = {lead["id"]: lead["company_name"] for lead in leads}
    lead_ids = [lead["id"] for lead in leads]
    company_names = [names[lead_id] for lead_id in lead_ids]
    if st.session_state.get("lead_selector") not in company_names:
        st.session_state.lead_selector = company_names[0]
    selected_name = st.selectbox("选择客户查看详情", options=company_names, key="lead_selector")
    selected = next(lead_id for lead_id in lead_ids if names[lead_id] == selected_name)
    st.session_state.selected_lead_id = selected
    lead = next(item for item in leads if item["id"] == selected)
    analysis = analyze_lead(lead)

    st.divider()
    left, mid, right = st.columns([2, 1, 1])
    with left:
        st.markdown(f"#### {lead['company_name']}")
        st.write(f"**产品：** {lead['product']}")
        st.write(f"**行业：** {lead['industry']}")
        st.write(f"**目标市场：** {'、'.join(lead['target_markets']) or '未说明'}")
        st.caption(f"官网：{lead['website']} · {lead['notes']}")
    with mid:
        st.metric("匹配分", f"{analysis['score']} / 100")
        st.progress(analysis["score"] / 100)
    with right:
        st.metric("优先级", analysis["priority_label"])

    dim_rows = [
        {
            "维度": DIMENSION_LABELS[key],
            "得分": f"{item['score']} / {item['max']}",
            "依据": item["reason"],
        }
        for key, item in analysis["dimensions"].items()
    ]
    st.dataframe(dim_rows, hide_index=True, use_container_width=True)

    col_fact, col_verify = st.columns(2)
    with col_fact:
        st.markdown("**已知事实**")
        st.markdown("\n".join(f"- {item}" for item in analysis["facts"]))
    with col_verify:
        st.markdown("**需要核验 / 确认**")
        st.markdown("\n".join(f"- {item}" for item in analysis["to_verify"]))

    if st.button("生成推荐理由与验证问题（AI）"):
        with st.spinner("正在生成分析说明…"):
            st.session_state.explanations[selected] = explain_lead(lead, analysis, llm)
    if selected in st.session_state.explanations:
        st.markdown(st.session_state.explanations[selected])

    if st.button("生成联系建议并进入第 2 步", type="primary"):
        with st.spinner("正在生成首次联系内容…"):
            contact = generate_contact(lead, analysis, "Email", "预约 20 分钟需求沟通", llm)
        for key in ("contact_subject", "contact_body"):
            st.session_state.pop(key, None)
        st.session_state.contact = {
            **contact,
            "lead_id": lead["id"],
            "analysis_score": analysis["score"],
            "analysis_priority": analysis["priority"],
        }
        goto(1)


def step_contact(llm: LLMClient | None) -> None:
    st.subheader("② 潜在客户联系：准备怎样的联系内容，如何跟进？")
    lead = current_lead()
    if lead is None:
        st.info("请先在第 1 步选择客户。")
        if st.button("返回客户分析"):
            goto(0)
        return

    analysis = analyze_lead(lead)
    contact = st.session_state.contact

    controls, info = st.columns([2, 1])
    with controls:
        channel = st.radio("联系渠道", ["Email", "LinkedIn"], horizontal=True)
        goal = st.text_input("沟通目标", value="预约 20 分钟需求沟通")
        if st.button("生成 / 重新生成联系内容", type="primary"):
            with st.spinner("正在生成联系内容…"):
                result = generate_contact(lead, analysis, channel, goal, llm)
            for key in ("contact_subject", "contact_body"):
                st.session_state.pop(key, None)
            st.session_state.contact = {
                **result,
                "lead_id": lead["id"],
                "analysis_score": analysis["score"],
                "analysis_priority": analysis["priority"],
            }
            st.rerun()
    with info:
        st.metric("客户", lead["company_name"])
        st.metric("匹配分", analysis["score"])

    contact = st.session_state.contact
    if not contact or contact.get("lead_id") != lead["id"]:
        st.info("当前客户尚未生成联系内容，请点击上方按钮生成。")
        return

    st.divider()
    subject = st.text_input("主题", value=contact["subject"], key="contact_subject")
    body = st.text_area("正文（可人工编辑）", value=contact["body"], height=320, key="contact_body")
    contact["subject"] = subject
    contact["body"] = body

    st.markdown("**跟进计划**")
    st.dataframe(
        pd.DataFrame(contact["follow_up_plan"]).rename(
            columns={"day": "时间", "channel": "渠道", "action": "动作"}
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        f"生成方式：{'大模型' if contact.get('generated_by') == 'llm' else '规则 / 模板'}。"
        f"{contact.get('notes', '')} 本 Demo 不会真实发送邮件或消息。"
    )
    if st.button("模拟客户已回复，进入方案撰写 →", type="primary"):
        goto(2)


def step_proposal(llm: LLMClient | None) -> None:
    st.subheader("③ 方案撰写：把客户需求整理成一页式试点方案")
    lead = current_lead()
    if lead is None:
        st.info("请先在第 1 步选择客户。")
        if st.button("返回客户分析"):
            goto(0)
        return

    reply = st.text_area("模拟客户回复（可编辑）", key="customer_reply", height=130)
    feedback = st.session_state.next_round_feedback
    if feedback:
        with st.expander("上一轮复盘反馈（已带入本轮方案）", expanded=False):
            st.markdown("\n".join(f"- {item}" for item in feedback))

    if st.button("生成 30 天试点方案", type="primary"):
        with st.spinner("正在整理方案…"):
            proposal = generate_proposal(lead, reply, llm)
            if feedback:
                proposal["open_questions"] = [
                    f"上一轮复盘建议：{item}" for item in feedback
                ] + proposal["open_questions"]
            st.session_state.proposal = proposal
            st.session_state.tasks = None
            st.session_state.sample = None
        st.rerun()

    proposal = st.session_state.proposal
    if not proposal or proposal.get("lead_id") != lead["id"]:
        st.info("尚未生成方案。填写客户回复后点击上方按钮。")
        return

    st.divider()
    st.markdown(render_proposal_markdown(proposal))
    with st.expander("查看结构化 JSON"):
        st.json({k: v for k, v in proposal.items() if k not in {"is_demo_data"}})
    st.caption(f"生成方式：{'大模型' if proposal.get('generated_by') == 'llm' else '规则 / 模板'}。方案为模拟内容，不代表效果承诺。")
    if st.button("确认方案（模拟），拆解执行任务 →", type="primary"):
        goto(3)


def step_delivery(llm: LLMClient | None) -> None:
    st.subheader("④ 执行交付：把方案变成任务，并展示一个交付样例")
    proposal = st.session_state.proposal
    if not proposal:
        st.info("请先在方案撰写环节生成方案。")
        if st.button("返回方案撰写"):
            goto(2)
        return

    if st.session_state.tasks is None:
        st.session_state.tasks = create_delivery_tasks(proposal)
        st.session_state.pop("task_editor", None)
    tasks = st.session_state.tasks
    completed = sum(1 for task in tasks if task["status"].startswith("已完成"))
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("任务总数", len(tasks))
    col_b.metric("已完成（模拟）", completed)
    col_c.metric("方案周期", proposal["duration"])

    task_df = pd.DataFrame(
        [
            {
                "任务": task["title"],
                "负责人角色": task["owner_role"],
                "时间": task["window"],
                "交付物": task["deliverable"],
                "状态": task["status"],
            }
            for task in tasks
        ]
    )
    edited = st.data_editor(
        task_df,
        hide_index=True,
        use_container_width=True,
        key="task_editor",
        column_config={
            "状态": st.column_config.SelectboxColumn("状态", options=TASK_STATUS_OPTIONS, required=True)
        },
    )
    for task, status in zip(tasks, edited["状态"].tolist()):
        task["status"] = status
    st.caption("任务状态仅保存在当前 Demo 会话中。")

    st.divider()
    st.markdown("**交付样例：一条 LinkedIn 内容草稿**")
    sample = st.session_state.sample
    if not sample:
        if st.button("生成交付样例", type="primary"):
            with st.spinner("正在生成内容样例…"):
                st.session_state.sample = generate_deliverable_sample(proposal, current_lead() or {}, llm)
                st.session_state.pop("linkedin_draft", None)
            st.rerun()
        return

    st.text_area(
        "LinkedIn 草稿（可编辑）",
        value=sample["linkedin_post"],
        height=240,
        key="linkedin_draft",
    )
    st.dataframe(
        pd.DataFrame(sample["topic_plan"]).rename(columns={"title": "英文选题", "angle": "切入角度"}),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(sample["notes"])
    if st.button("进入数据复盘 →", type="primary"):
        goto(4)


def step_review(llm: LLMClient | None) -> None:
    st.subheader("⑤ 数据复盘：判断效果并提出下一轮改进")
    metrics = load_metrics()
    computed = review_campaign(metrics)["computed"]

    st.caption("以下为本轮模拟营销数据（非真实业绩）。")
    cols = st.columns(6)
    cards = [
        ("内容发布", computed["published_posts"]),
        ("总曝光", f"{computed['impressions']:,}"),
        ("总互动", f"{computed['engagements']:,}"),
        ("官网访问", f"{computed['website_visits']:,}"),
        ("潜在线索", computed["leads"]),
        ("有效线索", computed["qualified_leads"]),
    ]
    for column, (label, value) in zip(cols, cards):
        column.metric(label, value)

    check_rows = [
        {
            "指标": check["name"],
            "本轮结果": pct(check["actual"]),
            "试点目标": pct(check["target"]),
            "结论": "达标" if check["passed"] else "未达标",
        }
        for check in computed["target_checks"]
    ]
    st.dataframe(check_rows, hide_index=True, use_container_width=True)

    post_rows = [
        {
            "内容": post["title"],
            "主题": post["topic"],
            "曝光": f"{post['impressions']:,}",
            "互动率": pct(post["engagement_rate"]),
            "官网访问": post["website_visits"],
            "访问率": pct(post["visit_rate"]),
            "线索": post["leads"],
            "有效线索": post["qualified_leads"],
        }
        for post in computed["posts"]
    ]
    st.markdown("**分内容表现**")
    st.dataframe(post_rows, hide_index=True, use_container_width=True)

    if st.button("生成复盘结论与下一轮建议（AI）", type="primary"):
        with st.spinner("正在分析数据…"):
            st.session_state.review = review_campaign(metrics, llm)

    review = st.session_state.review
    if not review:
        return

    st.divider()
    st.markdown("**本轮结论**")
    st.markdown("\n".join(f"- {item}" for item in review["summary"]))
    st.markdown("**问题与风险**")
    st.markdown("\n".join(f"- {item}" for item in review["issues"]))
    st.markdown("**下一轮优化动作**")
    st.markdown("\n".join(f"- {item}" for item in review["next_actions"]))
    st.markdown("**反馈到下一轮方案 / 选题**")
    st.markdown("\n".join(f"- {item}" for item in review["feedback_to_next_round"]))
    st.caption(f"生成方式：{'大模型' if review.get('generated_by') == 'llm' else '规则 / 模板'}。")

    if st.button("把复盘建议带入下一轮方案 →"):
        st.session_state.next_round_feedback = review["feedback_to_next_round"]
        st.session_state.proposal = None
        st.session_state.tasks = None
        st.session_state.sample = None
        goto(2)


def main() -> None:
    st.set_page_config(page_title="AI 出海营销助手 Demo", page_icon="🌍", layout="wide")
    init_state()
    llm = render_sidebar()

    st.title("AI 出海营销助手")
    st.caption(
        "面向海外营销服务商的流程 Demo：发现潜在客户 → 个性化联系 → 试点方案 → 任务交付 → 数据复盘。"
        "全部为模拟数据，AI 生成内容需人工检查。"
    )

    step = st.session_state.step
    if step == STEPS[0]:
        step_lead_analysis(llm)
    elif step == STEPS[1]:
        step_contact(llm)
    elif step == STEPS[2]:
        step_proposal(llm)
    elif step == STEPS[3]:
        step_delivery(llm)
    else:
        step_review(llm)


if __name__ == "__main__":
    main()
