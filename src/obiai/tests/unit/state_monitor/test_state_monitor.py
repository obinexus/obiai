"""
Unit tests for state_monitor
QA_LAYER: UNIT
QA_STANDARD: PolyCore QA Validation Plan
AEGIS_COMPLIANCE: Mathematical verification required
"""

import unittest
from obiai.core.state_monitor.state_monitor import State_monitor
from obiai.core.state_monitor.state_monitor_config import get_config, get_zero_trust_config

class TestState_monitor(unittest.TestCase):
    """Unit tests for State_monitor component"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.default_config = get_config()
        self.zero_trust_config = get_zero_trust_config()
    
    def test_initialization(self):
        """Test component initialization"""
        component = State_monitor(self.default_config)
        self.assertTrue(component.initialized)
        self.assertEqual(component.config['feature_name'], 'state_monitor')
    
    def test_zero_trust_mode(self):
        """Test Zero Trust configuration"""
        component = State_monitor(self.zero_trust_config)
        self.assertTrue(component.validate_integrity())
        self.assertEqual(component.config['security_level'], 'maximum')
    
    def test_processing(self):
        """Test basic processing functionality"""
        component = State_monitor(self.default_config)
        result = component.process({'test': 'data'})
        
        self.assertIn('status', result)
        self.assertEqual(result['status'], 'processed')
        self.assertTrue(result['data_processed'])

if __name__ == '__main__':
    unittest.main()
