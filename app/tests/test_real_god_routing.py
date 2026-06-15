from unittest.mock import MagicMock, patch

from app.agent.real_god import RealGodAgent


def test_real_god_call_llm_uses_nvwa_generate_route():
    agent = RealGodAgent()
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="hello"))]

    with patch("app.agent.real_god.get_chat_completion", return_value=[mock_chunk]) as mock_get:
        events = list(agent._call_llm([{"role": "user", "content": "Create a persona"}]))

    assert events
    assert mock_get.call_args.kwargs["route"] == "nvwa_generate"
