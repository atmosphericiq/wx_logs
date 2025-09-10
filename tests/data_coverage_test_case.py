import unittest
import datetime
from wx_logs import WeatherStation

class DataCoverageTestCase(unittest.TestCase):

  def test_full_year_hourly_data_ok(self):
    """Test case 1: Full year with hourly data should be OK"""
    station = WeatherStation('STATION')
    
    # Add hourly temperature data for full year 2021
    start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
    for day in range(365):  # Full year
      for hour in range(24):  # Every hour
        current_time = start_date + datetime.timedelta(days=day, hours=hour)
        station.add_temp_c(20.0 + (day % 20), current_time)
    
    # Should have adequate year coverage
    self.assertTrue(station.has_adequate_year_coverage('temperature'))
    
    coverage = station.assess_year_coverage('temperature')
    self.assertGreaterEqual(coverage['overall_score'], 95.0)
    self.assertGreaterEqual(coverage['seasonal_coverage'], 95.0)
    self.assertGreaterEqual(coverage['monthly_coverage'], 95.0)

  def test_full_year_daily_data_ok(self):
    """Test case 2: Full year with daily data should be OK"""
    station = WeatherStation('STATION')
    
    # Add daily temperature data for full year 2021
    start_date = datetime.datetime(2021, 1, 1, 12, 0, 0)  # Noon each day
    for day in range(365):  # Full year, once per day
      current_time = start_date + datetime.timedelta(days=day)
      station.add_temp_c(20.0 + (day % 20), current_time)
    
    # Should have adequate year coverage even with daily frequency
    self.assertTrue(station.has_adequate_year_coverage('temperature'))
    
    coverage = station.assess_year_coverage('temperature')
    self.assertGreaterEqual(coverage['overall_score'], 90.0)
    self.assertGreaterEqual(coverage['seasonal_coverage'], 90.0)
    self.assertGreaterEqual(coverage['monthly_coverage'], 90.0)

  def test_full_year_mixed_frequency_ok(self):
    """Test case 3: Full year with daily + sometimes hourly data should be OK"""
    station = WeatherStation('STATION')
    
    # Add daily data for full year
    start_date = datetime.datetime(2021, 1, 1, 12, 0, 0)
    for day in range(365):
      current_time = start_date + datetime.timedelta(days=day)
      station.add_temp_c(20.0 + (day % 20), current_time)
      
      # Add extra hourly data for some days (simulate mixed frequency)
      if day % 10 == 0:  # Every 10th day, add hourly data
        for hour in range(1, 24):  # Add remaining hours for that day
          hourly_time = current_time + datetime.timedelta(hours=hour-12)
          if hourly_time.hour != 12:  # Don't duplicate the noon reading
            station.add_temp_c(20.0 + (day % 20) + hour * 0.1, hourly_time)
    
    # Should still have adequate coverage
    self.assertTrue(station.has_adequate_year_coverage('temperature'))
    
    coverage = station.assess_year_coverage('temperature')
    self.assertGreaterEqual(coverage['overall_score'], 90.0)
    self.assertGreaterEqual(coverage['seasonal_coverage'], 90.0)
    self.assertGreaterEqual(coverage['monthly_coverage'], 90.0)

  def test_half_year_daily_not_ok(self):
    """Test case 4: Half year with daily data should NOT be OK"""
    station = WeatherStation('STATION')
    
    # Add daily data for only first half of year (182 days)
    start_date = datetime.datetime(2021, 1, 1, 12, 0, 0)
    for day in range(182):  # Only first half of year
      current_time = start_date + datetime.timedelta(days=day)
      station.add_temp_c(20.0 + (day % 20), current_time)
    
    # Should NOT have adequate year coverage
    self.assertFalse(station.has_adequate_year_coverage('temperature'))
    
    coverage = station.assess_year_coverage('temperature')
    self.assertLess(coverage['overall_score'], 75.0)  # Should be below threshold
    # Should be missing fall/winter seasons
    self.assertLess(coverage['seasonal_coverage'], 75.0)

  def test_scattered_data_throughout_year_ok(self):
    """Test case: Scattered measurements throughout year should be OK if distributed"""
    station = WeatherStation('STATION')
    
    # Add measurements scattered throughout the year (every 3 days)
    start_date = datetime.datetime(2021, 1, 1, 12, 0, 0)
    for day in range(0, 365, 3):  # Every 3rd day
      current_time = start_date + datetime.timedelta(days=day)
      station.add_temp_c(20.0 + (day % 20), current_time)
    
    # Should have adequate coverage if distributed across seasons
    coverage = station.assess_year_coverage('temperature')
    
    # Even with less frequent data, if well distributed it should pass
    if coverage['seasonal_coverage'] >= 75.0:
      self.assertTrue(station.has_adequate_year_coverage('temperature'))
    else:
      # If not well distributed seasonally, should fail
      self.assertFalse(station.has_adequate_year_coverage('temperature'))

  def test_large_gap_in_middle_not_ok(self):
    """Test case: Large gap in middle of year should NOT be OK"""
    station = WeatherStation('STATION')
    
    # Add data for first 3 months
    start_date = datetime.datetime(2021, 1, 1, 12, 0, 0)
    for day in range(90):  # First 90 days
      current_time = start_date + datetime.timedelta(days=day)
      station.add_temp_c(20.0, current_time)
    
    # Skip 6 months (large gap)
    
    # Add data for last 3 months  
    for day in range(275, 365):  # Last 90 days
      current_time = start_date + datetime.timedelta(days=day)
      station.add_temp_c(20.0, current_time)
    
    # Should NOT have adequate coverage due to large gap
    self.assertFalse(station.has_adequate_year_coverage('temperature'))
    
    coverage = station.assess_year_coverage('temperature')
    self.assertLess(coverage['overall_score'], 75.0)
    # Should show poor seasonal coverage (missing spring/summer)
    self.assertLess(coverage['seasonal_coverage'], 75.0)

  def test_different_measurement_types(self):
    """Test coverage analysis works for different measurement types"""
    station = WeatherStation('STATION')
    
    # Add full year of temperature data
    start_date = datetime.datetime(2021, 1, 1, 12, 0, 0)
    for day in range(365):
      current_time = start_date + datetime.timedelta(days=day)
      station.add_temp_c(20.0, current_time)
    
    # Add only half year of wind data
    for day in range(182):
      current_time = start_date + datetime.timedelta(days=day)
      station.add_wind(5.0, 180, current_time)
    
    # Temperature should have good coverage, wind should not
    self.assertTrue(station.has_adequate_year_coverage('temperature'))
    self.assertFalse(station.has_adequate_year_coverage('wind'))
    
    temp_coverage = station.assess_year_coverage('temperature')
    wind_coverage = station.assess_year_coverage('wind')
    
    self.assertGreater(temp_coverage['overall_score'], wind_coverage['overall_score'])

if __name__ == '__main__':
  unittest.main()
