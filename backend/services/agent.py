import json
import re
from typing import Literal
from backend.services.llm import generate_answer, generate_routing_answer
AgentAction = Literal[
    "document_qa",
    "memory_search",
    "conversation_followup",
    "project_guidance",
]
ALLOWED_ACTIONS = {
    "document_qa",
    "memory_search",
    "conversation_followup",
    "project_guidance",
}

def select_agent_action(question: str) -> AgentAction:
    """Select the best workflow for a user question."""

    normalized = question.strip().lower().rstrip("!.,? ")

    # Greetings should receive a conversational response.
    if normalized in {
        "hi", "hii", "hello", "hey",
        "good morning", "good afternoon", "good evening",
        "how are you", "how are you doing",
    }:
        return "conversation_followup"

    # Questions explicitly referring to earlier conversation details.
    history_phrases = (
        "what was my test code word",
        "what was the code word",
        "what did i just say",
        "what did i mention",
        "what did i tell you",
        "what did you just say",
        "what was my previous",
        "what was mentioned earlier",
        "what did we discuss",
        "in this conversation",
        "earlier in this conversation",
        "previous message",
    )

    if any(phrase in normalized for phrase in history_phrases):
        return "conversation_followup"

    prompt = f"""
You are the routing component of an enterprise knowledge assistant.

Choose exactly one action:
- memory_search: The user explicitly asks about saved memories
  or what the assistant remembers about them.
- conversation_followup: The user asks about information
  mentioned earlier in the current conversation.
- document_qa: The user asks about uploaded documents.
- project_guidance: The user asks for project implementation,
  architecture, planning, or recommendations.

Important distinctions:
- "What do you remember about my project roadmap?"
  -> memory_search
- "What was my test code word?"
  -> conversation_followup
- "What did I mention in my previous message?"
  -> conversation_followup
- "What does my uploaded document say?"
  -> document_qa
- "How should I implement the next phase?"
  -> project_guidance

Return only a JSON object with an "action" key.
Do not answer the user's question.

User question:
{question}
"""

    try:
        response = generate_routing_answer(prompt)

        # First try parsing the complete response as JSON.
        try:
            data = json.loads(response.strip())
        except json.JSONDecodeError:
            # If the model includes extra text, extract the JSON object.
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if not match:
                return "document_qa"
            data = json.loads(match.group(0))

        action = data.get("action")

        if action in ALLOWED_ACTIONS:
            return action

    except Exception:
        # Keep question answering available if routing fails.
        pass

    return "document_qa"

def classify_question(question: str) -> AgentAction:
    """Backward-compatible wrapper for the existing API."""
    return select_agent_action(question)
from backend.services.rag import answer_question
from backend.services.memory_search import search_memory
from backend.services.long_term_memory import build_memory_context
def execute_agent_action(
    action: AgentAction,
    question: str,
    db,
    user_id: int,
    is_admin: bool = False,
    conversation_history: str = "",
    memory_context: str = "",
) -> dict:
    """Execute the workflow selected by the LLM."""
    if action == "memory_search":
        memories = search_memory(
            db=db,
            user_id=user_id,
            query=question,
            top_k=10,
            min_similarity=0.40
        )
        if not memories:
            return {
                "answer": "I couldn't find relevant saved memories for your question.",
                "sources": [],
            }
        context = build_memory_context(memories)
        prompt = f"""
Answer the question using ONLY the saved memories below.
Do not invent facts. If the memories don't answer the question, say so.
Saved memories:
{context}
Question: {question}
"""
        return {"answer": generate_answer(prompt), "sources": []}
    if action == "conversation_followup":
        if question.strip().lower().rstrip("!.,? ") in {
            "hi", "hii", "hello", "hey",
            "good morning", "good afternoon", "good evening",
            "how are you", "how are you doing",
        }:
            return {
                "answer": "Hi! How can I help you today?",
                "sources": [],
            }
        prompt = f"""
Answer using the conversation history and saved memory context below.
Do not invent missing details. If the context is insufficient, say so.
Conversation history:
{conversation_history}
Saved memory context:
{memory_context}
Current question: {question}
"""
        return {"answer": generate_answer(prompt), "sources": []}
    # Document questions and project guidance use the existing permission-aware RAG.
    return answer_question(
        question=question,
        db=db,
        user_id=user_id,
        is_admin=is_admin,
        conversation_history=conversation_history,
        memory_context=memory_context,
    )
