# arxiv_paper_pulse/chat.py

from typing import List, Dict, Optional
from google import genai
from google.genai import types
from . import config


class PaperChatSession:
    """
    Multi-turn chat session for interactive paper exploration.
    Maintains conversation history with context.
    """

    def __init__(self, papers: List[Dict], model=None, system_instruction=None):
        """
        Initialize chat session with papers.

        Args:
            papers: List of paper dicts to chat about
            model: Model to use (default from config)
            system_instruction: Optional custom system instruction
        """
        self.model = model or config.DEFAULT_MODEL
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.papers = papers

        # Create initial history with paper context
        history = self._create_paper_context(papers)

        # System instruction
        if system_instruction is None:
            system_instruction = """You are a helpful research assistant specializing in analyzing scientific papers.
You can answer questions about the papers provided, compare them, explain concepts, and provide insights.
Be thorough but accessible in your explanations."""

        # Create chat session
        try:
            self.chat = self.client.chats.create(
                model=self.model,
                history=history
            )
        except Exception as e:
            # Fallback: create without config if API structure differs
            self.chat = self.client.chats.create(model=self.model)

    def _create_paper_context(self, papers: List[Dict]) -> List[Dict]:
        """
        Create initial conversation history with paper context.

        Args:
            papers: List of papers

        Returns:
            List of history dicts
        """
        context_parts = ["I have the following research papers to discuss:\n\n"]

        for i, paper in enumerate(papers, 1):
            context_parts.append(f"{i}. {paper.get('title', 'Unknown Title')}\n")
            context_parts.append(f"   URL: {paper.get('url', 'N/A')}\n")
            if paper.get('abstract'):
                context_parts.append(f"   Abstract: {paper.get('abstract')[:500]}...\n")
            context_parts.append("\n")

        context_text = "".join(context_parts)
        context_text += "\nYou can ask me questions about these papers, and I'll provide detailed answers."

        # Create history with user and model messages
        history = [
            {
                "role": "user",
                "parts": [{"text": context_text}]
            },
            {
                "role": "model",
                "parts": [{"text": "I understand. I'm ready to help you explore these research papers. "
                                  "What would you like to know about them?"}]
            }
        ]

        return history

    def ask(self, question: str, use_streaming: bool = False):
        """
        Ask a question about the papers.

        Args:
            question: Question to ask
            use_streaming: If True, return streaming response

        Returns:
            Response text or streaming generator
        """
        if use_streaming:
            response_stream = self.chat.send_message_stream(message=question)
            return response_stream
        else:
            response = self.chat.send_message(message=question)
            return response.text if hasattr(response, 'text') else str(response)

    def get_history(self, curated: bool = True) -> List[Dict]:
        """
        Get conversation history.

        Args:
            curated: If True, exclude empty or invalid parts

        Returns:
            List of message dicts
        """
        history = self.chat.get_history(curated=curated)

        result = []
        for content in history:
            result.append({
                "role": getattr(content, 'role', 'unknown'),
                "text": content.parts[0].text if content.parts else ""
            })

        return result

    def reset(self, papers: Optional[List[Dict]] = None):
        """
        Reset chat session, optionally with new papers.

        Args:
            papers: Optional new list of papers (uses existing if None)
        """
        if papers:
            self.papers = papers

        history = self._create_paper_context(self.papers)
        self.chat = self.client.chats.create(
            model=self.model,
            history=history
        )

