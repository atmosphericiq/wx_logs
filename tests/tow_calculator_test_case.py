import unittest
import datetime
from wx_logs.tow_calculator import TOWCalculator

class TOWCalculatorTestCase(unittest.TestCase):

  def test_simple(self):
    random_date = datetime.datetime(2019, 1, 1, 12, 32, 10)

    tow_calculator = TOWCalculator()
    tow_calculator.add_temperature(10, random_date)
    tow_calculator.add_humidity(20, random_date)
    years = tow_calculator.get_years()
    self.assertEqual(len(years.keys()), 1)
    self.assertIn(2019, years.keys())

    data_2019 = years[2019]
    self.assertEqual(data_2019['max_hours'], 8760)
    self.assertEqual(data_2019['total_hours'], 1)
    self.assertEqual(data_2019['percent_valid'], 1.0/8760.0)
    self.assertEqual(data_2019['qa_state'], 'FAIL')
    self.assertEqual(data_2019['time_of_wetness'], None)

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
