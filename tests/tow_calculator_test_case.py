import unittest
import datetime
from wx_logs.tow_calculator import TOWCalculator

class TOWCalculatorTestCase(unittest.TestCase):

  def test_simple(self):
    random_date = datetime.datetime(2019, 1, 1, 12, 32, 10)

    tow_calculator = TOWCalculator(4)
    tow_calculator.add_temperature(10, random_date)
    tow_calculator.add_humidity(20, random_date)
    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 1)
    self.assertIn(2019, years.keys())

    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], 1)
    self.assertEqual(data_2019['percent_valid'], round(1.0/8760.0, 4))
    self.assertEqual(data_2019['qa_state'], 'FAIL')
    self.assertEqual(data_2019['time_of_wetness'], None)

  def test_higher_precision_issues(self):
    tow = TOWCalculator(12)
    tow.add_temperature(10, datetime.datetime(2019, 1, 1, 0, 0, 0))
    tow.add_humidity(20, datetime.datetime(2019, 1, 1, 0, 0, 0))
    tow.add_temperature(10, datetime.datetime(2020, 2, 1, 1, 0, 0))
    tow.add_humidity(20, datetime.datetime(2020, 2, 1, 1, 0, 0))
    self.assertEqual(len(tow.get_years()), 2)
    data_2019 = tow.get_years()[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], 1)
    self.assertEqual(data_2019['percent_valid'], round(1.0/8760.0, 12))

  def test_data_with_no_humidity_provided(self):
    tow = TOWCalculator(4)
    tow.add_temperature(10, datetime.datetime(2019, 1, 1, 0, 0, 0))
    years = tow.get_years()
    self.assertEqual(len(years.keys()), 1)
    self.assertIn(2019, years.keys())
    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], 0)
    self.assertEqual(data_2019['percent_valid'], 0.0)
    self.assertEqual(data_2019['qa_state'], 'FAIL')
    self.assertEqual(data_2019['time_of_wetness'], None)

  def test_tow_weird_case_that_fails(self):
    tow = TOWCalculator(4)
    c = 0
    for i in range(1, 13):
      for j in range(1, 29):
        for h in range(0, 24):
          random_date = datetime.datetime(2021, i, j, h, 0, 0)
          tow.add_temperature(25, random_date)
          tow.add_humidity(100, random_date)
          c += 1
    years = tow.get_years()
    self.assertEqual(len(years), 1)
    self.assertIn(2021, years.keys())
    data_2021 = years[2021]
    self.assertEqual(data_2021['max_hours'], 8760)
    self.assertEqual(data_2021['percent_valid'], round(c/8760.0, 4))
    self.assertEqual(data_2021['total_hours'], c)
    self.assertEqual(data_2021['time_of_wetness'], 8760)

  def test_tow_80_percent_of_year_extrapolates_ok(self):
    random_date = datetime.datetime(2019, 1, 1, 0, 0, 0)
    tow_calculator = TOWCalculator()
    eighty_pct = round(8760 * 0.8)
    for i in range(eighty_pct):
      if i % 2 == 0:
        humidity = 90
      else:
        humidity = 10
      tow_calculator.add_temperature(10, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 1)
    self.assertIn(2019, years.keys())
    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], eighty_pct)
    self.assertEqual(data_2019['percent_valid'], 0.8)
    self.assertEqual(data_2019['qa_state'], 'PASS')
    self.assertEqual(data_2019['time_of_wetness'], 8760 * 0.50)

  # we want to be able to have a function called annualize which takes
  # - number of hours we got data for
  # - number of tow hours 
  # and then returns an annualized number of hours based on the
  # maximum annual of 8760
  def test_tow_annualize_function(self):
    max_hours = 100
    valid_hours = 50 
    tow_hours = 25
    tow_calculator = TOWCalculator()
    annualized = tow_calculator.annualize(valid_hours, tow_hours)
    self.assertEqual(annualized, int(8760 * 0.50))

  def test_tow_over_2_years(self):
    random_date = datetime.datetime(2018, 1, 1, 0, 0, 0)
    tow_calculator = TOWCalculator()
    samples = round(8760 * 2)
    for i in range(samples):
      if i % 2 == 0:
        humidity = 90
      else:
        humidity = 10
      tow_calculator.add_temperature(10, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)
    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 2)
    self.assertIn(2018, years.keys())
    self.assertIn(2019, years.keys())

    allyears = tow_calculator.get_averages()
    self.assertEqual(allyears['valid_years'], 2)
    self.assertEqual(allyears['annual_time_of_wetness'], 0.5 * 8760)

  def test_tow_over_2_point_five_years(self):
    random_date = datetime.datetime(2018, 1, 1, 0, 0, 0)
    tow_calculator = TOWCalculator()
    samples = round(8760 * 2.5)
    for i in range(samples):
      if i % 2 == 0:
        humidity = 90
      else:
        humidity = 10
      tow_calculator.add_temperature(10, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)
    years = tow_calculator.get_years()
    self.assertIn(2018, years.keys())
    self.assertIn(2019, years.keys())
    self.assertIn(2020, years.keys())

    data_2020 = years[2020]
    self.assertEqual(data_2020['max_hours'], 8760+24) #leap year
    self.assertEqual(data_2020['qa_state'], 'FAIL')

    allyears = tow_calculator.get_averages()
    self.assertEqual(allyears['valid_years'], 2)
    self.assertEqual(allyears['annual_time_of_wetness'], 0.5 * 8760)

  def test_tow_50_percent_of_the_year(self):
    random_date = datetime.datetime(2019, 1, 1, 0, 0, 0)
    tow_calculator = TOWCalculator()
    for i in range(8760):
      if i % 2 == 0:
        humidity = 90
      else:
        humidity = 10
      tow_calculator.add_temperature(10, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 1)
    self.assertIn(2019, years.keys())

    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], 8760)
    self.assertEqual(data_2019['percent_valid'], 1.0)
    self.assertEqual(data_2019['qa_state'], 'PASS')
    self.assertEqual(data_2019['time_of_wetness'], 4380)

  def test_values_in_every_hour_for_year(self):
    random_date = datetime.datetime(2019, 1, 1, 0, 0, 0)

    tow_calculator = TOWCalculator()
    for i in range(8760):
      tow_calculator.add_temperature(10, random_date)
      tow_calculator.add_humidity(20, random_date)
      random_date += datetime.timedelta(hours=1)

    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 1)
    self.assertIn(2019, years.keys())

    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], 8760)
    self.assertEqual(data_2019['percent_valid'], 1.0)
    self.assertEqual(data_2019['qa_state'], 'PASS')
    self.assertEqual(data_2019['time_of_wetness'], 0)

  def test_two_years_different_tow_percentages_average_correctly(self):
    random_date = datetime.datetime(2019, 1, 1, 0, 0, 0)  # Use non-leap years
    tow_calculator = TOWCalculator()

    # Year 1 (2019): 25% wetness (every 4th hour meets TOW conditions)
    for i in range(8760):
      temp = 10  # Always above 0°C threshold
      # Every 4th hour has high humidity (RH > 80%)
      humidity = 85 if i % 4 == 0 else 50
      tow_calculator.add_temperature(temp, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    # Year 2 (2020): 75% wetness (3 out of 4 hours meet TOW conditions)
    for i in range(8784):  # 2020 is leap year, has 8784 hours
      temp = 10  # Always above 0°C threshold
      # 3 out of 4 hours have high humidity (RH > 80%)
      humidity = 85 if i % 4 != 0 else 50
      tow_calculator.add_temperature(temp, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    # Check individual years
    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 2)
    self.assertIn(2019, years.keys())
    self.assertIn(2020, years.keys())

    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)  # Regular year
    self.assertEqual(data_2019['total_hours'], 8760)
    self.assertEqual(data_2019['qa_state'], 'PASS')
    self.assertEqual(data_2019['time_of_wetness'], round(8760 * 0.25, 2))  # 25% of year

    data_2020 = years[2020]
    self.assertEqual(data_2020['max_hours'], 8784)  # 2020 is leap year
    self.assertEqual(data_2020['total_hours'], 8784)
    self.assertEqual(data_2020['qa_state'], 'PASS')
    self.assertEqual(data_2020['time_of_wetness'], round(8784 * 0.75, 2))  # 75% of leap year

    # Check the average calculation
    # Year 2019: 2190 actual TOW hours out of 8760 data hours
    # Year 2020: 6588 actual TOW hours out of 8784 data hours
    # Total: 8778 TOW hours out of 17544 data hours = ~50% average
    allyears = tow_calculator.get_averages()
    self.assertEqual(allyears['valid_years'], 2)
    expected_avg = round((2190 + 6588) / (8760 + 8784) * 8760, 0)
    self.assertEqual(allyears['annual_time_of_wetness'], expected_avg)

  def test_three_years_with_minimal_third_year_data(self):
    random_date = datetime.datetime(2019, 1, 1, 0, 0, 0)
    tow_calculator = TOWCalculator()

    # Year 1 (2019): 25% wetness (every 4th hour meets TOW conditions)
    for i in range(8760):
      temp = 10  # Always above 0°C threshold
      # Every 4th hour has high humidity (RH > 80%)
      humidity = 85 if i % 4 == 0 else 50
      tow_calculator.add_temperature(temp, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    # Year 2 (2020): 75% wetness (3 out of 4 hours meet TOW conditions)
    for i in range(8784):  # 2020 is leap year, has 8784 hours
      temp = 10  # Always above 0°C threshold
      # 3 out of 4 hours have high humidity (RH > 80%)
      humidity = 85 if i % 4 != 0 else 50
      tow_calculator.add_temperature(temp, random_date)
      tow_calculator.add_humidity(humidity, random_date)
      random_date += datetime.timedelta(hours=1)

    # Year 3 (2021): Only one hour of data that meets TOW conditions
    random_date = datetime.datetime(2021, 6, 15, 12, 0, 0)  # Mid-year single point
    tow_calculator.add_temperature(15, random_date)  # Above 0°C threshold
    tow_calculator.add_humidity(85, random_date)     # Above 80% threshold

    # Check individual years
    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 3)
    self.assertIn(2019, years.keys())
    self.assertIn(2020, years.keys())
    self.assertIn(2021, years.keys())

    # Verify first two years (same as previous test)
    data_2019 = years[2019]
    self.assertEqual(data_2019['total_hours'], 8760)
    self.assertEqual(data_2019['qa_state'], 'PASS')
    self.assertEqual(data_2019['time_of_wetness_actual'], 2190)  # 25% of 8760

    data_2020 = years[2020]
    self.assertEqual(data_2020['total_hours'], 8784)
    self.assertEqual(data_2020['qa_state'], 'PASS')
    self.assertEqual(data_2020['time_of_wetness_actual'], 6588)  # 75% of 8784

    # Verify third year fails QA (only 1 hour out of 8760 = 0.011% coverage)
    data_2021 = years[2021]
    self.assertEqual(data_2021['max_hours'], 8760)
    self.assertEqual(data_2021['total_hours'], 1)
    self.assertEqual(data_2021['time_of_wetness_actual'], 1)  # 1 TOW hour
    self.assertEqual(data_2021['qa_state'], 'FAIL')  # Far below 75% threshold
    self.assertEqual(data_2021['time_of_wetness'], None)  # No projection due to QA fail

    # Check that third year is excluded from average (only first 2 years used)
    allyears = tow_calculator.get_averages()
    self.assertEqual(allyears['valid_years'], 2)  # Only 2019 and 2020 pass QA
    expected_avg = round((2190 + 6588) / (8760 + 8784) * 8760, 0)
    self.assertEqual(allyears['annual_time_of_wetness'], expected_avg)  # Same as 2-year test
