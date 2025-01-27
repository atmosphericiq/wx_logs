from wx_logs.hourly_grid import HourlyGrid
import random
import unittest
import datetime

class HourlyGridTestCase(unittest.TestCase):

  def test_one_measurement(self):
    grid = HourlyGrid()
    now = datetime.datetime.now()
    now_hour = now.replace(minute=0, second=0, microsecond=0)
    grid.add(now, 1)

    self.assertEqual(grid.get_start(), now_hour)
    self.assertEqual(grid.get_end(), now_hour)
    self.assertEqual(grid.get_total_hours(), 1)

  def test_no_measurements(self):
    grid = HourlyGrid()
    self.assertEqual(grid.get_start(), None)
    self.assertEqual(grid.get_end(), None)
    self.assertEqual(grid.get_total_hours(), 0)
    self.assertEqual(grid.get_total(), None)
    self.assertEqual(grid.get_mean(), None)
    self.assertEqual(grid.get_min(), None)
    self.assertEqual(grid.get_max(), None)

  def test_one_good_and_one_none_measurement(self):
    grid = HourlyGrid()
    jan1 = datetime.datetime(2022, 1, 1)
    grid.add(jan1, 1)
    jan1_hour2 = jan1.replace(hour=1)
    grid.add(jan1_hour2, None)

    self.assertEqual(grid.get_start(), jan1)
    self.assertEqual(grid.get_end(), jan1_hour2)
    self.assertEqual(grid.get_total_hours(), 2)
    self.assertEqual(grid.get_total(), 1.0) # usually none = 0
    self.assertEqual(grid.get_mean(), 0.5)
    self.assertEqual(grid.get_min(), 0)
    self.assertEqual(grid.get_max(), 1.0)

  def test_two_measurements(self):
    jan1 = datetime.datetime(2022, 1, 1)
    jan2 = datetime.datetime(2022, 1, 2)
    grid = HourlyGrid()
    grid.add(jan1, 1)
    grid.add(jan2, 1)
    self.assertEqual(grid.get_start(), jan1)
    self.assertEqual(grid.get_end(), jan2)

    jan3 = datetime.datetime(2022, 1, 3, 22, 59, 1)
    grid.add(jan3, 1)
    self.assertEqual(grid.get_start(), jan1)
    self.assertEqual(grid.get_end(), jan3.replace(minute=0, second=0, microsecond=0))
    self.assertEqual(grid.get_total_hours(), 24+24+23)

  def test_full_year(self):
    grid = HourlyGrid(0.0)
    jan1 = datetime.datetime(2022, 1, 1, 0, 0)
    dec31 = datetime.datetime(2022, 12, 31, 23, 59, 59)

    total = 0
    while jan1 <= dec31:
      v = random.randint(0, 10)
      total += v
      grid.add(jan1, v)
      jan1 += datetime.timedelta(hours=1)

    self.assertEqual(grid.get_start(), datetime.datetime(2022, 1, 1))
    self.assertEqual(grid.get_end(), datetime.datetime(2022, 12, 31, 23, 0, 0))
    self.assertEqual(grid.get_total_hours(), 24*365)
    self.assertEqual(grid.get_total(), total)
    self.assertEqual(grid.get_total_by_year(), {2022: total})

    self.assertEqual(grid.get_mean(), total / (24*365))
    self.assertEqual(grid.get_min(), 0.0)
    self.assertEqual(grid.get_max(), 10.0)

  def test_two_years(self):
    grid = HourlyGrid()
    jan1 = datetime.datetime(2022, 1, 1, 0, 0)
    dec31 = datetime.datetime(2023, 12, 31, 23, 59, 59)

    total = 0
    while jan1 <= dec31:
      v = 1.0
      grid.add(jan1, v)
      jan1 += datetime.timedelta(hours=1)

    self.assertEqual(grid.get_start(), datetime.datetime(2022, 1, 1, 0, 0, 0))
    self.assertEqual(grid.get_end(), datetime.datetime(2023, 12, 31, 23, 0, 0))
    self.assertEqual(grid.get_total_hours(), (24*365)+(24*365))
    self.assertEqual(grid.get_total_by_year(), {2022: (24*365), 2023: 24*365})
