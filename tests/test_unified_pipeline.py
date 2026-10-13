"""Unit test for the Unified End-to-End Pipeline (Sarra's Scenario)."""
import unittest
from data.data_generator import generate_dataset
from core.unified_pipeline import run_unified_scenario


class TestUnifiedPipeline(unittest.TestCase):
    def test_run_unified_scenario_synthetic_data(self):
        df = generate_dataset(120, anomaly_rate=0.05, seed=42)
        query = "Quel est le montant moyen des transactions et comparer les depenses ?"
        
        result = run_unified_scenario(
            df_raw=df,
            query=query,
            dataset_name="test_customers.csv",
            policy_version="1.2.0"
        )
        
        # Verify execution
        self.assertIsNotNone(result)
        self.assertEqual(len(result.nodes), 8)
        self.assertTrue(result.total_duration > 0)
        
        # Verify node statuses
        for n_id, node in result.nodes.items():
            self.assertEqual(node.status, "COMPLETED", f"Node {n_id} failed: {node.summary}")
            
        # Verify BO4 components
        self.assertIsNotNone(result.business_answer)
        self.assertIsNotNone(result.chart_recommendation)
        self.assertIn(result.chart_recommendation.chart_type, [
            "bar", "horizontal_bar", "line", "scatter", "donut", "kpi_card", "table"
        ])
        
        # Verify BO2 components
        self.assertIsNotNone(result.cleaned_df)
        self.assertTrue(len(result.lineage_graph["nodes"]) > 0)
        self.assertTrue(len(result.lineage_graph["edges"]) > 0)
        self.assertIn("digraph lineage", result.lineage_dot)
        
        # Verify BO3 components
        self.assertTrue(result.audit_chain_valid)
        self.assertTrue(len(result.drift_summary.get("reports", {})) > 0)


if __name__ == "__main__":
    unittest.main()
