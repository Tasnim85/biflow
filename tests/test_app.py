import sys
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ui.components import PAGES

class AppTests(unittest.TestCase):
    def button(self,app,label): return next(b for b in app.button if b.label==label)

    def test_review_gate_pages_filters_and_execution(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90).run()
        self.assertEqual(len(app.exception),0)
        next(s for s in app.selectbox if s.label=='Rows per demo dataset').set_value(100)
        self.button(app,'Generate Demo Data').click().run()
        self.button(app,'Analyze selected datasets').click().run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(app.session_state['result']['execution']['all_completed'])
        self.assertFalse(app.session_state['result']['cleaning'])
        for page in PAGES:
            app.sidebar.radio[0].set_value(page).run()
            self.assertEqual(len(app.exception),0,page)
        app.sidebar.radio[0].set_value('Intelligent Cleaning & Transformation').run()
        self.assertTrue(self.button(app,'Approve & Execute').disabled)
        self.button(app,'Preview Cleaning').click().run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(self.button(app,'Approve & Execute').disabled)
        next(c for c in app.checkbox if c.label.startswith('I reviewed the preview')).check()
        next(t for t in app.text_input if t.label=='Approval / rejection reason').set_value('Reviewed demo policy and preview')
        app.run(); self.button(app,'Approve & Execute').click().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.session_state['result']['cleaning']),5)
        for page in PAGES:
            app.sidebar.radio[0].set_value(page).run()
            self.assertEqual(len(app.exception),0,page)
        app.sidebar.radio[0].set_value('Data Quality').run()
        before=app.dataframe[0].value
        next(s for s in app.selectbox if s.label=='Severity').set_value('High').run()
        filtered=app.dataframe[0].value
        self.assertLess(len(filtered),len(before))
        self.assertTrue((filtered.severity=='High').all())
        self.button(app,'Reset Filters').click().run()
        self.assertEqual(len(app.dataframe[0].value),len(before))
        app.sidebar.radio[0].set_value('Overview').run()
        self.button(app,'✓ Profiling').click().run()
        self.assertEqual(app.session_state['nav'],'Data Profiling')

if __name__=='__main__': unittest.main()
