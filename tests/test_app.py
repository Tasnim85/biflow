import sys
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

class AppTests(unittest.TestCase):
    def test_all_nine_pages_and_controlled_execution(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90).run()
        self.assertEqual(len(app.exception),0)
        app.sidebar.slider[0].set_value(30)
        app.sidebar.button[0].click().run()
        self.assertEqual(len(app.session_state['datasets']),5)
        app.sidebar.button[2].click().run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(app.session_state['result']['execution']['all_completed'])
        pages=['Data Sources','Data Profiling','Dataset Similarity — DSO 6','Semantic Classification — DSO 7','Data Quality','Cleaning & Transformation — DSO 5','DAG Orchestration — DSO 1','Final Results']
        for page in pages:
            app.sidebar.radio[0].set_value(page).run()
            self.assertEqual(len(app.exception),0,page)
            if page=='Cleaning & Transformation — DSO 5':
                button=next(b for b in app.button if b.label=='Validate & Execute Cleaning')
                button.click().run(); self.assertEqual(len(app.exception),0)

if __name__=='__main__': unittest.main()
