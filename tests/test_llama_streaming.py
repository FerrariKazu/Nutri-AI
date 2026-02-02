import unittest
from unittest.mock import patch, MagicMock, Mock
import json
from backend.llm.llama_cpp_client import LlamaCppClient
from backend.memory_guard import MemoryGuard

class TestLlamaStreaming(unittest.TestCase):
    
    @patch("backend.llm.llama_cpp_client.httpx")
    @patch("backend.memory_guard.MemoryGuard.get_safe_token_limit")
    def test_stream_text_success(self, mock_limit, mock_httpx):
        # Setup
        mock_limit.return_value = 100  # Safe limit
        
        # Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        # Generator for SSE lines
        def line_generator():
            yield 'data: {"choices": [{"delta": {"content": "Hello"}}]}'
            yield 'data: {"choices": [{"delta": {"content": " "}}]}'
            yield 'data: {"choices": [{"delta": {"content": "World"}}]}'
            yield 'data: [DONE]'
            
        mock_response.iter_lines.return_value = line_generator()
        
        # Mock Context Manager
        mock_httpx.stream.return_value.__enter__.return_value = mock_response
        
        # Execution
        client = LlamaCppClient()
        chunks = list(client.stream_text([{"role":"user", "content":"Hi"}]))
        
        # Verification
        self.assertEqual("".join(chunks), "Hello World")
        mock_httpx.stream.assert_called()
        
        # Verify JSON payload
        call_kwargs = mock_httpx.stream.call_args.kwargs
        payload = call_kwargs.get("json", {})
        self.assertEqual(payload.get("max_tokens"), 100)

    @patch("backend.llm.llama_cpp_client.httpx")
    def test_generate_text_json_mode(self, mock_httpx):
        # Setup (Non-streaming)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "```json\n{\"key\": \"value\"}\n```"
                }
            }]
        }
        mock_httpx.post.return_value = mock_response
        
        client = LlamaCppClient()
        result = client.generate_text([{"role":"user", "content":"json pls"}], json_mode=True)
        
        self.assertEqual(result, '{"key": "value"}')
        
    @patch("backend.llm.llama_cpp_client.httpx")
    def test_connection_error(self, mock_httpx):
        # Explicit exception
        mock_httpx.get.side_effect = Exception("Connection Failed")
        
        client = LlamaCppClient()
        # Should not crash init
        
        # Now stream
        mock_httpx.stream.side_effect = Exception("Stream Failed")
        chunks = list(client.stream_text([{"role":"user", "content":"Hi"}]))
        
        self.assertTrue(any("Connection Error" in c for c in chunks))

if __name__ == '__main__':
    unittest.main()
