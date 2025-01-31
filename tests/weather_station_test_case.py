import unittest
import os
import numpy as np
import json
import pytz
import datetime
from wx_logs.weather_station import WeatherStation

class WeatherStationTestCase(unittest.TestCase):
    # ... existing test cases ...

    def test_adding_null_precipitation(self):
        a = WeatherStation('STATION')
        dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
        a.add_precipitation_mm(None, 60, dt)
        self.assertEqual(a.get_precipitation_mm('SUM'), 0)

    def test_adding_empty_precipitation(self):
        a = WeatherStation('STATION')
        dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
        a.add_precipitation_mm("", 60, dt)
        self.assertEqual(a.get_precipitation_mm('SUM'), 0)

    def test_adding_nan_precipitation(self):
        a = WeatherStation('STATION')
        dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
        a.add_precipitation_mm(np.nan, 60, dt)
        self.assertEqual(a.get_precipitation_mm('SUM'), 0)
