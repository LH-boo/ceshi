"""环节 5：数据复盘 —— 指标计算 + 下一轮建议。"""
from __future__ import annotations

from llm import prompts
from llm.client import LLMClient


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _post_rows(metrics: dict) -> list[dict]:
    rows = []
    for post in metrics.get("posts") or []:
        impressions = post.get("impressions", 0)
        visits = post.get("website_visits", 0)
        leads = post.get("leads", 0)
        rows.append(
            {
                "title": post.get("title", ""),
                "topic": post.get("topic", ""),
                "impressions": impressions,
                "engagements": post.get("engagements", 0),
                "website_visits": visits,
                "leads": leads,
                "qualified_leads": post.get("qualified_leads", 0),
                "engagement_rate": _ratio(post.get("engagements", 0), impressions),
                "visit_rate": _ratio(visits, impressions),
                "lead_rate": _ratio(leads, visits),
            }
        )
    return rows


def review_campaign(metrics: dict, llm: LLMClient | None = None) -> dict:
    """计算指标、对比目标，并生成复盘结论与下一轮动作。"""
    impressions = metrics.get("impressions", 0)
    engagements = metrics.get("engagements", 0)
    visits = metrics.get("website_visits", 0)
    leads = metrics.get("leads", 0)
    qualified = metrics.get("qualified_leads", 0)
    targets = metrics.get("targets") or {}
    posts = _post_rows(metrics)

    computed = {
        "published_posts": metrics.get("published_posts", len(posts)),
        "impressions": impressions,
        "engagements": engagements,
        "website_visits": visits,
        "leads": leads,
        "qualified_leads": qualified,
        "engagement_rate": _ratio(engagements, impressions),
        "visit_rate": _ratio(visits, impressions),
        "lead_rate": _ratio(leads, visits),
        "qualified_lead_share": _ratio(qualified, leads),
        "targets": targets,
        "posts": posts,
        "is_demo_data": True,
    }

    by_visit = sorted(posts, key=lambda row: row["visit_rate"], reverse=True)
    best_post = by_visit[0] if by_visit else None
    weakest_post = by_visit[-1] if by_visit else None

    target_checks = [
        {
            "name": "互动率",
            "actual": computed["engagement_rate"],
            "target": targets.get("engagement_rate", 0.025),
        },
        {
            "name": "访问率（曝光 → 官网访问）",
            "actual": computed["visit_rate"],
            "target": targets.get("visit_rate", 0.035),
        },
        {
            "name": "有效线索占比",
            "actual": computed["qualified_lead_share"],
            "target": targets.get("qualified_lead_share", 0.4),
        },
    ]
    for check in target_checks:
        check["passed"] = check["actual"] >= check["target"]
    computed["target_checks"] = target_checks

    best_text = (
        f"「{best_post['title']}」带来 {best_post['website_visits']} 次官网访问，访问率 {_pct(best_post['visit_rate'])}"
        if best_post
        else "暂无可对比内容"
    )
    weakest_text = (
        f"「{weakest_post['title']}」曝光 {weakest_post['impressions']} 但访问率仅 {_pct(weakest_post['visit_rate'])}"
        if weakest_post
        else ""
    )

    summary = [
        f"本轮完成 {computed['published_posts']} 篇内容发布，累计 {impressions:,} 次模拟曝光，"
        f"互动率 {_pct(computed['engagement_rate'])}，访问率 {_pct(computed['visit_rate'])}。",
        f"{qualified} 条有效线索占全部 {leads} 条线索的 {_pct(computed['qualified_lead_share'])}，"
        "说明内容触达了部分目标受众，但仍需人工核验线索质量。",
        f"内容表现分化明显：{best_text}。" + (f"相比之下，{weakest_text}。" if weakest_text else ""),
    ]
    issues = [
        "曝光和线索集中在少数主题上，长尾内容对转化贡献有限。",
        "有效线索仍需人工核验，当前无法判断线索质量是否稳定。",
        "缺少落地页与表单层面的细分数据，难以定位访问到线索的流失点。",
    ]
    next_actions = [
        "下一轮优先围绕表现最好的知识管理主题扩展 2–3 篇内容。",
        "对曝光较高但访问较低的内容，优化 CTA 与落地页信息一致性。",
        "对访问较高但线索较少的页面，检查表单长度、产品价值表达与转化路径。",
        "为每条内容设定唯一的主导 CTA，并按渠道添加 UTM 标记，便于归因。",
    ]
    feedback = [
        "把知识管理主题加入下一轮内容选题表，并提高其内容占比。",
        "在下一轮方案中补充「落地页与表单优化」工作项。",
        "为每篇内容设定明确的线索目标，复盘时按主题对比转化率。",
    ]

    review = {
        "computed": computed,
        "summary": summary,
        "issues": issues,
        "next_actions": next_actions,
        "feedback_to_next_round": feedback,
        "generated_by": "template",
    }

    if llm and llm.configured:
        data = llm.complete_json(prompts.review_prompt(metrics, computed))
        if data:
            for key in ("summary", "issues", "next_actions", "feedback_to_next_round"):
                values = data.get(key)
                if isinstance(values, list) and values:
                    review[key] = [str(item) for item in values]
            review["generated_by"] = "llm"

    return review
