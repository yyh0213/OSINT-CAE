import unittest
import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import json

# Setup mock modules before importing collector modules
mock_feedparser = MagicMock()
sys.modules['feedparser'] = mock_feedparser

mock_trafilatura = MagicMock()
sys.modules['trafilatura'] = mock_trafilatura

mock_qdrant = MagicMock()
sys.modules['qdrant_client'] = mock_qdrant
sys.modules['qdrant_client.models'] = MagicMock()

mock_dateparser = MagicMock()
sys.modules['dateparser'] = mock_dateparser

# Add collector directory to path
collector_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, collector_dir)

# Set environment variables for tests
os.environ["DATA_PATH"] = os.path.join(collector_dir, "config_test")
os.environ["OLLAMA_URL"] = "http://localhost:11434/api/embeddings"
os.environ["QDRANT_HOST"] = "localhost"

# Now import the modules
if 'collector' in sys.modules:
    del sys.modules['collector']
import hooks
import evaluator
import collector

class TestCollectorLogSystem(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Clear database path
        self.test_data_path = os.path.join(collector_dir, "config_test")
        os.makedirs(self.test_data_path, exist_ok=True)
        
        # Setup mock for evaluator DB initialization to run cleanly
        self.sqlite_db_path = os.path.join(self.test_data_path, "reliability.db")
        
    def tearDown(self):
        # Clean up database path
        if os.path.exists(self.test_data_path):
            import shutil
            try:
                shutil.rmtree(self.test_data_path)
            except PermissionError:
                pass # Normal on Windows if sqlite file handle is held

    async def test_hook_manager_pending_tasks(self):
        hm = hooks.HookManager()
        self.assertEqual(hm.pending_tasks, [], "pending_tasks should be empty initially")
        
        async def dummy_callback(*args, **kwargs):
            await asyncio.sleep(0.05)
            return "done"
            
        hm.register("test_event", dummy_callback)
        await hm.trigger("test_event")
        
        self.assertEqual(len(hm.pending_tasks), 1, "Should have 1 task registered in pending_tasks")
        await asyncio.gather(*hm.pending_tasks)

    async def test_evaluator_copycat_articles(self):
        eval_inst = evaluator.SourceEvaluator(
            sqlite_db_path=self.sqlite_db_path,
            qdrant_client=MagicMock(),
            llm_client=MagicMock(),
        )
        self.assertTrue(hasattr(eval_inst, "copycat_articles"), "copycat_articles set should exist")
        self.assertIsInstance(eval_inst.copycat_articles, set, "copycat_articles should be a set")
        
        # Mock LLM call to return delta score less than threshold (e.g. 1.0)
        post_mock = AsyncMock()
        response_mock = MagicMock()
        response_mock.json = MagicMock(return_value={"response": '{"delta": 1.0, "richness": 5.0}'})
        post_mock.return_value = response_mock
        eval_inst.llm = MagicMock()
        eval_inst.llm.post = post_mock
        eval_inst.llm_gen_url = "http://localhost:11434/api/generate"
        
        # Mock qdrant search results to return a prior article
        eval_inst.qdrant = MagicMock()
        mock_point = MagicMock()
        mock_point.score = 0.95
        mock_point.payload = {"source_name": "Prior Source", "timestamp": 100, "content": "Prior content"}
        eval_inst.qdrant.query_points.return_value.points = [mock_point]
        
        # Call on_article_inserted
        payload = {
            "title": "Copycat Article",
            "link": "http://copycat.com",
            "source_name": "Test Source",
            "timestamp": 200,
            "content": "Copycat content"
        }
        vector = [0.1] * 1024
        
        # Step 1 logic mocks to avoid DB lock issues during test
        with patch.object(eval_inst, '_step1_upsert_source', AsyncMock()), \
             patch.object(eval_inst, '_step4_update_scores', AsyncMock()):
            await eval_inst.on_article_inserted(payload, vector)
            
        self.assertEqual(len(eval_inst.copycat_articles), 1, "Should have tracked the copycat article")
        article_info = json.loads(list(eval_inst.copycat_articles)[0])
        self.assertEqual(article_info["title"], "Copycat Article")
        self.assertEqual(article_info["link"], "http://copycat.com")

    async def test_collector_run_crawl_cycle_logging(self):
        # Mock process_feed to simulate a crawl
        async def mock_process_feed(source, db, http_client):
            # Trigger an insertion hook to simulate background work
            await collector.hook_manager.trigger(
                "article_inserted", 
                payload={"title": "Test Art", "link": "http://test.com", "source_name": "Test Source"},
                vector=[0.1] * 1024
            )
            return 1, 2 # 1 article, 2 vectors
            
        # Setup test logs path inside collector
        logs_dir = os.path.join(collector_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Track pre-existing logs to verify the new log creation
        initial_logs = set(os.listdir(logs_dir))
        
        # Mock yaml config load using a conditional open
        original_open = open
        def custom_open(file, *args, **kwargs):
            if str(file).endswith("sources.yaml"):
                from io import StringIO
                return StringIO("sources:\n  - name: Mock Source\n    url: http://mock.com\n")
            return original_open(file, *args, **kwargs)
        
        with patch('collector.process_feed', mock_process_feed), \
             patch('collector.load_db', return_value={}), \
             patch('collector.cleanup_database', AsyncMock()), \
             patch('builtins.open', custom_open):
                 await collector.run_crawl_cycle()
                 
        # Verify log file was created
        current_logs = set(os.listdir(logs_dir))
        new_logs = current_logs - initial_logs
        
        log_files = [f for f in new_logs if f.startswith("collect_") and f.endswith(".json")]
        self.assertEqual(len(log_files), 1, "Log file should be created")
        
        log_path = os.path.join(logs_dir, log_files[0])
        try:
            with open(log_path, 'r', encoding='utf-8') as lf:
                log_data = json.load(lf)
                
            self.assertEqual(log_data["sources_processed"], 1)
            self.assertEqual(log_data["collected_articles_count"], 1)
            self.assertEqual(log_data["created_vectors_count"], 2)
            self.assertIn("elapsed_time_seconds", log_data)
            self.assertIn("timestamp", log_data)
        finally:
            # Clean up the created log file
            if os.path.exists(log_path):
                os.remove(log_path)

if __name__ == "__main__":
    unittest.main()
