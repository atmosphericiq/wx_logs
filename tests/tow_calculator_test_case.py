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
