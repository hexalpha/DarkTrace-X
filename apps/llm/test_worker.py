"""Load-path fault tests; GPU failures are simulated, not a GPU performance claim."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import worker


class WorkerLoadTests(unittest.TestCase):
    def setUp(self):
        self.config=worker.Config(local_llm_enabled=True,local_llm_model_path='fixture.gguf',copilot_worker_key='fixture')
        self.state={'state':'OFFLINE','model':'fixture','backend':'CPU','load_failures':0,'loaded_at':None}

    def test_missing_file_is_offline(self):
        with patch.object(worker,'config',self.config),patch.object(worker,'state',self.state),patch.object(worker.Path,'is_file',return_value=False):
            worker.load()
        self.assertEqual(self.state['state'],'OFFLINE')

    def test_gpu_failure_retries_cpu_and_qwen_uses_chatml(self):
        model=SimpleNamespace(metadata={'general.architecture':'qwen3','general.name':'Fixture Qwen'},chat_format='llama-2')
        factory=Mock(side_effect=[RuntimeError('GPU allocation failed'),model])
        library=SimpleNamespace(Llama=factory,llama_supports_gpu_offload=lambda:True)
        with patch.object(worker,'config',self.config),patch.object(worker,'state',self.state),patch.object(worker,'model',None),patch.object(worker.Path,'is_file',return_value=True),patch.dict('sys.modules',{'llama_cpp':library}):
            worker.load()
        self.assertEqual(self.state['state'],'ONLINE')
        self.assertEqual(self.state['backend'],'CPU')
        self.assertEqual(factory.call_args_list[1].kwargs['n_gpu_layers'],0)
        self.assertEqual(model.chat_format,'chatml')

    def test_corrupt_model_reports_error(self):
        library=SimpleNamespace(Llama=Mock(side_effect=ValueError('fixture corrupt model')),llama_supports_gpu_offload=lambda:False)
        with patch.object(worker,'config',self.config),patch.object(worker,'state',self.state),patch.object(worker.Path,'is_file',return_value=True),patch.dict('sys.modules',{'llama_cpp':library}):
            worker.load()
        self.assertEqual(self.state['state'],'ERROR')
        self.assertEqual(self.state['load_failures'],1)
