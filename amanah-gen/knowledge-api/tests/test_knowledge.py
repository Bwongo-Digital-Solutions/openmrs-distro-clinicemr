import asyncio
import tempfile
import unittest
from pathlib import Path

import app as knowledge


class KnowledgeRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        knowledge.DB_PATH = Path(self.temp.name) / "knowledge.db"
        knowledge.ACCESS_TOKEN = "unit-test-secret"
        knowledge.initialise()
        with knowledge.connect() as db:
            db.execute("""
                INSERT INTO documents
                (id,title,source,publisher,version,language,content_sha256,status,created_at)
                VALUES ('doc-1','Genetic screening basics','https://example.invalid/source',
                        'Test Publisher','v1','en','test-hash','pending','2026-01-01T00:00:00Z')
            """)
            db.execute("""
                INSERT INTO chunks(id,document_id,ordinal,content)
                VALUES ('chunk-1','doc-1',1,'Genetic screening is a process used to look for selected health conditions.')
            """)
            db.execute("""
                INSERT INTO chunks_fts(chunk_id,document_id,content)
                VALUES ('chunk-1','doc-1','Genetic screening is a process used to look for selected health conditions.')
            """)
            db.commit()

    def tearDown(self):
        self.temp.cleanup()

    def test_pending_document_is_not_retrievable(self):
        result = asyncio.run(knowledge.search(
            knowledge.SearchRequest(question="genetic screening", language="en")
        ))
        self.assertEqual(result["results"], [])

    def test_approved_document_is_retrievable_with_source_metadata(self):
        with knowledge.connect() as db:
            db.execute("UPDATE documents SET status='approved', approved_by='reviewer', approved_at='2026-01-02T00:00:00Z' WHERE id='doc-1'")
            db.commit()
        result = asyncio.run(knowledge.search(
            knowledge.SearchRequest(question="genetic screening", language="en")
        ))
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["document_id"], "doc-1")
        self.assertEqual(result["results"][0]["version"], "v1")

    def test_withdrawn_document_is_not_retrievable(self):
        with knowledge.connect() as db:
            db.execute("UPDATE documents SET status='withdrawn' WHERE id='doc-1'")
            db.commit()
        result = asyncio.run(knowledge.search(
            knowledge.SearchRequest(question="genetic screening", language="en")
        ))
        self.assertEqual(result["results"], [])

    def test_language_filter_is_applied(self):
        with knowledge.connect() as db:
            db.execute("UPDATE documents SET status='approved' WHERE id='doc-1'")
            db.commit()
        result = asyncio.run(knowledge.search(
            knowledge.SearchRequest(question="genetic screening", language="ar")
        ))
        self.assertEqual(result["results"], [])

    def test_internal_token_fails_closed(self):
        with self.assertRaises(Exception) as error:
            knowledge.require_internal_token("wrong-token")
        self.assertEqual(getattr(error.exception, "status_code", None), 401)

    def test_fts_query_quotes_user_input(self):
        query = knowledge.fts_query('screening OR "malicious query"')
        self.assertNotIn('"malicious query"', query)
        self.assertIn('"screening"*', query)


if __name__ == "__main__":
    unittest.main()
