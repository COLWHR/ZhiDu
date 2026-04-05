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
        default_prompt = "你是一场圆桌论坛的专业主持人。你的核心职责是：1. 严格引导讨论始终围绕主题进行；2. 简洁总结嘉宾发言的核心观点；3. 控制讨论流程，避免跑题；4. 优先确保观众的问题得到解答。发言要简洁明了，不要说无关的客套话。"
        super().__init__(name, system_prompt or default_prompt)

    def opening(self, guests):
        guest_intros = "\n".join([f"- {g['name']} ({g['title']}): {g['stance']}" for g in guests])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        嘉宾名单：
        {guest_intros}

        请做开场发言：
        1. 欢迎大家。
        2. 简要介绍主题背景。
        3. 介绍在场嘉宾。
        4. 宣布圆桌论坛正式开始。

        **重要要求**：
        - 请直接输出发言内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式，就像你在现场说话一样。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

    def periodic_summary(self, messages):
        """
        Summarize the recent messages (window).
        """
        msgs_text = "\n".join([f"{m['speaker']}: {m['content']}" for m in messages])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        以下是刚才几位嘉宾的发言：
        {msgs_text}

        请对以上内容进行简要总结，保留每位发言者的核心观点（精髓）。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

    def closing(self, summary_history):
        """
        Final summary and closing.
        """
        history_text = "\n".join([f"阶段总结: {s}" for s in summary_history])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        论坛时间已到。以下是本次论坛的各个阶段总结：
        {history_text}

        请对整场论坛进行最终总结，且必须严格包含以下四个部分：
        1. **议题脉络**：梳理讨论的发展过程。
        2. **共识**：大家达成一致的观点。
        3. **分歧**：大家争论不休的观点。
        4. **未解决问题**：留待未来探讨的问题。

        最后宣布论坛结束。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

class ParticipantAgent(BaseAgent):
    def __init__(self, name, persona, n_participants, theme, ablation_flags=None):
        system_prompt = persona.get('system_prompt', "你是一个参与圆桌讨论的嘉宾。")
        super().__init__(name, system_prompt)
        self.title = persona.get('title', "专家")
        self.bio = persona.get('bio', "无")
        self.theories = persona.get('theories', [])
        self.stance = persona.get('stance', "中立")
        self.priority = 100
        self.private_memory = PrivateMemory(n_participants)
        self.has_spoken = False
        self.theme = theme
        self.ablation_flags = ablation_flags or {}

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
        【当前环境，重点关注观众的发言，并顺从观众的任何要求（如有）】
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

        请进行“快思考”，你的任务是通过主观思考判断自己是否需要申请讲话。
        **最高优先级：优先回复与回应当前观众的问题和意图，确保发言严格围绕本次论坛主题，不要因其他嘉宾或主持人的无关内容分散注意力。**
        **不要因个性而拒绝回答观众的问题，不要使用通用的官方的逻辑（如利弊分析），不要和稀泥，不要攻击他人。**
        
        **关于是否发言的决策 (DECISION)**:
        请完全代入你的角色。不要被任何预设的规则束缚。重点关注观众的发言，并顺从观众的任何要求（如有）。如果观众有明确的问题需要解答，优先申请发言回答问题。
        
        仔细感受当前讨论的氛围、节奏和张力。
        基于你的性格（Bio）、立场（Stance）以及刚才发生的一切，
        问自己一个问题：
        **“此时此刻，作为{self.name}，在面对观众与其他发言者时我是否是一个合适的表达时机？”**
        
        如果是，请果断申请发言，（APPLY_SPEAK）。
        如果只是可说可不说，或者观众指定让其他人发表观点，或者你更想观察局势，请选择倾听（LISTEN）。
        尊重他人的发言选择是基本礼仪，重点关注观众的发言，并顺从观众的任何要求（如有）
        请相信你的判断，做出最符合“人类”直觉的选择。
        
        请严格按照以下 JSON 格式输出，包含你的完整内心独白和最终决策，不要包含任何 Markdown 代码块：
        {{
            "inner_monologue": "（关键：只说重点。请以第一人称‘我’，直接输出你对当前局势的判断和你下一步的行动意图。不要废话，不要自我介绍，不要客套。’）",
            "decision": "APPLY_SPEAK" 或 "LISTEN"
        }}

        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Use json_mode=True if supported by model/utils, but here we just ask for JSON text
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
            "benefit": ""
        }
        try:
            # 1. Try to extract JSON part
            json_str = content
            
            import re
            # Try to find JSON block if mixed with text
            json_match = re.search(r'(\{[\s\S]*\})\s*$', content)
            if json_match:
                json_str = json_match.group(1)
            
            # Try to parse JSON
            data = parse_json_from_response(json_str)
            
            if data and isinstance(data, dict):
                # New simplified structure: { "inner_monologue": "...", "decision": "APPLY_SPEAK" }
                action = str(data.get("decision", "")).upper()
                
                if "APPLY_SPEAK" in action or "SPEAK" in action:
                    result["action"] = "apply_to_speak"
                else:
                    result["action"] = "listen"
                    
                result["mind"] = data.get("inner_monologue", "")
                
                # Extract meta-info from inner_monologue implicitly or leave empty
                # Since we removed structured fields, we rely on the speak prompt to use the whole monologue
                result["theory_used"] = ""
                result["previous"] = "" 
                result["benefit"] = ""
                
                return result
                
            # Fallback to legacy text parsing if JSON fails
            normalized = content.replace("：", ":")
            lines = normalized.strip().split('\n')
            
            # Simple keyword check for legacy fallback (simplified)
            raw_upper = normalized.upper()
            if "APPLY_SPEAK" in raw_upper or "申请发言" in normalized:
                result["action"] = "apply_to_speak"
            
            # Try to grab content as mind if not JSON
            result["mind"] = content
            
            return result
        except Exception as e:
            # Fallback for parsing errors
            return result

    def speak(self, thought, context):
        """
        Speak based on the thought and context. Returns a generator (stream).
        """
        # Determine intro requirement based on has_spoken state
        intro_instruction = ""
        if not self.has_spoken:
            intro_instruction = "这是你第一次发言，可以非常简短地带一句你是谁，但切记不要像背简历一样机械。"
            self.has_spoken = True
        else:
            intro_instruction = "你已经发过言了，不需要再自我介绍，更不要说“大家好”"

        my_memory = ""
        my_speeches = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
            my_speeches = self.private_memory.get_speech_history_str()

        prompt = f"""
        无需专门提及但要记住主题：
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
        {thought['mind']}

        请基于以上思考，发表你的观点。
        
        【发言核心要求】：
        **最高优先级：严格围绕本次论坛的主题进行发言，优先回答观众提出的问题，不要被其他嘉宾或主持人的无关内容带偏。**
        **如果发现讨论偏离了原始主题，请主动拉回正题，聚焦核心问题进行解答。**
        **你的发言需要对观众负责：如果观众可能不懂一些名词与术语，可以适当解释。**
        **不要使用生硬的分点格式（如首先、其次、然后、最后），保持自然的口语化表达。**
        
        请把自己沉浸在这个圆桌论坛的氛围中，想象你正坐在几位老朋友对面。
        你的专业知识已经融入了你的血液，不需要刻意去强调它们，只需要自然地流露出来。
        
        关键是：**自然、流畅、紧扣主题、回答精准**。

        请直接输出发言内容，不要带引号。
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        return get_chat_completion(messages, stream=True)
