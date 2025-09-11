import unittest
import datetime
from wx_logs.data_coverage import YearCoverageAnalyzer

class DataCoverageTestCase(unittest.TestCase):
  
  def setUp(self):
    self.analyzer = YearCoverageAnalyzer(adequate_threshold=75.0)
    
    # Create test data for 2024 (leap year)
    self.leap_year = 2024
    # Create test data for 2023 (regular year)
    self.regular_year = 2023
  
  def _create_datetime_list(self, dates_list):
    return [datetime.datetime.strptime(
      date_str + ' 12:00:00', '%Y-%m-%d %H:%M:%S')
      for date_str in dates_list]
  
  def _create_date_range(self, start_date, end_date):
    start = datetime.datetime.strptime(
      start_date + ' 12:00:00', '%Y-%m-%d %H:%M:%S')
    end = datetime.datetime.strptime(
      end_date + ' 12:00:00', '%Y-%m-%d %H:%M:%S')
    current = start
    dates = []
    while current <= end:
      dates.append(current)
      current += datetime.timedelta(days=1)
    return dates
  
  # ==================== SEASONAL DISTRIBUTION TESTS ====================
  
  def test_well_balanced_seasonal_distribution(self):
    # Create evenly distributed data across all seasons of 2023
    spring_dates = self._create_date_range('2023-03-20', '2023-06-20')
    summer_dates = self._create_date_range('2023-06-21', '2023-09-22')
    fall_dates = self._create_date_range('2023-09-23', '2023-12-20')
    winter_dates_late = self._create_date_range(
      '2023-12-21', '2023-12-31')
    winter_dates_early = self._create_date_range(
      '2023-01-01', '2023-03-19')
    
    all_dates = (spring_dates + summer_dates + fall_dates +
      winter_dates_late + winter_dates_early)
    
    result = self.analyzer.analyze_coverage(all_dates, self.regular_year)
    
    # Should have good seasonal coverage
    self.assertGreater(result['seasonal_coverage'], 80.0)
    self.assertTrue(result['adequate_coverage'])
  
  def test_heavily_skewed_seasonal_distribution(self):
    # Only summer data
    summer_dates = self._create_date_range('2023-06-01', '2023-08-31')
    
    result = self.analyzer.analyze_coverage(summer_dates, self.regular_year)
    
    # Should show poor seasonal coverage despite having data
    self.assertLess(result['seasonal_coverage'], 50.0)
    seasonal_breakdown = result['seasonal_breakdown']
    self.assertGreater(seasonal_breakdown['summer'], 0)
    self.assertEqual(seasonal_breakdown['spring'], 0)
    self.assertEqual(seasonal_breakdown['fall'], 0)
    self.assertEqual(seasonal_breakdown['winter'], 0)
  
  def test_partial_seasonal_coverage(self):
    # Partial spring and fall coverage only
    # 30 days
    spring_dates = self._create_date_range('2023-04-01', '2023-04-30')
    # 31 days
    fall_dates = self._create_date_range('2023-10-01', '2023-10-31')
    
    all_dates = spring_dates + fall_dates
    
    result = self.analyzer.analyze_coverage(all_dates, self.regular_year)
    
    # Should have moderate coverage
    # (but might be lower due to missing seasons)
    self.assertGreater(result['seasonal_coverage'], 10.0)
    self.assertLess(result['seasonal_coverage'], 70.0)
    
    seasonal_breakdown = result['seasonal_breakdown']
    self.assertGreater(seasonal_breakdown['spring'], 0)
    self.assertGreater(seasonal_breakdown['fall'], 0)
    self.assertEqual(seasonal_breakdown['summer'], 0)
    self.assertEqual(seasonal_breakdown['winter'], 0)
  
  # ==================== MONTHLY COVERAGE TESTS ====================
  
  def test_complete_monthly_coverage(self):
    # Complete year of data
    all_dates = self._create_date_range('2023-01-01', '2023-12-31')
    
    result = self.analyzer.analyze_coverage(all_dates, self.regular_year)
    
    # All months should be represented
    monthly_breakdown = result['monthly_breakdown']
    for month in range(1, 13):
      self.assertGreater(monthly_breakdown[month], 0,
        f'Month {month} should have data')
    
    # Should have excellent monthly coverage
    self.assertGreater(result['monthly_coverage'], 95.0)
  
  def test_missing_months_coverage(self):
    # Only January, March, and December data
    jan_dates = self._create_date_range('2023-01-01', '2023-01-31')
    mar_dates = self._create_date_range('2023-03-01', '2023-03-31')
    dec_dates = self._create_date_range('2023-12-01', '2023-12-31')
    
    all_dates = jan_dates + mar_dates + dec_dates
    
    result = self.analyzer.analyze_coverage(all_dates, self.regular_year)
    
    monthly_breakdown = result['monthly_breakdown']
    
    # Present months should have data
    self.assertGreater(monthly_breakdown[1], 0)   # January
    self.assertGreater(monthly_breakdown[3], 0)   # March
    self.assertGreater(monthly_breakdown[12], 0)  # December
    
    # Missing months should not be in the breakdown dict
    for month in [2, 4, 5, 6, 7, 8, 9, 10, 11]:
      self.assertEqual(monthly_breakdown.get(month, 0), 0,
        f'Month {month} should have no data')
    
    # Monthly coverage should be 25% (3/12 months)
    self.assertAlmostEqual(result['monthly_coverage'], 25.0, delta=1.0)
  
  def test_partial_monthly_coverage(self):
    # Half of January, quarter of February
    jan_partial = self._create_date_range('2023-01-01', '2023-01-15')
    feb_partial = self._create_date_range('2023-02-01', '2023-02-07')
    
    all_dates = jan_partial + feb_partial
    
    result = self.analyzer.analyze_coverage(all_dates, self.regular_year)
    
    monthly_breakdown = result['monthly_breakdown']
    
    # January and February should have partial data
    self.assertGreater(monthly_breakdown[1], 0)
    self.assertGreater(monthly_breakdown[2], 0)
    
    # Other months should have no data
    for month in range(3, 13):
      self.assertEqual(monthly_breakdown.get(month, 0), 0)
    
    # Monthly coverage should be ~17% (2/12 months with data)
    self.assertAlmostEqual(result['monthly_coverage'], 16.7, delta=2.0)
  
  # ==================== GAP ANALYSIS TESTS ====================
  
  def test_no_gaps_continuous_data(self):
    all_dates = self._create_date_range('2023-01-01', '2023-12-31')
    
    result = self.analyzer.analyze_coverage(all_dates, self.regular_year)
    
    # Should have minimal gaps
    # (only 1-day gaps are allowed in continuous data)
    self.assertEqual(result['largest_gap_days'], 1)
  
  def test_large_gaps_analysis(self):
    # Create data with large gaps:
    # January data, then November data only
    jan_dates = self._create_date_range('2023-01-01', '2023-01-31')
    nov_dates = self._create_date_range('2023-11-01', '2023-11-30')
    
    all_dates = jan_dates + nov_dates
    
    result = self.analyzer.analyze_coverage(all_dates, self.regular_year)
    
    # Should detect large gap between January and November
    self.assertGreater(result['largest_gap_days'], 250)
    self.assertFalse(result['adequate_coverage'])
  
  def test_multiple_varied_gaps(self):
    dates_list = [
      '2023-01-01', '2023-01-02', '2023-01-03',  # 3 days
      # Gap
      '2023-01-08', '2023-01-09',  # 2 days
      # Gap
      '2023-02-01', '2023-02-02', '2023-02-03'  # 3 days
    ]
    datetime_list = self._create_datetime_list(dates_list)
    
    result = self.analyzer.analyze_coverage(datetime_list, self.regular_year)
    
    # Should detect gaps
    # Gap from Jan 9 to Feb 1
    self.assertGreater(result['largest_gap_days'], 15)
  
  # ==================== ADEQUATE COVERAGE TESTS ====================
  
  def test_adequate_coverage_high_threshold(self):
    # Create analyzer with 90% threshold
    high_analyzer = YearCoverageAnalyzer(adequate_threshold=90.0)
    
    # 95% coverage (347/365 days)
    # 347 days
    dates = self._create_date_range('2023-01-01', '2023-12-13')
    
    result = high_analyzer.analyze_coverage(dates, self.regular_year)
    
    self.assertTrue(result['adequate_coverage'])
    self.assertGreater(result['overall_score'], 90.0)
  
  def test_adequate_coverage_low_threshold(self):
    # Create analyzer with 50% threshold
    low_analyzer = YearCoverageAnalyzer(adequate_threshold=50.0)
    
    # 60% coverage
    # ~219 days = 60%
    dates = self._create_date_range('2023-01-01', '2023-08-29')
    
    result = low_analyzer.analyze_coverage(dates, self.regular_year)
    
    self.assertTrue(result['adequate_coverage'])
    self.assertGreater(result['overall_score'], 50.0)
  
  def test_inadequate_coverage_threshold(self):
    # 40% coverage with 75% threshold (default)
    # ~146 days = 40%
    dates = self._create_date_range('2023-01-01', '2023-05-26')
    
    result = self.analyzer.analyze_coverage(dates, self.regular_year)
    
    self.assertFalse(result['adequate_coverage'])
    self.assertLess(result['overall_score'], 75.0)
  
  # ==================== LEAP YEAR TESTS ====================
  
  def test_leap_year_complete_coverage(self):
    all_dates = self._create_date_range('2024-01-01', '2024-12-31')
    
    result = self.analyzer.analyze_coverage(all_dates, self.leap_year)
    
    self.assertGreater(result['overall_score'], 95.0)
    self.assertEqual(result['days_with_data'], 366)
    self.assertTrue(result['adequate_coverage'])
  
  def test_leap_year_february_coverage(self):
    # Complete February in leap year
    feb_dates = self._create_date_range('2024-02-01', '2024-02-29')
    
    result = self.analyzer.analyze_coverage(feb_dates, self.leap_year)
    
    # Should detect all 29 days
    self.assertEqual(result['days_with_data'], 29)
    
    # Total coverage should be 29/366 ≈ 7.9%
    expected_coverage = (29.0 / 366.0) * 100.0
    self.assertAlmostEqual(result['days_with_data'] / 366.0 * 100,
      expected_coverage, delta=0.5)
  
  def test_leap_year_vs_regular_year_comparison(self):
    # Same absolute number of days (100 days)
    regular_dates = self._create_date_range('2023-01-01', '2023-04-10')
    leap_dates = self._create_date_range('2024-01-01', '2024-04-10')
    
    result_regular = self.analyzer.analyze_coverage(regular_dates, self.regular_year)
    result_leap = self.analyzer.analyze_coverage(leap_dates, self.leap_year)
    
    # Regular year: 100 days
    self.assertEqual(result_regular['days_with_data'], 100)
    # Leap year: 101 days (includes Feb 29)
    self.assertEqual(result_leap['days_with_data'], 101)
  
  # ==================== EDGE CASES TESTS ====================
  
  def test_single_day_data(self):
    single_date = [datetime.datetime(2023, 6, 15, 12, 0, 0)]
    
    result = self.analyzer.analyze_coverage(single_date, self.regular_year)
    
    self.assertEqual(result['days_with_data'], 1)
    self.assertLess(result['overall_score'], 10.0)
    self.assertFalse(result['adequate_coverage'])
    
    # Should have data in summer season only
    seasonal_breakdown = result['seasonal_breakdown']
    self.assertGreater(seasonal_breakdown['summer'], 0)
    self.assertEqual(seasonal_breakdown['spring'], 0)
    self.assertEqual(seasonal_breakdown['fall'], 0)
    self.assertEqual(seasonal_breakdown['winter'], 0)
  
  def test_year_start_boundary(self):
    # First week of year
    dates = self._create_date_range('2023-01-01', '2023-01-07')
    
    result = self.analyzer.analyze_coverage(dates, self.regular_year)
    
    self.assertEqual(result['days_with_data'], 7)
    self.assertLess(result['overall_score'], 20.0)  # Should be low coverage
    
    # Should be winter season
    seasonal_breakdown = result['seasonal_breakdown']
    self.assertGreater(seasonal_breakdown['winter'], 0)
  
  def test_year_end_boundary(self):
    # Last week of year
    dates = self._create_date_range('2023-12-25', '2023-12-31')
    
    result = self.analyzer.analyze_coverage(dates, self.regular_year)
    
    self.assertEqual(result['days_with_data'], 7)
    self.assertLess(result['overall_score'], 20.0)  # Should be low coverage
    
    # Should be winter season
    seasonal_breakdown = result['seasonal_breakdown']
    self.assertGreater(seasonal_breakdown['winter'], 0)
  
  def test_cross_year_boundary_data(self):
    # Data spanning multiple years, but we only analyze 2023
    dates_list = [
      '2022-12-30', '2022-12-31',  # Should be ignored
      '2023-01-01', '2023-01-02', '2023-01-03',
      '2024-01-01', '2024-01-02'  # Should be ignored
    ]
    datetime_list = self._create_datetime_list(dates_list)
    
    result = self.analyzer.analyze_coverage(datetime_list, self.regular_year)
    
    # Should only count the 3 days from 2023
    self.assertEqual(result['days_with_data'], 3)
    self.assertEqual(result['year_analyzed'], 2023)
  
  def test_empty_datetime_list(self):
    empty_list = []
    
    result = self.analyzer.analyze_coverage(empty_list, self.regular_year)
    
    self.assertEqual(result['days_with_data'], 0)
    self.assertEqual(result['overall_score'], 0.0)
    self.assertFalse(result['adequate_coverage'])
    
    # All monthly coverage should be 0
    for month in range(1, 13):
      self.assertEqual(result['monthly_breakdown'][month], 0)
    
    # All seasonal distribution should be 0
    seasonal_breakdown = result['seasonal_breakdown']
    for season in ['spring', 'summer', 'fall', 'winter']:
      self.assertEqual(seasonal_breakdown[season], 0)

if __name__ == '__main__':
  unittest.main()
