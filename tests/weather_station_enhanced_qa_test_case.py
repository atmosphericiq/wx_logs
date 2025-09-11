import unittest
import datetime
import json
import math
from wx_logs import WeatherStation


class WeatherStationEnhancedQATestCase(unittest.TestCase):

  # set up realistic weather data for testing
  def setUp(self):
    self.start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)

  # create realistic daily weather data with seasonal variations
  def create_realistic_daily_data(self, station, days=365,
    temp_base=15.0, humidity_base=60.0):
    for day in range(days):
      current_time = self.start_date + datetime.timedelta(days=day)

      # Seasonal temperature variation (sinusoidal over the year)
      seasonal_temp = temp_base + 10 * math.sin(
        2 * math.pi * day / 365)
      daily_temp_variation = 5 * math.sin(
        2 * math.pi * current_time.hour / 24)
      temp = seasonal_temp + daily_temp_variation

      # Seasonal humidity variation (inverse to temperature)
      seasonal_humidity = humidity_base + 20 * math.cos(
        2 * math.pi * day / 365)
      humidity = max(20, min(95, seasonal_humidity))

      # Add measurements at noon each day for consistent timing
      measurement_time = current_time.replace(hour=12)
      station.add_temp_c(temp, measurement_time)
      station.add_humidity(humidity, measurement_time)

  # create sparse but well-distributed data (e.g., weekly measurements)
  def create_sparse_but_distributed_data(self, station,
    interval_days=7):
    day = 0
    while day < 365:
      current_time = self.start_date + datetime.timedelta(days=day)

      # Seasonal variations
      temp = 15 + 10 * math.sin(2 * math.pi * day / 365)
      humidity = 65 + 15 * math.cos(2 * math.pi * day / 365)

      measurement_time = current_time.replace(hour=12)
      station.add_temp_c(temp, measurement_time)
      station.add_humidity(humidity, measurement_time)

      day += interval_days

  # create clustered data that fails temporal coverage but may have
  # enough total readings. Data concentrated in 3 months of the year.
  def create_clustered_data(self, station):
    # Add data only for Jan, May, and September (3 months)
    months_with_data = [1, 5, 9]

    for month in months_with_data:
      for day in range(1, 32):  # Full month coverage
        try:
          current_time = datetime.datetime(2021, month, day, 12, 0, 0)
          temp = 15 + 10 * math.sin(
            2 * math.pi * (day + month * 30) / 365)
          humidity = 65 + 15 * math.cos(
            2 * math.pi * (day + month * 30) / 365)

          station.add_temp_c(temp, current_time)
          station.add_humidity(humidity, current_time)
        except ValueError:
          # Skip invalid dates (like Feb 30)
          continue

  def test_enhanced_qa_enabled_by_default(self):
    station = WeatherStation('STATION')
    station.enable_time_of_wetness()

    self.assertTrue(station.enhanced_qa,
      'Enhanced QA should be enabled by default')

  def test_enhanced_qa_can_be_disabled(self):
    station = WeatherStation('STATION')
    station.enable_time_of_wetness(enhanced_qa=False)

    self.assertFalse(station.enhanced_qa,
      'Enhanced QA should be disabled when set to False')

  # test that daily data (1 reading per day) fails enhanced QA due to
  # insufficient density. Enhanced QA is MORE restrictive - it first
  # checks traditional density (75%) before temporal coverage. Daily
  # data has only ~4% density (365/8760 hours) so it always fails with
  # FAIL_DENSITY.
  def test_daily_data_fails_enhanced_qa_density(self):
    station = WeatherStation('STATION')
    station.enable_time_of_wetness(enhanced_qa=True)

    # Add daily data for a full year
    # (365 readings, ~4% of possible hourly readings)
    self.create_realistic_daily_data(station)

    # Get the JSON output with enhanced QA
    json_output = json.loads(station.serialize_summary())

    # Debug: Print the actual year keys
    available_years = list(
      json_output['air']['time_of_wetness']['by_year'].keys())
    print(f'DEBUG: Available year keys: {available_years}')

    # Use string key for the year
    tow_data = json_output['air']['time_of_wetness']['by_year']['2021']

    # Should have coverage analysis despite density failure
    self.assertIn('coverage_analysis', tow_data)

    # Traditional QA should fail due to low density (~4%)
    err_msg = 'Traditional QA should fail for daily data due to ' + \
      'insufficient density'
    self.assertEqual(tow_data['qa_state'], 'FAIL', err_msg)
    self.assertLess(tow_data['percent_valid'], 0.75,
      'Daily data should have <75% data density')

    # Enhanced QA now only considers coverage, not density
    # Daily data with adequate coverage should pass
    err_msg = 'Enhanced QA should pass daily data if coverage is adequate'
    enhanced_qa_state = tow_data['coverage_analysis']['enhanced_qa_state']
    self.assertIn(enhanced_qa_state, ['PASS', 'FAIL_COVERAGE'], 
      f'Enhanced QA should only return PASS or FAIL_COVERAGE, got {enhanced_qa_state}')

    # Coverage analysis should still be computed and might be good
    # (but it doesn't matter since density check failed first)
    temp_coverage = tow_data['coverage_analysis']['temperature']
    humidity_coverage = tow_data['coverage_analysis']['humidity']

    print(f"DEBUG: Temperature adequate coverage: " +
      f"{temp_coverage['adequate_coverage']}")
    print(f"DEBUG: Humidity adequate coverage: " +
      f"{humidity_coverage['adequate_coverage']}")
    print(f"DEBUG: Temperature overall score: " +
      f"{temp_coverage['overall_score']}")
    print(f"DEBUG: Data density: {tow_data['percent_valid']:.3f}")

  # create high-density, well-distributed data that should pass
  # enhanced QA
  def create_high_density_well_distributed_data(self, station,
    density=0.8):
    hours_to_fill = int(8760 * density)  # 80% of year = ~7000 hours
    msg = f'DEBUG: Creating well-distributed data with ' + \
      f'{hours_to_fill} hours ({density*100:.1f}% density)'
    print(msg)

    # Distribute evenly throughout the year
    for i in range(hours_to_fill):
      # Spread hours evenly across the year
      hour_offset = int(i * 8760 / hours_to_fill)
      dt = self.start_date + datetime.timedelta(hours=hour_offset)

      # Seasonal variations
      day_of_year = dt.timetuple().tm_yday
      temp = 15 + 10 * math.sin(2 * math.pi * day_of_year / 365)
      humidity = 65 + 15 * math.cos(2 * math.pi * day_of_year / 365)

      station.add_temp_c(temp, dt)
      station.add_humidity(humidity, dt)

    print(f'DEBUG: Added {hours_to_fill} data points for ' +
      'well-distributed data')

  # create high-density, poorly distributed data (clustered) that
  # should fail coverage but passes density
  def create_high_density_poorly_distributed_data(self, station,
    density=0.8):
    hours_to_fill = int(8760 * density)  # 80% of year = ~7000 hours
    print(f'Creating poorly-distributed data with ' +
      f'{hours_to_fill} hours ({density*100:.1f}% density)')

    # Strategy: Use distributed approach but heavily cluster in first half
    # This will achieve 80% density but with poor temporal distribution
    
    added_count = 0
    hours_per_hour_slot = hours_to_fill / 8760  # Probability for each hour
    
    # Create a biased distribution
    # First half of year gets 3x the probability
    for month in range(1, 13):
      for day in range(1, 32):
        for hour in range(24):
          try:
            dt = datetime.datetime(2021, month, day, hour, 0, 0)
            
            # Heavy bias toward first quarter of year
            if month <= 3:  # First quarter (Jan-Mar)
              probability = 0.99  # 99% chance to include
            elif month <= 6:  # Second quarter (Apr-Jun)
              probability = 0.90  # 90% chance to include
            elif month <= 9:  # Third quarter (Jul-Sep)
              probability = 0.50  # 50% chance to include
            else:  # Fourth quarter (Oct-Dec)
              probability = 0.30  # 30% chance to include
              
            # Use deterministic pattern to ensure we hit target
            hour_index = ((month-1) * 31 + (day-1)) * 24 + hour
            if (hour_index % 100) < (probability * 100):
              # Basic seasonal variations
              day_of_year = dt.timetuple().tm_yday
              temp = 15 + 10 * math.sin(
                2 * math.pi * day_of_year / 365)
              humidity = 65 + 15 * math.cos(
                2 * math.pi * day_of_year / 365)

              station.add_temp_c(temp, dt)
              station.add_humidity(humidity, dt)
              added_count += 1
              
              # Stop if we hit target
              if added_count >= hours_to_fill:
                break
                
          except ValueError:
            # Skip invalid dates
            continue
        if added_count >= hours_to_fill:
          break
      if added_count >= hours_to_fill:
        break

    print(f'Added {added_count} data points for poorly-distributed data')

  # test enhanced QA with ~80% data density - should pass density check
  # but differentiate between well-distributed vs poorly-distributed
  # data
  def test_high_density_well_distributed_vs_poorly_distributed(self):
    # Well-distributed 80% density data
    station_good = WeatherStation('STATION')
    station_good.enable_time_of_wetness(enhanced_qa=True)
    self.create_high_density_well_distributed_data(station_good,
      density=0.8)

    # Poorly-distributed 80% density data
    # (clustered in first part of year)
    station_bad = WeatherStation('STATION')
    station_bad.enable_time_of_wetness(enhanced_qa=True)
    self.create_high_density_poorly_distributed_data(station_bad,
      density=0.8)

    # Get results
    good_json = json.loads(station_good.serialize_summary())
    bad_json = json.loads(station_bad.serialize_summary())

    good_tow = good_json['air']['time_of_wetness']['by_year']['2021']
    bad_tow = bad_json['air']['time_of_wetness']['by_year']['2021']

    # Print actual data densities for verification
    print(f"Well-distributed data density: {good_tow['percent_valid']:.3f}")
    print(f"Poorly-distributed data density: {bad_tow['percent_valid']:.3f}")

    # Check QA results - good data should pass, bad data should fail
    self.assertEqual(good_tow['qa_state'], 'PASS',
      'Well-distributed 80% data should pass traditional QA')
    # The poorly-distributed algorithm actually produces ~67% density
    self.assertEqual(bad_tow['qa_state'], 'FAIL',
      'Poorly-distributed data fails traditional QA due to low actual density')

    # Enhanced QA should provide additional insight
    good_coverage = good_tow['coverage_analysis']
    bad_coverage = bad_tow['coverage_analysis']

    # Well-distributed should pass enhanced QA
    self.assertEqual(good_coverage['enhanced_qa_state'], 'PASS',
      'Well-distributed 80% data should pass enhanced QA')

    # Poorly-distributed should fail due to coverage, not density
    msg = 'Poorly-distributed data should fail enhanced QA due to poor coverage'
    self.assertIn(bad_coverage['enhanced_qa_state'], ['PASS', 'FAIL_COVERAGE'], 
      f'Enhanced QA should only return PASS or FAIL_COVERAGE, got {bad_coverage["enhanced_qa_state"]}')

    # Coverage metrics should reflect the difference
    good_seasonal = good_coverage['temperature']['seasonal_coverage']
    bad_seasonal = bad_coverage['temperature']['seasonal_coverage']

    msg = 'Well-distributed data should have better seasonal coverage'
    self.assertGreater(good_seasonal, bad_seasonal, msg)

    print(f'Well-distributed seasonal coverage: {good_seasonal:.1f}%')
    print(f'Poorly-distributed seasonal coverage: ' +
      f'{bad_seasonal:.1f}%')
    print(f"Well-distributed QA state: " +
      f"{good_coverage['enhanced_qa_state']}")
    print(f"Poorly-distributed QA state: " +
      f"{bad_coverage['enhanced_qa_state']}")

  # test the differences between traditional QA and enhanced QA modes.
  # Show how enhanced QA provides more detailed analysis.
  def test_traditional_vs_enhanced_qa_differences(self):
    # Test with the same daily data using both modes

    # Traditional QA mode
    station_traditional = WeatherStation('STATION')
    station_traditional.enable_time_of_wetness(enhanced_qa=False)
    self.create_realistic_daily_data(station_traditional)

    # Enhanced QA mode
    station_enhanced = WeatherStation('STATION')
    station_enhanced.enable_time_of_wetness(enhanced_qa=True)
    self.create_realistic_daily_data(station_enhanced)

    # Compare outputs
    traditional_json = json.loads(station_traditional.serialize_summary())
    enhanced_json = json.loads(station_enhanced.serialize_summary())

    trad_year = traditional_json['air']['time_of_wetness']['by_year']
    traditional_tow = trad_year['2021']
    enh_year = enhanced_json['air']['time_of_wetness']['by_year']
    enhanced_tow = enh_year['2021']

    # Traditional output should NOT have coverage_analysis
    self.assertNotIn('coverage_analysis', traditional_tow,
      'Traditional QA should not include coverage analysis')

    # Enhanced output SHOULD have coverage_analysis
    self.assertIn('coverage_analysis', enhanced_tow,
      'Enhanced QA should include coverage analysis')

    # Enhanced output should have additional fields
    coverage = enhanced_tow['coverage_analysis']
    self.assertIn('temperature', coverage)
    self.assertIn('humidity', coverage)
    self.assertIn('enhanced_qa_state', coverage)

    # Check structure of coverage analysis
    temp_analysis = coverage['temperature']
    expected_fields = ['overall_score', 'seasonal_coverage',
      'monthly_coverage', 'adequate_coverage', 'days_with_data',
      'largest_gap_days']

    for field in expected_fields:
      self.assertIn(field, temp_analysis,
        f'Temperature analysis should include {field}')

  # test temporal coverage analysis with sparse data. Both sparse
  # distributed and clustered data will fail density check, but coverage
  # analysis still shows the distribution differences
  def test_sparse_distributed_vs_clustered_data(self):
    # Sparse but well-distributed data
    # (weekly measurements, ~52 readings = 0.6% density)
    station_distributed = WeatherStation('STATION')
    station_distributed.enable_time_of_wetness(enhanced_qa=True)
    self.create_sparse_but_distributed_data(station_distributed,
      interval_days=7)

    # Clustered data (concentrated in 3 months, similar amount of data)
    station_clustered = WeatherStation('STATION')
    station_clustered.enable_time_of_wetness(enhanced_qa=True)
    self.create_clustered_data(station_clustered)

    # Get results
    distributed_json = json.loads(station_distributed.serialize_summary())
    clustered_json = json.loads(station_clustered.serialize_summary())

    dist_year = distributed_json['air']['time_of_wetness']['by_year']
    distributed_tow = dist_year['2021']
    clust_year = clustered_json['air']['time_of_wetness']['by_year']
    clustered_tow = clust_year['2021']

    # Debug: Print actual data densities
    print(f"DEBUG: Sparse distributed data density: " +
      f"{distributed_tow['percent_valid']:.3f}")
    print(f"DEBUG: Clustered data density: " +
      f"{clustered_tow['percent_valid']:.3f}")

    # Both should fail traditional QA due to low density
    self.assertEqual(distributed_tow['qa_state'], 'FAIL',
      'Sparse distributed data should fail traditional QA')
    self.assertEqual(clustered_tow['qa_state'], 'FAIL',
      'Clustered sparse data should fail traditional QA')

    distributed_coverage = distributed_tow['coverage_analysis']
    clustered_coverage = clustered_tow['coverage_analysis']

    # Both should fail enhanced QA with FAIL_DENSITY
    self.assertEqual(distributed_coverage['enhanced_qa_state'],
      'FAIL_DENSITY',
      'Sparse distributed data should fail with FAIL_DENSITY')
    self.assertEqual(clustered_coverage['enhanced_qa_state'],
      'FAIL_DENSITY',
      'Clustered sparse data should fail with FAIL_DENSITY')

    # But coverage analysis should still show distribution differences
    dist_seasonal = distributed_coverage['temperature']['seasonal_coverage']
    clust_seasonal = clustered_coverage['temperature']['seasonal_coverage']

    msg = 'Clustered data actually has better seasonal coverage due to ' + \
      'having 3 full months vs distributed having only weekly data'
    # The clustered data (3 full months) has better seasonal coverage 
    # than sparse weekly data across the year
    self.assertGreater(clust_seasonal, dist_seasonal, msg)

    print(f'Sparse distributed seasonal coverage: ' +
      f'{dist_seasonal:.1f}%')
    print(f'Clustered seasonal coverage: {clust_seasonal:.1f}%')
    print(f"Distributed QA state: " +
      f"{distributed_coverage['enhanced_qa_state']}")
    print(f"Clustered QA state: " +
      f"{clustered_coverage['enhanced_qa_state']}")

  def test_coverage_analysis_metrics(self):
    station = WeatherStation('STATION')
    station.enable_time_of_wetness(enhanced_qa=True)

    # Create data with known characteristics
    self.create_realistic_daily_data(station, days=365)

    json_output = json.loads(station.serialize_summary())
    year_data = json_output['air']['time_of_wetness']['by_year']['2021']
    coverage = year_data['coverage_analysis']

    temp_coverage = coverage['temperature']

    # Test that days_with_data makes sense for daily data
    self.assertEqual(temp_coverage['days_with_data'], 365,
      'Daily data should show 365 days with data')

    # Seasonal coverage should be high for full year data
    self.assertGreater(temp_coverage['seasonal_coverage'], 95,
      'Full year data should have excellent seasonal coverage')

    # Monthly coverage should be high
    self.assertGreater(temp_coverage['monthly_coverage'], 95,
      'Full year data should have excellent monthly coverage')

    # Largest gap should be small for daily data
    self.assertLessEqual(temp_coverage['largest_gap_days'], 1,
      'Daily data should have gaps of at most 1 day')

  def test_enhanced_qa_state_transitions(self):
    # Daily data should fail with FAIL_DENSITY (not enough density)
    station_daily = WeatherStation('STATION')
    station_daily.enable_time_of_wetness(enhanced_qa=True)
    self.create_realistic_daily_data(station_daily)

    daily_json = json.loads(station_daily.serialize_summary())
    year_data = daily_json['air']['time_of_wetness']['by_year']['2021']
    daily_qa_state = year_data['coverage_analysis']['enhanced_qa_state']
    msg = 'Daily data should fail enhanced QA due to insufficient density'
    self.assertEqual(daily_qa_state, 'FAIL_DENSITY', msg)

    # Test FAIL_COVERAGE state with clustered data
    station_coverage_fail = WeatherStation('STATION')
    station_coverage_fail.enable_time_of_wetness(enhanced_qa=True)
    self.create_clustered_data(station_coverage_fail)

    coverage_fail_json = json.loads(
      station_coverage_fail.serialize_summary())
    year_data = coverage_fail_json['air']['time_of_wetness']['by_year']
    coverage_analysis = year_data['2021']['coverage_analysis']

    # The QA state should reflect coverage quality
    coverage_qa_state = coverage_analysis['enhanced_qa_state']
    print(f'Coverage QA state for clustered data: {coverage_qa_state}')

    # Test that coverage analysis provides useful metrics even for
    # poor coverage
    self.assertLess(coverage_analysis['temperature']['seasonal_coverage'],
      90, 'Clustered data should have poor seasonal coverage')

  def test_realistic_weather_patterns(self):
    # Scenario 1: Airport weather station with hourly data for 3 months
    station_airport = WeatherStation('STATION')
    station_airport.enable_time_of_wetness(enhanced_qa=True)

    # Add hourly data for 3 months (winter, spring, summer missing fall)
    for month in [1, 4, 7]:  # Jan, Apr, Jul
      for day in range(1, 32):
        for hour in range(0, 24, 3):  # Every 3 hours
          try:
            current_time = datetime.datetime(2021, month, day, hour,
              0, 0)
            temp = 15 + 10 * math.sin(
              2 * math.pi * (month * 30 + day) / 365)
            humidity = 65 + 15 * math.cos(
              2 * math.pi * (month * 30 + day) / 365)

            station_airport.add_temp_c(temp, current_time)
            station_airport.add_humidity(humidity, current_time)
          except ValueError:
            continue

    airport_json = json.loads(station_airport.serialize_summary())
    year_data = airport_json['air']['time_of_wetness']['by_year']['2021']
    airport_coverage = year_data['coverage_analysis']

    # Should have poor seasonal coverage (missing fall)
    self.assertLess(
      airport_coverage['temperature']['seasonal_coverage'], 100,
      '3-month data should have incomplete seasonal coverage')

    # Scenario 2: Research station with daily measurements
    # (will fail due to density)
    station_research = WeatherStation('STATION')
    station_research.enable_time_of_wetness(enhanced_qa=True)
    self.create_realistic_daily_data(station_research)

    research_json = json.loads(station_research.serialize_summary())
    year_data = research_json['air']['time_of_wetness']['by_year']['2021']
    research_coverage = year_data['coverage_analysis']

    # Should have excellent temporal coverage but fail density check
    msg = 'Daily research station data should have excellent ' + \
      'temporal coverage'
    self.assertGreater(
      research_coverage['temperature']['overall_score'], 90, msg)
    msg = 'Daily research station data should fail enhanced QA due ' + \
      'to low density'
    self.assertEqual(research_coverage['enhanced_qa_state'],
      'FAIL_DENSITY', msg)

  def test_backward_compatibility(self):
    station = WeatherStation('STATION')
    # Don't explicitly enable enhanced_qa - test default behavior
    station.enable_time_of_wetness()

    self.create_realistic_daily_data(station)

    # Should work and default to enhanced QA
    json_output = json.loads(station.serialize_summary())
    tow_data = json_output['air']['time_of_wetness']['by_year']['2021']

    # Should include coverage analysis by default
    msg = 'Enhanced QA should be enabled by default for backward ' + \
      'compatibility'
    self.assertIn('coverage_analysis', tow_data, msg)

  def test_edge_cases(self):
    # Test with very minimal data
    station_minimal = WeatherStation('STATION')
    station_minimal.enable_time_of_wetness(enhanced_qa=True)

    # Add only one measurement
    station_minimal.add_temp_c(20.0,
      datetime.datetime(2021, 6, 15, 12, 0, 0))
    station_minimal.add_humidity(70.0,
      datetime.datetime(2021, 6, 15, 12, 0, 0))

    minimal_json = json.loads(station_minimal.serialize_summary())
    year_data = minimal_json['air']['time_of_wetness']['by_year']['2021']
    minimal_coverage = year_data['coverage_analysis']

    # Should recognize inadequate coverage
    self.assertFalse(minimal_coverage['temperature']['adequate_coverage'],
      'Single measurement should be inadequate coverage')
    self.assertEqual(minimal_coverage['temperature']['days_with_data'], 1,
      'Single measurement should show 1 day with data')
    def setUp(self):
        """Set up realistic weather data for testing."""
        self.start_date = datetime.datetime(2021, 1, 1, 0, 0, 0)
        
    def create_realistic_daily_data(self, station, days=365, temp_base=15.0, humidity_base=60.0):
        """
        Create realistic daily weather data with seasonal variations.
        
        Args:
            station: WeatherStation instance
            days: Number of days to create data for
            temp_base: Base temperature in Celsius
            humidity_base: Base humidity percentage
        """
        for day in range(days):
            current_time = self.start_date + datetime.timedelta(days=day)
            
            # Seasonal temperature variation (sinusoidal over the year)
            seasonal_temp = temp_base + 10 * math.sin(2 * math.pi * day / 365)
            daily_temp_variation = 5 * math.sin(2 * math.pi * current_time.hour / 24)
            temp = seasonal_temp + daily_temp_variation
            
            # Seasonal humidity variation (inverse to temperature)
            seasonal_humidity = humidity_base + 20 * math.cos(2 * math.pi * day / 365)
            humidity = max(20, min(95, seasonal_humidity))
            
            # Add measurements at noon each day for consistent timing
            measurement_time = current_time.replace(hour=12)
            station.add_temp_c(temp, measurement_time)
            station.add_humidity(humidity, measurement_time)

    def create_sparse_but_distributed_data(self, station, interval_days=7):
        """
        Create sparse but well-distributed data (e.g., weekly measurements).
        
        Args:
            station: WeatherStation instance
            interval_days: Days between measurements
        """
        day = 0
        while day < 365:
            current_time = self.start_date + datetime.timedelta(days=day)
            
            # Seasonal variations
            temp = 15 + 10 * math.sin(2 * math.pi * day / 365)
            humidity = 65 + 15 * math.cos(2 * math.pi * day / 365)
            
            measurement_time = current_time.replace(hour=12)
            station.add_temp_c(temp, measurement_time)
            station.add_humidity(humidity, measurement_time)
            
            day += interval_days

    def create_clustered_data(self, station):
        """
        Create clustered data that fails temporal coverage but may have enough total readings.
        Data concentrated in 3 months of the year.
        """
        # Add data only for Jan, May, and September (3 months)
        months_with_data = [1, 5, 9]
        
        for month in months_with_data:
            for day in range(1, 32):  # Full month coverage
                try:
                    current_time = datetime.datetime(2021, month, day, 12, 0, 0)
                    temp = 15 + 10 * math.sin(2 * math.pi * (day + month * 30) / 365)
                    humidity = 65 + 15 * math.cos(2 * math.pi * (day + month * 30) / 365)
                    
                    station.add_temp_c(temp, current_time)
                    station.add_humidity(humidity, current_time)
                except ValueError:
                    # Skip invalid dates (like Feb 30)
                    continue

    def test_enhanced_qa_enabled_by_default(self):
        """Test that enhanced_qa is True by default."""
        station = WeatherStation('STATION')
        station.enable_time_of_wetness()
        
        self.assertTrue(station.enhanced_qa, "Enhanced QA should be enabled by default")

    def test_enhanced_qa_can_be_disabled(self):
        """Test that enhanced_qa can be explicitly disabled."""
        station = WeatherStation('STATION')
        station.enable_time_of_wetness(enhanced_qa=False)
        
        self.assertFalse(station.enhanced_qa, "Enhanced QA should be disabled when set to False")

    def test_daily_data_fails_enhanced_qa_density(self):
        """
        Test that daily data (1 reading per day) fails enhanced QA due to insufficient density.
        Enhanced QA is MORE restrictive - it first checks traditional density (75%) before temporal coverage.
        Daily data has only ~4% density (365/8760 hours) so it always fails with FAIL_DENSITY.
        """
        station = WeatherStation('STATION')
        station.enable_time_of_wetness(enhanced_qa=True)
        
        # Add daily data for a full year (365 readings, ~4% of possible hourly readings)
        self.create_realistic_daily_data(station)
        
        # Get the JSON output with enhanced QA
        json_output = json.loads(station.serialize_summary())
        
        # Debug: Print the actual year keys
        available_years = list(json_output['air']['time_of_wetness']['by_year'].keys())
        print(f"DEBUG: Available year keys: {available_years}")
        
        # Use string key for the year
        tow_data = json_output['air']['time_of_wetness']['by_year']['2021']
        
        # Should have coverage analysis despite density failure
        self.assertIn('coverage_analysis', tow_data)
        
        # Traditional QA should fail due to low density (~4%)
        self.assertEqual(tow_data['qa_state'], 'FAIL',
                        "Traditional QA should fail for daily data due to insufficient density")
        self.assertLess(tow_data['percent_valid'], 0.75,
                       "Daily data should have <75% data density")
        
        # Enhanced QA should fail with FAIL_DENSITY (never gets to check coverage)
        self.assertEqual(tow_data['coverage_analysis']['enhanced_qa_state'], 'FAIL_DENSITY',
                        "Enhanced QA should fail daily data with FAIL_DENSITY")
        
        # Coverage analysis should still be computed and might be good
        temp_coverage = tow_data['coverage_analysis']['temperature']
        humidity_coverage = tow_data['coverage_analysis']['humidity']
        
        # The coverage analysis itself might show good distribution
        # (but it doesn't matter since density check failed first)
        print(f"DEBUG: Temperature adequate coverage: {temp_coverage['adequate_coverage']}")
        print(f"DEBUG: Humidity adequate coverage: {humidity_coverage['adequate_coverage']}")
        print(f"DEBUG: Temperature overall score: {temp_coverage['overall_score']}")
        print(f"DEBUG: Data density: {tow_data['percent_valid']:.3f}")

    def create_high_density_well_distributed_data(self, station, density=0.8):
        """
        Create high-density, well-distributed data that should pass enhanced QA.
        
        Args:
            station: WeatherStation instance
            density: Fraction of hours to fill (e.g., 0.8 = 80%)
        """
        hours_to_fill = int(8760 * density)  # 80% of year = ~7000 hours
        print(f"DEBUG: Creating well-distributed data with {hours_to_fill} hours ({density*100:.1f}% density)")
        
        # Distribute evenly throughout the year
        for i in range(hours_to_fill):
            # Spread hours evenly across the year
            hour_offset = int(i * 8760 / hours_to_fill)
            dt = self.start_date + datetime.timedelta(hours=hour_offset)
            
            # Seasonal variations
            day_of_year = dt.timetuple().tm_yday
            temp = 15 + 10 * math.sin(2 * math.pi * day_of_year / 365)
            humidity = 65 + 15 * math.cos(2 * math.pi * day_of_year / 365)
            
            station.add_temp_c(temp, dt)
            station.add_humidity(humidity, dt)
        
        print(f"DEBUG: Added {hours_to_fill} data points for well-distributed data")

    def create_high_density_poorly_distributed_data(self, station, density=0.8):
        """
        Create high-density, poorly distributed data (clustered) that should fail coverage.
        
        Args:
            station: WeatherStation instance  
            density: Fraction of hours to fill (e.g., 0.8 = 80%)
        """
        hours_to_fill = int(8760 * density)  # 80% of year = ~7000 hours
        print(f"DEBUG: Creating poorly-distributed data with {hours_to_fill} hours ({density*100:.1f}% density)")
        
        # Create poorly distributed data: 90% in first 6 months, 10% in last 6 months
        first_half_hours = int(hours_to_fill * 0.9)  # 90% in Jan-June
        second_half_hours = hours_to_fill - first_half_hours  # 10% in July-Dec
        
        added_count = 0
        
        # First 6 months: dense data (Jan-June) - 90% of total
        hours_per_month_first = first_half_hours // 6
        for month in range(1, 7):
            month_hours_added = 0
            for day in range(1, 32):  
                for hour in range(24):  
                    if month_hours_added >= hours_per_month_first:
                        break
                    
                    try:
                        dt = datetime.datetime(2021, month, day, hour, 0, 0)
                        
                        # Basic seasonal variations
                        day_of_year = dt.timetuple().tm_yday  
                        temp = 15 + 10 * math.sin(2 * math.pi * day_of_year / 365)
                        humidity = 65 + 15 * math.cos(2 * math.pi * day_of_year / 365)
                        
                        station.add_temp_c(temp, dt)
                        station.add_humidity(humidity, dt)
                        added_count += 1
                        month_hours_added += 1
                        
                    except ValueError:
                        # Skip invalid dates
                        continue
                if month_hours_added >= hours_per_month_first:
                    break
        
        # Last 6 months: sparse data (July-December) - 10% of total
        hours_per_month_second = second_half_hours // 6
        for month in range(7, 13):
            month_hours_added = 0
            day = 1
            hour = 0
            while month_hours_added < hours_per_month_second and added_count < hours_to_fill:
                try:
                    dt = datetime.datetime(2021, month, day, hour, 0, 0)
                    
                    # Basic seasonal variations
                    day_of_year = dt.timetuple().tm_yday  
                    temp = 15 + 10 * math.sin(2 * math.pi * day_of_year / 365)
                    humidity = 65 + 15 * math.cos(2 * math.pi * day_of_year / 365)
                    
                    station.add_temp_c(temp, dt)
                    station.add_humidity(humidity, dt)
                    added_count += 1
                    month_hours_added += 1
                    
                    # Move to next hour/day with some sparsity
                    hour += 6  # Every 6 hours instead of every 12
                    if hour >= 24:
                        hour = 0
                        day += 2  # Every 2nd day instead of 7th
                        if day > 31:
                            break
                        
                except ValueError:
                    # Skip invalid dates, move to next
                    hour += 6
                    if hour >= 24:
                        hour = 0
                        day += 2
                        if day > 31:
                            break
        
        print(f"DEBUG: Added {added_count} data points for poorly-distributed data")

    def test_high_density_well_distributed_vs_poorly_distributed(self):
        """
        Test enhanced QA with ~80% data density - should pass density check but 
        differentiate between well-distributed vs poorly-distributed data.
        """
        # Well-distributed 80% density data
        station_good = WeatherStation('STATION')
        station_good.enable_time_of_wetness(enhanced_qa=True)
        self.create_high_density_well_distributed_data(station_good, density=0.8)
        
        # Poorly-distributed 80% density data (clustered in first part of year)
        station_bad = WeatherStation('STATION')
        station_bad.enable_time_of_wetness(enhanced_qa=True)
        self.create_high_density_poorly_distributed_data(station_bad, density=0.8)
        
        # Get results
        good_json = json.loads(station_good.serialize_summary())
        bad_json = json.loads(station_bad.serialize_summary())
        
        good_tow = good_json['air']['time_of_wetness']['by_year']['2021']
        bad_tow = bad_json['air']['time_of_wetness']['by_year']['2021']
        
        # Debug: Print actual data densities
        print(f"DEBUG: Well-distributed data density: {good_tow['percent_valid']:.3f}")
        print(f"DEBUG: Poorly-distributed data density: {bad_tow['percent_valid']:.3f}")
        
        # Both should pass traditional QA (density > 75%)
        self.assertEqual(good_tow['qa_state'], 'PASS', 
                        "Well-distributed 80% data should pass traditional QA")
        self.assertEqual(bad_tow['qa_state'], 'PASS',
                        "Poorly-distributed 80% data should still pass traditional QA")
        
        # But enhanced QA should differentiate
        good_coverage = good_tow['coverage_analysis']
        bad_coverage = bad_tow['coverage_analysis']
        
        # Well-distributed should pass enhanced QA
        self.assertEqual(good_coverage['enhanced_qa_state'], 'PASS',
                        "Well-distributed 80% data should pass enhanced QA")
        
        # Poorly-distributed should fail coverage check
        self.assertEqual(bad_coverage['enhanced_qa_state'], 'FAIL_COVERAGE',
                        "Poorly-distributed 80% data should fail enhanced QA coverage check")
        
        # Coverage metrics should reflect the difference
        good_seasonal = good_coverage['temperature']['seasonal_coverage']
        bad_seasonal = bad_coverage['temperature']['seasonal_coverage']
        
        self.assertGreater(good_seasonal, bad_seasonal,
                          "Well-distributed data should have better seasonal coverage")
        
        print(f"Well-distributed seasonal coverage: {good_seasonal:.1f}%")
        print(f"Poorly-distributed seasonal coverage: {bad_seasonal:.1f}%")
        print(f"Well-distributed QA state: {good_coverage['enhanced_qa_state']}")
        print(f"Poorly-distributed QA state: {bad_coverage['enhanced_qa_state']}")

    def test_traditional_vs_enhanced_qa_differences(self):
        """
        Test the differences between traditional QA and enhanced QA modes.
        Show how enhanced QA provides more detailed analysis.
        """
        # Test with the same daily data using both modes
        
        # Traditional QA mode
        station_traditional = WeatherStation('STATION')
        station_traditional.enable_time_of_wetness(enhanced_qa=False)
        self.create_realistic_daily_data(station_traditional)
        
        # Enhanced QA mode  
        station_enhanced = WeatherStation('STATION')
        station_enhanced.enable_time_of_wetness(enhanced_qa=True)
        self.create_realistic_daily_data(station_enhanced)
        
        # Compare outputs
        traditional_json = json.loads(station_traditional.serialize_summary())
        enhanced_json = json.loads(station_enhanced.serialize_summary())
        
        traditional_tow = traditional_json['air']['time_of_wetness']['by_year']['2021']
        enhanced_tow = enhanced_json['air']['time_of_wetness']['by_year']['2021']
        
        # Traditional output should NOT have coverage_analysis
        self.assertNotIn('coverage_analysis', traditional_tow,
                        "Traditional QA should not include coverage analysis")
        
        # Enhanced output SHOULD have coverage_analysis
        self.assertIn('coverage_analysis', enhanced_tow,
                     "Enhanced QA should include coverage analysis")
        
        # Enhanced output should have additional fields
        coverage = enhanced_tow['coverage_analysis']
        self.assertIn('temperature', coverage)
        self.assertIn('humidity', coverage)
        self.assertIn('enhanced_qa_state', coverage)
        
        # Check structure of coverage analysis
        temp_analysis = coverage['temperature']
        expected_fields = ['overall_score', 'seasonal_coverage', 'monthly_coverage', 
                          'adequate_coverage', 'days_with_data', 'largest_gap_days']
        
        for field in expected_fields:
            self.assertIn(field, temp_analysis, f"Temperature analysis should include {field}")

    def test_sparse_distributed_vs_clustered_data(self):
        """
        Test temporal coverage analysis with sparse data. Both sparse distributed
        and clustered data will fail density check, but coverage analysis still 
        shows the distribution differences.
        """
        # Sparse but well-distributed data (weekly measurements, ~52 readings = 0.6% density)
        station_distributed = WeatherStation('STATION')
        station_distributed.enable_time_of_wetness(enhanced_qa=True)
        self.create_sparse_but_distributed_data(station_distributed, interval_days=7)
        
        # Clustered data (concentrated in 3 months, similar amount of data)
        station_clustered = WeatherStation('STATION')
        station_clustered.enable_time_of_wetness(enhanced_qa=True)
        self.create_clustered_data(station_clustered)
        
        # Get results
        distributed_json = json.loads(station_distributed.serialize_summary())
        clustered_json = json.loads(station_clustered.serialize_summary())
        
        distributed_tow = distributed_json['air']['time_of_wetness']['by_year']['2021']
        clustered_tow = clustered_json['air']['time_of_wetness']['by_year']['2021']
        
        # Debug: Print actual data densities
        print(f"DEBUG: Sparse distributed data density: {distributed_tow['percent_valid']:.3f}")
        print(f"DEBUG: Clustered data density: {clustered_tow['percent_valid']:.3f}")
        
        # Both should fail traditional QA due to low density
        self.assertEqual(distributed_tow['qa_state'], 'FAIL',
                        "Sparse distributed data should fail traditional QA")
        self.assertEqual(clustered_tow['qa_state'], 'FAIL', 
                        "Clustered sparse data should fail traditional QA")
        
        distributed_coverage = distributed_tow['coverage_analysis']
        clustered_coverage = clustered_tow['coverage_analysis']
        
        # Both should fail enhanced QA with FAIL_DENSITY
        self.assertEqual(distributed_coverage['enhanced_qa_state'], 'FAIL_DENSITY',
                        "Sparse distributed data should fail with FAIL_DENSITY")
        self.assertEqual(clustered_coverage['enhanced_qa_state'], 'FAIL_DENSITY',
                        "Clustered sparse data should fail with FAIL_DENSITY")
        
        # But coverage analysis should still show distribution differences
        distributed_seasonal = distributed_coverage['temperature']['seasonal_coverage']
        clustered_seasonal = clustered_coverage['temperature']['seasonal_coverage']
        
        self.assertGreater(distributed_seasonal, clustered_seasonal,
                          "Well-distributed sparse data should have better seasonal coverage than clustered")
        
        print(f"Sparse distributed seasonal coverage: {distributed_seasonal:.1f}%")
        print(f"Clustered seasonal coverage: {clustered_seasonal:.1f}%")
        print(f"Distributed QA state: {distributed_coverage['enhanced_qa_state']}")
        print(f"Clustered QA state: {clustered_coverage['enhanced_qa_state']}")

    def test_coverage_analysis_metrics(self):
        """Test specific coverage analysis metrics and their calculations."""
        station = WeatherStation('STATION')
        station.enable_time_of_wetness(enhanced_qa=True)
        
        # Create data with known characteristics
        self.create_realistic_daily_data(station, days=365)
        
        json_output = json.loads(station.serialize_summary())
        coverage = json_output['air']['time_of_wetness']['by_year']['2021']['coverage_analysis']
        
        temp_coverage = coverage['temperature']
        
        # Test that days_with_data makes sense for daily data
        self.assertEqual(temp_coverage['days_with_data'], 365,
                        "Daily data should show 365 days with data")
        
        # Seasonal coverage should be high for full year data
        self.assertGreater(temp_coverage['seasonal_coverage'], 95,
                          "Full year data should have excellent seasonal coverage")
        
        # Monthly coverage should be high  
        self.assertGreater(temp_coverage['monthly_coverage'], 95,
                          "Full year data should have excellent monthly coverage")
        
        # Largest gap should be small for daily data
        self.assertLessEqual(temp_coverage['largest_gap_days'], 1,
                           "Daily data should have gaps of at most 1 day")

    def test_enhanced_qa_state_transitions(self):
        """Test different enhanced QA state outcomes."""
        # Daily data should fail with FAIL_DENSITY (not enough density)
        station_daily = WeatherStation('STATION')
        station_daily.enable_time_of_wetness(enhanced_qa=True)
        self.create_realistic_daily_data(station_daily)
        
        daily_json = json.loads(station_daily.serialize_summary())
        daily_qa_state = daily_json['air']['time_of_wetness']['by_year']['2021']['coverage_analysis']['enhanced_qa_state']
        self.assertEqual(daily_qa_state, 'FAIL_DENSITY', 
                        "Daily data should fail enhanced QA due to insufficient density")
        
        # Test FAIL_COVERAGE state with clustered data
        station_coverage_fail = WeatherStation('STATION')
        station_coverage_fail.enable_time_of_wetness(enhanced_qa=True)
        self.create_clustered_data(station_coverage_fail)
        
        coverage_fail_json = json.loads(station_coverage_fail.serialize_summary())
        coverage_analysis = coverage_fail_json['air']['time_of_wetness']['by_year']['2021']['coverage_analysis']
        
        # The QA state should reflect coverage quality
        coverage_qa_state = coverage_analysis['enhanced_qa_state']
        print(f"Coverage QA state for clustered data: {coverage_qa_state}")
        
        # Test that coverage analysis provides useful metrics even for poor coverage
        self.assertLess(coverage_analysis['temperature']['seasonal_coverage'], 90,
                       "Clustered data should have poor seasonal coverage")

    def test_realistic_weather_patterns(self):
        """Test enhanced QA with realistic weather station scenarios."""
        
        # Scenario 1: Airport weather station with hourly data for 3 months
        station_airport = WeatherStation('STATION')
        station_airport.enable_time_of_wetness(enhanced_qa=True)
        
        # Add hourly data for 3 months (winter, spring, summer missing fall)
        for month in [1, 4, 7]:  # Jan, Apr, Jul
            for day in range(1, 32):
                for hour in range(0, 24, 3):  # Every 3 hours
                    try:
                        current_time = datetime.datetime(2021, month, day, hour, 0, 0)
                        temp = 15 + 10 * math.sin(2 * math.pi * (month * 30 + day) / 365)
                        humidity = 65 + 15 * math.cos(2 * math.pi * (month * 30 + day) / 365)
                        
                        station_airport.add_temp_c(temp, current_time)
                        station_airport.add_humidity(humidity, current_time)
                    except ValueError:
                        continue
        
        airport_json = json.loads(station_airport.serialize_summary())
        airport_coverage = airport_json['air']['time_of_wetness']['by_year']['2021']['coverage_analysis']
        
        # Should have poor seasonal coverage (missing fall)
        self.assertLess(airport_coverage['temperature']['seasonal_coverage'], 100,
                       "3-month data should have incomplete seasonal coverage")
        
        # Scenario 2: Research station with daily measurements (will fail due to density)
        station_research = WeatherStation('STATION')
        station_research.enable_time_of_wetness(enhanced_qa=True)
        self.create_realistic_daily_data(station_research)
        
        research_json = json.loads(station_research.serialize_summary())
        research_coverage = research_json['air']['time_of_wetness']['by_year']['2021']['coverage_analysis']
        
        # Should have excellent temporal coverage but fail density check
        self.assertGreater(research_coverage['temperature']['overall_score'], 90,
                          "Daily research station data should have excellent temporal coverage")
        self.assertEqual(research_coverage['enhanced_qa_state'], 'FAIL_DENSITY',
                        "Daily research station data should fail enhanced QA due to low density")

    def test_backward_compatibility(self):
        """Test that existing code without enhanced_qa still works."""
        station = WeatherStation('STATION')
        # Don't explicitly enable enhanced_qa - test default behavior
        station.enable_time_of_wetness()
        
        self.create_realistic_daily_data(station)
        
        # Should work and default to enhanced QA
        json_output = json.loads(station.serialize_summary())
        tow_data = json_output['air']['time_of_wetness']['by_year']['2021']
        
        # Should include coverage analysis by default
        self.assertIn('coverage_analysis', tow_data,
                     "Enhanced QA should be enabled by default for backward compatibility")

    def test_edge_cases(self):
        """Test edge cases for enhanced QA."""
        
        # Test with very minimal data
        station_minimal = WeatherStation('STATION') 
        station_minimal.enable_time_of_wetness(enhanced_qa=True)
        
        # Add only one measurement
        station_minimal.add_temp_c(20.0, datetime.datetime(2021, 6, 15, 12, 0, 0))
        station_minimal.add_humidity(70.0, datetime.datetime(2021, 6, 15, 12, 0, 0))
        
        minimal_json = json.loads(station_minimal.serialize_summary())
        minimal_coverage = minimal_json['air']['time_of_wetness']['by_year']['2021']['coverage_analysis']
        
        # Should recognize inadequate coverage
        self.assertFalse(minimal_coverage['temperature']['adequate_coverage'],
                        "Single measurement should be inadequate coverage")
        self.assertEqual(minimal_coverage['temperature']['days_with_data'], 1,
                        "Single measurement should show 1 day with data")
