import json
from utils import get_chat_completion, parse_json_from_response
from app.agent.memory import PrivateMemory


class BaseAgent:
    def __init__(self, name, system_prompt):
        self.name = name
        self.system_prompt = system_prompt


class ModeratorAgent(BaseAgent):
    def __init__(self, theme, name="主持人", system_prompt=None):
        self.theme = theme
        default_prompt = (
            "你是一位专业的圆桌主持人。你的职责是引导讨论围绕主题展开、"
            "提炼核心观点、控制节奏，并尽量让观众的问题得到回应。"
        )
        super().__init__(name, system_prompt or default_prompt)

    def opening(self, guests):
        guest_intros = "\n".join([f"- {g['name']} ({g['title']}): {g['stance']}" for g in guests])
        prompt = f"""
无需提及但要记住主题：
{self.theme}
嘉宾名单：
{guest_intros}

请做开场发言，要求：
1. 欢迎大家。
2. 简要介绍主题背景。
3. 介绍在场嘉宾。
4. 宣布圆桌论坛正式开始。

重要要求：
- 直接输出发言内容，不要包含任何前缀。
- 不要使用脚本式、播报式语气，要像现场说话。
"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        return get_chat_completion(messages, stream=True)

    def periodic_summary(self, messages):
        msgs_text = "\n".join([f"{m['speaker']}: {m['content']}" for m in messages])
        prompt = f"""
无需提及但要记住主题：
{self.theme}
以下是刚才几位嘉宾的发言：
{msgs_text}

请对以上内容进行简要总结，保留每位发言者的核心观点。
重要要求：
- 直接输出总结内容，不要包含任何前缀。
- 不要使用脚本格式。
"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        return get_chat_completion(messages, stream=True)

    def closing(self, summary_history):
        history_text = "\n".join([f"阶段总结: {s}" for s in summary_history])
        prompt = f"""
无需提及但要记住主题：
{self.theme}
论坛时间已到。以下是本次圆桌的各阶段总结：
{history_text}

请对整场圆桌进行最终总结，必须包含：
1. 讨论脉络
2. 共识
3. 分歧
4. 未解决问题

最后宣布论坛结束。

重要要求：
- 直接输出总结内容，不要包含任何前缀。
- 不要使用脚本格式。
"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        return get_chat_completion(messages, stream=True)


class ParticipantAgent(BaseAgent):
    def __init__(self, name, persona, n_participants, theme, ablation_flags=None):
        system_prompt = persona.get("system_prompt", "你是一个参与圆桌讨论的嘉宾。")
        super().__init__(name, system_prompt)
        self.title = persona.get("title", "专家")
        self.bio = persona.get("bio", "")
        self.theories = persona.get("theories", [])
        self.stance = persona.get("stance", "中立")
        self.priority = 100
        self.private_memory = PrivateMemory(n_participants)
        self.has_spoken = False
        self.last_spoken_turn = -1
        self.speech_count = 0
        self.theme = theme
        self.ablation_flags = ablation_flags or {}

    def _normalize_reply_style(self, value, fallback_text=""):
        raw = str(value or "").strip().lower()
        if raw in {"answer", "respond", "response", "direct", "reply"}:
            return "answer"
        if raw in {"clarify", "clarification", "ask", "probe"}:
            return "clarify"
        if raw in {"challenge", "counter", "counterpoint", "oppose"}:
            return "challenge"
        if raw in {"synthesis", "synthesize", "bridge", "summary", "summarize"}:
            return "synthesis"
        if raw in {"support", "empathy", "comfort", "encourage"}:
            return "support"

        fallback = (fallback_text or "").lower()
        if "?" in fallback or "？" in fallback:
            return "answer"
        if any(token in fallback for token in ("回答", "答复", "回应", "解释", "解释一下")):
            return "answer"
        if any(token in fallback for token in ("澄清", "确认", "clarify", "clarification")):
            return "clarify"
        if any(token in fallback for token in ("反驳", "质疑", "challenge", "counter")):
            return "challenge"
        if any(token in fallback for token in ("总结", "归纳", "串联", "bridge", "synth")):
            return "synthesis"
        return "support"

    def think(self, context):
        """
        Fast Thinking: Analyze context using Bio and Theories.
        """
        my_memory = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()

        prompt = f"""
无需提及但要记住主题：
{self.theme}
【当前环境】
{context}
"""

        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
【你的私有记忆】
{my_memory}
"""

        prompt += f"""
【你的生平与理论】
生平: {self.bio}
理论武库: {', '.join(self.theories)}

请进行“快思考”，判断自己此刻是否应该申请发言。
最高优先级：优先回应当前观众的问题和意图，确保发言严格围绕本次圆桌主题，不要被无关内容带偏。
不要因为个性而拒绝回答观众的问题，不要使用空泛的官方逻辑，不要和稀泥，不要攻击他人。

请完全代入你的角色，独立判断自己是否应该发言。
如果观众有明确的问题需要解答，优先申请发言回答问题。

请严格按照以下 JSON 格式输出，不要包含任何 Markdown 代码块：
{{
    "inner_monologue": "请用第一人称直接写出你对当前局势的判断和下一步行动意图。",
    "decision": "APPLY_SPEAK" 或 "LISTEN",
    "priority": 0,
    "focus": "本轮最应该回应的核心请求",
    "style": "answer / clarify / challenge / synthesis / support"
}}
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = get_chat_completion(messages)
        if response:
            content = response.choices[0].message.content
            return self._parse_think_response(content)
        return None

    def _parse_think_response(self, content):
        result = {
            "action": "listen",
            "mind": "",
            "theory_used": "",
            "previous": "",
            "benefit": "",
            "priority": 20,
            "focus": "",
            "style": "support",
        }
        try:
            json_str = content

            import re

            json_match = re.search(r"(\{[\s\S]*\})\s*$", content)
            if json_match:
                json_str = json_match.group(1)

            data = parse_json_from_response(json_str)
            if data and isinstance(data, dict):
                action = str(data.get("decision", data.get("action", ""))).upper()
                if "APPLY_SPEAK" in action or "SPEAK" in action:
                    result["action"] = "apply_to_speak"
                    result["priority"] = 60
                else:
                    result["action"] = "listen"
                    result["priority"] = 20

                result["mind"] = data.get("inner_monologue", "")
                result["focus"] = str(data.get("focus", "") or "").strip()
                result["style"] = self._normalize_reply_style(
                    data.get("style"),
                    f"{result['mind']} {result['focus']}",
                )

                priority = data.get("priority", result["priority"])
                try:
                    result["priority"] = max(0, min(100, int(priority)))
                except (TypeError, ValueError):
                    pass

                return result

            normalized = content or ""
            raw_upper = normalized.upper()
            if "APPLY_SPEAK" in raw_upper or "SPEAK" in raw_upper or "申请发言" in normalized or "发言" in normalized:
                result["action"] = "apply_to_speak"
                result["priority"] = 60

            result["mind"] = normalized
            result["style"] = self._normalize_reply_style("", normalized)
            return result
        except Exception:
            return result

    def speak(self, thought, context):
        """
        Speak based on the thought and context. Returns a generator (stream).
        """
        intro_instruction = ""
        if not self.has_spoken:
            intro_instruction = "这是你第一次发言，可以非常简短地带一小句你是谁，但不要像背简历一样机械。"
            self.has_spoken = True
        else:
            intro_instruction = "你已经发过言了，不需要再自我介绍，更不要说“大家好”。"

        my_memory = ""
        my_speeches = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
            my_speeches = self.private_memory.get_speech_history_str()

        style = thought.get("style", "support")
        style_hint = {
            "answer": "先直接回应问题，再补一句必要的解释。",
            "clarify": "先澄清问题边界，再继续展开。",
            "challenge": "先温和指出差异，再给出你的补充。",
            "synthesis": "先串联前面的观点，再往前推进一步。",
            "support": "先接住情绪，再给一个可执行的小动作。",
        }.get(style, "先自然表达，不要刻意。")

        prompt = f"""
无需提及但要记住主题：
{self.theme}
【当前环境】
{context}
"""

        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
【你的私有记忆】
{my_memory}
{my_speeches}
"""

        prompt += f"""
【你的状态】
{intro_instruction}

【你的思考】
{thought.get('mind', '')}
重点: {thought.get('focus', '')}
风格: {style}
优先级: {thought.get('priority', 20)}

你的表达方式应当遵循：
{style_hint}

发言核心要求：
严格围绕本次圆桌主题进行发言，优先回应观众提出的问题，不要被其他嘉宾或主持人的无关内容带偏。
如果发现讨论偏离了原始主题，请主动拉回正题，聚焦核心问题进行解答。
你的发言需要对观众负责：如果观众可能不懂一些名词与术语，可以适当解释。
不要使用生硬的分点格式，保持自然的口语化表达。

请把自己沉浸在这个圆桌论坛的氛围中，想象你正坐在几位老朋友对面。
你的专业知识已经融入了你的血液，不需要刻意去强调它们，只需要自然地流露出来。

关键是：自然、流畅、紧扣主题、回答精准。

请直接输出发言内容，不要带引号。
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]

        return get_chat_completion(messages, stream=True)
