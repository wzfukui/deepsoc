import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 将项目根目录添加到 pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 预先设置环境变量，确保导入时能读到
os.environ['LLM_API_KEY'] = 'sk-test'

from app.services import llm_service
from app.services.llm_service import call_llm

class TestLLMService(unittest.TestCase):

    def setUp(self):
        # 强制设置 llm_service 模块中的变量
        llm_service.LLM_API_KEY = 'sk-test'
        # Reset client global
        llm_service._client = None

    @patch('app.services.llm_service.OpenAI')
    @patch('app.services.llm_service.db')
    def test_call_llm_normal(self, mock_db, mock_openai_cls):
        # Setup mock client
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.model = "gpt-test"
        mock_response.id = "req-123"
        # mock_dump must return a dict
        mock_response.model_dump.return_value = {"id": "req-123", "choices": [{"message": {"content": "Test response"}}]}
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Call function
        result = call_llm("System", "User", temperature=0.7)
        
        # Assertions
        self.assertEqual(result, "Test response")
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs['temperature'], 0.7)
        self.assertEqual(kwargs['stream'], False)
        
        # Verify DB save
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @patch('app.services.llm_service.OpenAI')
    @patch('app.services.llm_service.db')
    def test_call_llm_stream(self, mock_db, mock_openai_cls):
        # Setup mock client
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        # Setup mock stream response (generator)
        chunk1 = MagicMock()
        chunk1.choices[0].delta.content = "Hello "
        chunk1.choices[0].delta.reasoning_content = None
        chunk1.id = "req-stream"
        chunk1.model = "gpt-stream"
        
        chunk2 = MagicMock()
        chunk2.choices[0].delta.content = "World"
        chunk2.choices[0].delta.reasoning_content = None
        chunk2.id = "req-stream"
        chunk2.model = "gpt-stream"
        
        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])
        
        # Call function
        generator = call_llm("System", "User", stream=True)
        
        # Consume generator
        content = "".join(list(generator))
        
        # Assertions
        self.assertEqual(content, "Hello World")
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs['stream'], True)
        
        # Verify DB save (should happen after generator is consumed)
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    @patch('app.services.llm_service.OpenAI')
    @patch('app.services.llm_service.db')
    def test_call_llm_json_mode(self, mock_db, mock_openai_cls):
        # Setup mock client
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        mock_response.model = "gpt-test-json"
        mock_response.id = "req-json"
        mock_response.model_dump.return_value = {"id": "req-json", "choices": [{"message": {"content": "{}"}}]}

        mock_client.chat.completions.create.return_value = mock_response
        
        # Call function
        call_llm("System", "User", json_mode=True)
        
        # Assertions
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs['response_format'], {"type": "json_object"})

if __name__ == '__main__':
    unittest.main()
