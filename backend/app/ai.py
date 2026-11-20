import httpx

from app.config import settings

ACTIONS = {
    "continue": "从给定文字往后续写一段，保持人称、语气和已有事实，不要重复原文。",
    "expand": "把给定文字扩写得更具体，补充动作、感官和场景，不改变原有情节结论。",
    "polish": "润色给定文字，让句子更顺，不改变情节和人物决定。",
    "rewrite": "改写给定文字，换一种叙述方式，保留关键事实。",
}


def demo_suggestion(action: str, source: str) -> str:
    seed = source.strip() or "夜色压在城门上。"
    snippet = seed[-80:]
    if action == "continue":
        return f"{snippet}风从巷口倒灌进来，灯火晃了一下。他没有回头，只把没说完的话咽了回去。"
    if action == "expand":
        return f"{seed}石阶还带着白日的热气，远处的更鼓一声一声，敲得人心口发紧。"
    if action == "polish":
        return seed.replace("  ", " ").strip() or "灯火在风里晃了一下。"
    return f"他站在原地，听完了{snippet}留下的那半句，终于决定自己走过去。"


async def complete_text(action: str, source: str, context: str) -> tuple[str, str]:
    instruction = ACTIONS[action]
    if not settings.ai_api_key.strip():
        return demo_suggestion(action, source or context), "demo"

    payload = {
        "model": settings.ai_model,
        "temperature": 0.8,
        "messages": [
            {"role": "system", "content": "你是小说写作助手。只输出可直接放入正文的文字，不要标题，不要解释。"},
            {
                "role": "user",
                "content": f"{instruction}\n\n上文节选：\n{context[-1200:]}\n\n需要处理的文字：\n{source or '（从上文末尾续写）'}",
            },
        ],
    }
    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"}
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    text = data["choices"][0]["message"]["content"].strip()
    return text, "model"
