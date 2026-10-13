from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

class AppTests(unittest.TestCase):
    def test_generate_and_render_all_results(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
        self.assertEqual(len(app.exception),0)
        app.sidebar.button[0].click().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.metric[0].value,'5')
        self.assertEqual(len(app.tabs),4)
        self.assertIn('transactions_enriched',app.session_state['results']['integrated'])

if __name__=='__main__': unittest.main()
