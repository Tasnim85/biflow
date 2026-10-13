import asyncio
import ast
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from data_generator import generate_data
from pipeline import run_pipeline,build_artifacts,zip_artifacts
from core.semantic_classifier import classify_dataset
from core.profiling import profile_dataset
from core.quality_engine import assess_quality
from core.cleaning_engine import generate_plan,validate_plan,execute_plan,generate_code
from core.embeddings import EmbeddingEngine
from core.dag_engine import DagEngine
from core.llm_provider import CleaningProvider
from utils.helpers import load_csv

class CoreTests(unittest.TestCase):
    def test_full_pipeline_and_recipe_reuse(self):
        data=generate_data(60); r=run_pipeline(data,{'embedding_backend':'local'},persist_outputs=False)
        self.assertTrue(r['execution']['all_completed'])
        best=r['similarity']['pairs'][0]
        self.assertEqual({best['left'],best['right']},{'customers','clients_2026'})
        self.assertGreater(best['score'],.75)
        self.assertEqual(len(r['final']['integration']['datasets']['transactions_enriched']),180)
        registry={n:{'plan':r['plans'][n],'semantics':r['semantics'][n]} for n in data}
        second=run_pipeline(data,{'embedding_backend':'local'},registry=registry,persist_outputs=False)
        self.assertGreater(second['plans']['clients_2026']['reused_steps'],0)
        for n,item in r['cleaning'].items():
            self.assertGreater(item['after']['score'],r['quality_before'][n]['score'])
            self.assertEqual(item['after']['duplicate_rows'],0)
            self.assertEqual(item['after']['invalid_cells'],0)
            twice=execute_plan(item['cleaned'],r['plans'][n],r['semantics'][n])
            pd.testing.assert_frame_equal(item['cleaned'],twice['cleaned'])
            ast.parse(generate_code(r['plans'][n]))
        artifacts=build_artifacts(r)
        self.assertIn('dag_execution.json',artifacts)
        self.assertIn('similarity_matrix.csv',artifacts)
        self.assertTrue(zip_artifacts(artifacts).startswith(b'PK'))
        for filename,content in artifacts.items():
            if filename.endswith('.json'): json.loads(content)

    def test_semantic_classes_and_safe_transformations(self):
        df=pd.DataFrame({'client_identifier':['001','002'],'full_name':[' Sara ','Adam'],
            'email_address':[' SARA@EXAMPLE.COM ','broken'],'telephone':['00216 20 123 456','123'],
            'customer_age':['30','200'],'signup_date':['31/01/2025','31/02/2025'],
            'location':[' PARIS ','Paris'],'is_active':['yes','false'],
            'url':['https://example.com','bad'],'postal_code':['00100','00101'],'address':['street a','street b'],
            'timestamp':['2025-01-01T12:00:00Z','2025-01-02T10:00:00Z']})
        semantics=classify_dataset(df); types={s['column']:s['semantic_type'] for s in semantics}
        for c,kind in [('client_identifier','IDENTIFIER'),('telephone','PHONE_NUMBER'),('is_active','BOOLEAN'),('postal_code','POSTAL_CODE'),('timestamp','DATETIME')]: self.assertEqual(types[c],kind)
        plan=generate_plan('test',df,semantics,assess_quality(df,semantics)); clean=execute_plan(df,plan,semantics)['cleaned']
        self.assertEqual(clean.client_identifier.iloc[0],'001')
        self.assertEqual(clean.telephone.iloc[0],'+21620123456')
        self.assertEqual(clean.email_address.iloc[0],'sara@example.com')
        self.assertEqual(clean.signup_date.iloc[0],'2025-01-31')
        self.assertEqual(set(clean.location),{'paris'})
        self.assertTrue(pd.isna(clean.customer_age.iloc[1]))

    def test_reject_unsafe_and_unknown_operations(self):
        df=pd.DataFrame({'id':['001']}); semantics=classify_dataset(df)
        for operation,column in [('exec','id'),('strip','unknown'),('convert_numeric','id')]:
            plan={'dataset':'x','steps':[{'operation':operation,'column':column,'explanation':'test'}]}
            with self.assertRaises(ValueError): validate_plan(plan,df,semantics)
        with self.assertRaises(ValueError): validate_plan({'dataset':'x','steps':[{'operation':'strip','column':'id','params':{'code':'import os'},'explanation':'test'}]},df,semantics)

    def test_parallel_dependencies_and_failure_propagation(self):
        def worker(_): time.sleep(.08); return {'done':True}
        functions={'profile':worker,'a':worker,'b':worker,'join':worker}
        dependencies={'profile':[],'a':['profile'],'b':['profile'],'join':['a','b']}
        for backend in ['asyncio','langgraph']:
            run=DagEngine(functions,dependencies,backend=backend).run(); nodes=run['execution']['nodes']
            self.assertTrue(run['execution']['all_completed'])
            self.assertLess(max(nodes['a']['start_offset_seconds'],nodes['b']['start_offset_seconds']),min(nodes['a']['end_offset_seconds'],nodes['b']['end_offset_seconds']))
            self.assertGreaterEqual(nodes['join']['start_offset_seconds'],max(nodes['a']['end_offset_seconds'],nodes['b']['end_offset_seconds']))
        def bad(_): raise RuntimeError('injected error')
        run=DagEngine({'a':bad,'b':worker},{'a':[],'b':['a']}).run()
        self.assertFalse(run['execution']['all_completed']); self.assertIn('Skipped',run['execution']['nodes']['b']['error'])
        with self.assertRaises(ValueError): DagEngine(functions,{'profile':['join'],'a':['profile'],'b':['profile'],'join':['a','b']})

    def test_embedding_order_invariance_and_single_missing_source(self):
        data=generate_data(30); profiles={n:profile_dataset(n,df) for n,df in data.items()}
        engine=EmbeddingEngine(); a=engine.compare_datasets(data,profiles)
        reordered={n:df[df.columns[::-1]] for n,df in data.items()}; b=engine.compare_datasets(reordered,profiles)
        pd.testing.assert_frame_equal(a['matrix'],b['matrix'])
        single={'only':pd.DataFrame({'email':[None,None],'customer_id':['001','002']})}
        r=run_pipeline(single,{'embedding_backend':'local'},persist_outputs=False)
        self.assertTrue(r['execution']['all_completed']); self.assertEqual(r['similarity']['pairs'],[])
        self.assertEqual(r['cleaning']['only']['cleaned'].email.isna().sum(),2)

    def test_csv_delimiters_duplicate_headers_and_leading_zeros(self):
        frame=load_csv(io.BytesIO(b'id;email\n001;a@example.com\n'))
        self.assertEqual(frame.id.iloc[0],'001')
        with self.assertRaises(ValueError): load_csv(io.BytesIO(b'id,id\n1,2\n'))

    def test_llm_fallback_and_unsafe_provider(self):
        df=pd.DataFrame({'id':['001'],'email':[' a@x.com ']}); types=classify_dataset(df); quality=assess_quality(df,types)
        plan=generate_plan('x',df,types,quality); profile=profile_dataset('x',df)
        with patch.dict(os.environ,{},clear=True):
            r=CleaningProvider(True).improve(plan,profile,types,quality,df); self.assertEqual(r['provider'],'local_rules')
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test'}),patch('urllib.request.urlopen',side_effect=TimeoutError):
            r=CleaningProvider(True).improve(plan,profile,types,quality,df); self.assertEqual(r['provider'],'local_fallback')
        evil={'dataset':'x','steps':[{'operation':'exec','column':'id','explanation':'evil'}]}
        payload={'choices':[{'message':{'content':json.dumps(evil)}}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())):
            r=CleaningProvider(True).improve(plan,profile,types,quality,df); self.assertEqual(r['provider'],'local_fallback')

    def test_neural_model_and_missing_package_fallback(self):
        with patch.dict(sys.modules,{'sentence_transformers':None}):
            fallback=EmbeddingEngine('minilm'); self.assertEqual(fallback.backend,'local_hashing'); self.assertIsNotNone(fallback.warning)
        model=Path(__file__).resolve().parents[1]/'models/all-MiniLM-L6-v2/model.safetensors'
        if not model.exists(): self.skipTest('Optional local model not installed; offline fallback tested')
        encoder=EmbeddingEngine('minilm'); self.assertEqual(encoder.backend,'sentence_transformers_minilm',encoder.warning)
        self.assertEqual(encoder.generate_embeddings(['customer email','product price']).shape,(2,384))

if __name__=='__main__': unittest.main()
