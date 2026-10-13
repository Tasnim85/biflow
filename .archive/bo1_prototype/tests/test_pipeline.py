import sys
from pathlib import Path
import unittest
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data_generator import generate_data
from pipeline import run_pipeline
from core.cleaning_engine import make_plan,apply_plan,generate_code,execute_code
from core.integration_plan import integration_plan,execute_integration
from core.similarity import detect_similarity

class PrototypeTests(unittest.TestCase):
    def test_demo_detects_expected_relationships(self):
        data=generate_data(); r=run_pipeline(data,persist=False)
        self.assertEqual({r['similarity'][0]['left'],r['similarity'][0]['right']},{'customers','clients'})
        self.assertGreater(r['similarity'][0]['score'],.9)
        self.assertEqual(len(r['integrated']['transactions_enriched']),360)
        for item in r['cleaning'].values():
            self.assertGreaterEqual(item['audit']['after']['score'],item['audit']['before']['score'])
            self.assertFalse(item['cleaned'].duplicated().any())

    def test_code_equivalence_and_idempotence(self):
        frame=pd.DataFrame({'customer_id':['001','002','002'],'email':[' A@X.COM ','bad','bad'],'age':['30','-4','-4'],'signup_date':['31/01/2024','invalid','invalid']})
        plan=make_plan(frame); cleaned,audit=apply_plan(frame,plan)
        pd.testing.assert_frame_equal(cleaned,execute_code(frame,generate_code(plan)))
        pd.testing.assert_frame_equal(cleaned,apply_plan(cleaned,plan)[0])
        self.assertEqual(cleaned.customer_id.iloc[0],'001')
        self.assertEqual(cleaned.signup_date.iloc[0],'2024-01-31')
        self.assertTrue(pd.isna(cleaned.email.iloc[1]))
        self.assertEqual(audit['duplicates_removed'],1)

    def test_column_order_invariance_and_unrelated_sources(self):
        data=generate_data(); first=detect_similarity(data)
        shuffled={n:df[df.columns[::-1]] for n,df in data.items()}
        second=detect_similarity(shuffled)
        self.assertEqual([(p['left'],p['right'],p['score']) for p in first],[(p['left'],p['right'],p['score']) for p in second])
        self.assertLess(next(p['score'] for p in first if {p['left'],p['right']}=={'customers','employees'}),.5)

    def test_empty_missing_and_single_source(self):
        frame=pd.DataFrame({'email':pd.Series([None,None],dtype='string'),'customer_id':['01','02']})
        r=run_pipeline({'only':frame},persist=False)
        self.assertEqual(r['similarity'],[])
        self.assertEqual(r['integrated'],{})
        self.assertEqual(r['cleaning']['only']['cleaned'].email.isna().sum(),2)

    def test_no_join_from_nonunique_parent(self):
        data={'parent':pd.DataFrame({'customer_id':[1,1],'name':['a','b']}),'child':pd.DataFrame({'customer_id':[1,1,1],'value':[1,2,3]})}
        plan=integration_plan(data,detect_similarity(data),threshold=.95)
        self.assertEqual(plan['relationships'],[])

if __name__=='__main__': unittest.main()
