"""
Unit tests for protective_barrier
QA_LAYER: UNIT
QA_STANDARD: PolyCore QA Validation Plan
AEGIS_COMPLIANCE: Mathematical verification required
"""

import unittest
from obiai.core.protective_barrier.protective_barrier import Protective_barrier
from obiai.core.protective_barrier.protective_barrier_config import get_config, get_zero_trust_config

class TestProtective_barrier(unittest.TestCase):
    """Unit tests for Protective_barrier component"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.default_config = get_config()
        self.zero_trust_config = get_zero_trust_config()
    
    def test_initialization(self):
        """Test component initialization"""
        component = Protective_barrier(self.default_config)
        self.assertTrue(component.initialized)
        self.assertEqual(component.config['feature_name'], 'protective_barrier')
    
    def test_zero_trust_mode(self):
        """Test Zero Trust configuration"""
        component = Protective_barrier(self.zero_trust_config)
        self.assertTrue(component.validate_integrity())
        self.assertEqual(component.config['security_level'], 'maximum')
    
    def test_processing(self):
        """Test basic processing functionality"""
        component = Protective_barrier(self.default_config)
        result = component.process({'test': 'data'})
        
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'processed')
        self.assertTrue(result['data_processed'])

if __name__ == '__main__':
    unittest.main()
