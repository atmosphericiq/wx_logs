import unittest
import datetime
from wx_logs.tow_calculator import TOWCalculator

class TOWCoverageTestCase(unittest.TestCase):

  def test_tow_full_year_hourly_coverage_ok(self):
    tow = TOWCalculator()
    
    # Add hourly data for full year 2021
    start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
    for day in range(365):
      for hour in range(24):
        current_time = start_date + datetime.timedelta(days=day, hours=hour)
        tow.add_temperature(25.0, current_time)
        tow.add_humidity(85.0, current_time)
    
    # Should have adequate coverage for both temperature and humidity
    self.assertTrue(tow.has_adequate_year_coverage(2021, 'temperature'))
    self.assertTrue(tow.has_adequate_year_coverage(2021, 'humidity'))
    
    temp_coverage = tow.assess_year_coverage(2021, 'temperature')
    humidity_coverage = tow.assess_year_coverage(2021, 'humidity')
    
    self.assertGreaterEqual(temp_coverage['overall_score'], 95.0)
    self.assertGreaterEqual(humidity_coverage['overall_score'], 95.0)

  def test_tow_half_year_coverage_not_ok(self):
    tow = TOWCalculator()
    
    # Add hourly data for only first half of year
    start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
    for day in range(182):  # Half year
      for hour in range(24):
        current_time = start_date + datetime.timedelta(days=day, hours=hour)
        tow.add_temperature(25.0, current_time)
        tow.add_humidity(85.0, current_time)
    
    # Should NOT have adequate coverage
    self.assertFalse(tow.has_adequate_year_coverage(2021, 'temperature'))
    self.assertFalse(tow.has_adequate_year_coverage(2021, 'humidity'))
    
    temp_coverage = tow.assess_year_coverage(2021, 'temperature')
    self.assertLess(temp_coverage['overall_score'], 75.0)

  def test_tow_enhanced_qa_states(self):
    tow = TOWCalculator(threshold=0.5)  # Lower threshold for density
    
    # Add hourly data for full year - should pass both density and coverage
    start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
    for day in range(365):
      for hour in range(24):
        current_time = start_date + datetime.timedelta(days=day, hours=hour)
        tow.add_temperature(25.0, current_time)
        tow.add_humidity(85.0, current_time)
    
    years_with_coverage = tow.get_years_with_coverage()
    year_data = years_with_coverage[2021]
    
    # Should pass enhanced QA
    self.assertEqual(year_data['coverage_analysis']['enhanced_qa_state'], 
      'PASS')
    
    # Traditional QA should also pass
    self.assertEqual(year_data['qa_state'], 'PASS')

  def test_tow_enhanced_qa_fail_coverage(self):
    tow = TOWCalculator(threshold=0.1)  # Very low threshold for density
    
    # Add data only for first 3 months - good density but poor coverage
    start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
    for day in range(90):  # Only first 90 days
      for hour in range(24):
        current_time = start_date + datetime.timedelta(days=day, hours=hour)
        tow.add_temperature(25.0, current_time)
        tow.add_humidity(85.0, current_time)
    
    years_with_coverage = tow.get_years_with_coverage()
    year_data = years_with_coverage[2021]
    
    # Enhanced QA should fail due to poor coverage (coverage-only QA)
    self.assertEqual(year_data['coverage_analysis']['enhanced_qa_state'], 
      'FAIL_COVERAGE')
    
    # Coverage should be inadequate
    coverage = year_data['coverage_analysis']['temperature']
    self.assertFalse(coverage['adequate_coverage'])

  def test_tow_coverage_different_measurement_types(self):
    tow = TOWCalculator()
    
    # Add temperature data for full year
    start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
    for day in range(365):
      for hour in range(0, 24, 6):  # Every 6 hours
        current_time = start_date + datetime.timedelta(days=day, hours=hour)
        tow.add_temperature(25.0, current_time)
    
    # Add humidity data for only half year
    for day in range(182):  # Half year
      for hour in range(0, 24, 6):  # Every 6 hours
        current_time = start_date + datetime.timedelta(days=day, hours=hour)
        tow.add_humidity(85.0, current_time)
    
    # Temperature should have better coverage than humidity
    temp_coverage = tow.assess_year_coverage(2021, 'temperature')
    humidity_coverage = tow.assess_year_coverage(2021, 'humidity')
    
    self.assertGreater(temp_coverage['overall_score'], 
      humidity_coverage['overall_score'])
    self.assertTrue(tow.has_adequate_year_coverage(2021, 'temperature'))
    self.assertFalse(tow.has_adequate_year_coverage(2021, 'humidity'))

  def test_tow_get_years_with_coverage_structure(self):
    tow = TOWCalculator()
    
    # Add some data
    start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
    for day in range(100):
      current_time = start_date + datetime.timedelta(days=day)
      tow.add_temperature(25.0, current_time)
      tow.add_humidity(85.0, current_time)
    
    years_data = tow.get_years_with_coverage()
    year_data = years_data[2021]
    
    # Check that coverage_analysis is added
    self.assertIn('coverage_analysis', year_data)
    
    coverage_analysis = year_data['coverage_analysis']
    
    # Check structure for temperature and humidity
    for measurement_type in ['temperature', 'humidity']:
      self.assertIn(measurement_type, coverage_analysis)
      
      analysis = coverage_analysis[measurement_type]
      expected_keys = ['overall_score', 'seasonal_coverage',
        'monthly_coverage', 'adequate_coverage', 'days_with_data',
        'largest_gap_days']
      
      for key in expected_keys:
        self.assertIn(key, analysis)
    
    # Check enhanced QA state exists and only has valid coverage-only states
    self.assertIn('enhanced_qa_state', coverage_analysis)
    self.assertIn(coverage_analysis['enhanced_qa_state'], 
      ['PASS', 'FAIL_COVERAGE'])  # No FAIL_DENSITY in coverage-only QA

if __name__ == '__main__':
  unittest.main()
