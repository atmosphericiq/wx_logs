# weather_station_tow_test_case.py
# Tests for the WeatherStation TOW calculator integration
# This tests the end-to-end flow from adding weather readings
# to WeatherStation to getting TOW calculations

import unittest
import datetime
from wx_logs.weather_station import WeatherStation


class WeatherStationTOWTestCase(unittest.TestCase):

  def test_single_year_with_mixed_conditions(self):
    """Test a single year with varying TOW conditions through WeatherStation"""
    station = WeatherStation(reading_type='STATION')
    station.enable_time_of_wetness()
    
    # Generate a full year of data for 2019 with 25% wetness
    random_date = datetime.datetime(2019, 1, 1, 0, 0, 0)
    
    # Add 8760 hours of data (full year)
    for i in range(8760):
      temp = 10  # Always above 0°C threshold
      # Every 4th hour has high humidity (RH > 80%)
      humidity = 85 if i % 4 == 0 else 50
      
      station.add_temp_c(temp, random_date)
      station.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)
    
    # Get TOW results
    tow = station.get_tow()
    years = tow.get_years()
    
    # Verify single year results
    self.assertEqual(len(years.keys()), 1)
    self.assertIn(2019, years.keys())
    
    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], 8760)
    self.assertEqual(data_2019['qa_state'], 'PASS')
    self.assertEqual(data_2019['time_of_wetness_actual'], 2190)  # 25% of 8760
    self.assertEqual(data_2019['time_of_wetness'], round(8760 * 0.25, 2))

  def test_multi_year_different_wetness_patterns(self):
    """Test multi-year TOW calculation with different wetness percentages"""
    station = WeatherStation(reading_type='STATION')
    station.enable_time_of_wetness()
    
    random_date = datetime.datetime(2019, 1, 1, 0, 0, 0)
    
    # Year 1 (2019): 25% wetness (every 4th hour meets TOW conditions)
    for i in range(8760):
      temp = 10  # Always above 0°C threshold
      humidity = 85 if i % 4 == 0 else 50
      station.add_temp_c(temp, random_date)
      station.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    # Year 2 (2020): 75% wetness (3 out of 4 hours meet TOW conditions)
    for i in range(8784):  # 2020 is leap year
      temp = 10  # Always above 0°C threshold
      humidity = 85 if i % 4 != 0 else 50  # Inverted pattern
      station.add_temp_c(temp, random_date)
      station.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    # Get TOW results
    tow = station.get_tow()
    years = tow.get_years()
    averages = tow.get_averages()
    
    # Verify individual years
    self.assertEqual(len(years.keys()), 2)
    
    data_2019 = years[2019]
    self.assertEqual(data_2019['qa_state'], 'PASS')
    self.assertEqual(data_2019['time_of_wetness_actual'], 2190)  # 25% of 8760
    
    data_2020 = years[2020]
    self.assertEqual(data_2020['qa_state'], 'PASS')
    self.assertEqual(data_2020['time_of_wetness_actual'], 6588)  # 75% of 8784
    
    # Verify averages
    self.assertEqual(averages['valid_years'], 2)
    expected_avg = round((2190 + 6588) / (8760 + 8784) * 8760, 0)
    self.assertEqual(averages['annual_time_of_wetness'], expected_avg)

  def test_sparse_data_qa_failure(self):
    """Test that sparse data results in QA failure and exclusion from averages"""
    station = WeatherStation(reading_type='STATION')
    station.enable_time_of_wetness()
    
    # Year 1: Full year of data with 50% wetness
    random_date = datetime.datetime(2020, 1, 1, 0, 0, 0)
    for i in range(8784):  # 2020 is leap year
      temp = 5  # Above 0°C
      humidity = 85 if i % 2 == 0 else 70  # 50% above 80%
      station.add_temp_c(temp, random_date)
      station.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)
    
    # Year 2: Only 10 hours of data (should fail QA)
    for i in range(10):
      random_date = datetime.datetime(2021, 6, 15, i, 0, 0)
      station.add_temp_c(15, random_date)  # Above threshold
      station.add_humidity(85, random_date)  # Above threshold
    
    tow = station.get_tow()
    years = tow.get_years()
    averages = tow.get_averages()
    
    # Verify 2020 passes QA
    data_2020 = years[2020]
    self.assertEqual(data_2020['qa_state'], 'PASS')
    self.assertEqual(data_2020['time_of_wetness_actual'], 4392)  # 50% of 8784
    
    # Verify 2021 fails QA (only 10/8760 = 0.11% coverage)
    data_2021 = years[2021]
    self.assertEqual(data_2021['qa_state'], 'FAIL')
    self.assertEqual(data_2021['total_hours'], 10)
    self.assertEqual(data_2021['time_of_wetness_actual'], 10)
    self.assertEqual(data_2021['time_of_wetness'], None)  # No projection due to QA fail
    
    # Verify only 2020 is included in averages
    self.assertEqual(averages['valid_years'], 1)

  def test_temperature_threshold_filtering(self):
    """Test that temperatures at or below 0°C don't contribute to TOW"""
    station = WeatherStation(reading_type='STATION')
    station.enable_time_of_wetness()
    
    # Add data with temperatures around the 0°C threshold
    test_data = [
      # (temp, humidity, should_count_as_tow)
      (-5, 85, False),   # Below temp threshold
      (0, 85, False),    # At temp threshold (not above)
      (0.1, 85, True),   # Just above temp threshold
      (5, 85, True),     # Well above temp threshold
      (5, 80, False),    # At humidity threshold (not above)
      (5, 81, True),     # Just above humidity threshold
    ]
    
    base_date = datetime.datetime(2020, 1, 1, 0, 0, 0)
    expected_tow_hours = 0
    
    for i, (temp, humidity, should_count) in enumerate(test_data):
      current_date = base_date + datetime.timedelta(hours=i)
      station.add_temp_c(temp, current_date)
      station.add_humidity(humidity, current_date)
      if should_count:
        expected_tow_hours += 1
    
    tow = station.get_tow()
    years = tow.get_years()
    
    data_2020 = years[2020]
    self.assertEqual(data_2020['time_of_wetness_actual'], expected_tow_hours)

  def test_serialization_includes_tow_data(self):
    """Test that WeatherStation serialization includes TOW data"""
    station = WeatherStation(reading_type='STATION')
    station.enable_time_of_wetness()
    
    # Add enough data to pass QA (need >75% of 8784 hours for 2020)
    base_date = datetime.datetime(2020, 1, 1, 0, 0, 0)
    for i in range(7000):  # More than 75% of 8784
      current_date = base_date + datetime.timedelta(hours=i)
      station.add_temp_c(10, current_date)  # Above threshold
      station.add_humidity(85, current_date)  # Above threshold
    
    # Get serialized summary
    summary_json = station.serialize_summary()
    
    # Parse and verify TOW data is included
    import json
    summary = json.loads(summary_json)
    
    self.assertIn('time_of_wetness', summary['air'])
    tow_data = summary['air']['time_of_wetness']
    
    # Should have averages
    self.assertIn('annual_time_of_wetness', tow_data)
    self.assertIn('valid_years', tow_data)
    
    # Should have by_year breakdown
    self.assertIn('by_year', tow_data)
    # Keys are strings in the JSON, not integers
    self.assertIn('2020', tow_data['by_year'])

  def test_dewpoint_integration_with_tow(self):
    """Test that dewpoint calculations properly feed into TOW calculator"""
    station = WeatherStation(reading_type='STATION')
    station.enable_time_of_wetness()
    
    # Add temperature first, then dewpoint at same datetime
    # When dewpoint is added, it calculates humidity and adds to same hour
    base_date = datetime.datetime(2020, 1, 1, 0, 0, 0)
    
    # High dewpoint relative to temperature should result in high RH > 80%
    station.add_temp_c(10, base_date)  # 10°C (this goes to TOW calculator)
    station.add_dewpoint_c(9, 10, base_date)  # Dewpoint 9°C = ~93% RH (this also goes to TOW)
    
    # Verify the calculated humidity is above 80%
    self.assertIn(base_date, station.air_humidity_values)
    calculated_rh = station.air_humidity_values[base_date]
    self.assertGreater(calculated_rh, 80)  # Should be ~93%
    
    # Check that this contributed to TOW calculation  
    tow = station.get_tow()
    years = tow.get_years()
    
    # Should have 1 TOW hour from the high humidity calculated from dewpoint
    data_2020 = years[2020]
    self.assertEqual(data_2020['time_of_wetness_actual'], 1)


if __name__ == '__main__':
  unittest.main()
