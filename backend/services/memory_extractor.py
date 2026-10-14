
import json

from backend.services.llm import generate_answer


def extract_memories(conversation_text: str) -> list[str]:
    if len(conversation_text.strip()) < 100:
        return []

    prompt = f"""
You are a long-term memory extraction system for an enterprise AI assistant.

Extract concise, useful, durable facts about the user from the conversation.

Prioritize:
- Technical skills and technologies the user uses
- Ongoing projects and their current progress
- Explicit ongoing learning, interview preparation, and career goals
- Stable preferences and communication preferences
- Explicitly stated constraints that matter in future conversations

Rules:
1. Store only facts supported by the conversation.
2. Preserve important details.
3. Prefer one clear fact per memory.
4. Do not create duplicate memories.
5. Never store temporary events or short-term needs.
6. Do not treat a one-time question as an ongoing goal.
7. Do not infer facts the user did not state.
8. Never extract passwords, API keys, authentication tokens,
   or sensitive personal information.
9. Do not include assistant-generated claims unless confirmed.
10. Preserve distinct additional facts.
11. Return only a valid JSON array of strings.
12. If no useful memories exist, return [].

Conversation:
{conversation_text}
"""

    response = generate_answer(prompt)

    try:
        memories = json.loads(response)

        if not isinstance(memories, list):
            return []

        return [
            memory.strip()
            for memory in memories
            if isinstance(memory, str) and memory.strip()
        ]

    except json.JSONDecodeError:
        return []
