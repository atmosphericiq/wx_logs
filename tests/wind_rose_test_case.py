import unittest
import datetime
import numpy as np
from wx_logs import WindRose

class WindRoseTestCase(unittest.TestCase):

  # make a blank wind rose of 8 dimensions and 
  # add some data to it
  def test_wind_rose(self):
    wr = WindRose(8, 2)
    wr.add_wind(10, 0, '2020-01-01 00:00:00') # mph, degrees, dt
    rose = wr.get_wind_rose()
    self.assertEqual(rose['N'], {'percent': 1.0, 'mean_wind_speed': 10.00})
    self.assertEqual(rose['E'], {'percent': 0.0, 'mean_wind_speed': None})

  def test_wind_rose_with_invalid_bins_in_constructor(self):
    self.assertRaises(ValueError, WindRose, 0)
    self.assertRaises(ValueError, WindRose, -1)

  def test_4_bin_wind_rose(self):
    a = WindRose(4)
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_wind(10, 180, datetime.datetime.now())
    a.add_wind(10, 270, datetime.datetime.now())

    wind_rose = a.get_wind_rose()
    self.assertEqual(wind_rose['N'], {'percent': 0.25, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['E'], {'percent': 0.25, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['S'], {'percent': 0.25, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['W'], {'percent': 0.25, 'mean_wind_speed': 10.0})

  def test_bearing_to_direction_4_8_16_bins(self):
    a = WindRose(8)
    self.assertEqual(a.bearing_to_direction(0), 'N')
    self.assertEqual(a.bearing_to_direction(45), 'NE')
    self.assertEqual(a.bearing_to_direction(90), 'E')
    self.assertEqual(a.bearing_to_direction(135), 'SE')
    self.assertEqual(a.bearing_to_direction(180), 'S')
    self.assertEqual(a.bearing_to_direction(225), 'SW')
    self.assertEqual(a.bearing_to_direction(270), 'W')
    self.assertEqual(a.bearing_to_direction(315), 'NW')

  def test_4_bin_wind_rose_with_calm(self):
    a = WindRose(4)
    a.add_wind(0.1, 0, datetime.datetime.now()) # CALM
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_wind(10, 180, datetime.datetime.now())
    a.add_wind(10, 270, datetime.datetime.now())

    wind_rose = a.get_wind_rose()
    self.assertEqual(wind_rose['N'], {'percent': 0, 'mean_wind_speed': None})
    self.assertEqual(wind_rose['CALM'], {'percent': 0.25, 'mean_wind_speed': 0.1})
    self.assertEqual(wind_rose['S'], {'percent': 0.25, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['E'], {'percent': 0.25, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['W'], {'percent': 0.25, 'mean_wind_speed': 10.0})


  def test_8_bin_wind_rose(self):
    a = WindRose(8)
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 45, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_wind(10, 135, datetime.datetime.now())
    a.add_wind(10, 180, datetime.datetime.now())
    a.add_wind(10, 225, datetime.datetime.now())
    a.add_wind(10, 270, datetime.datetime.now())
    a.add_wind(10, 315, datetime.datetime.now())

    wind_rose = a.get_wind_rose()
    self.assertEqual(wind_rose['N'], {'percent': 0.125, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['NE'], {'percent': 0.125, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['E'], {'percent': 0.125, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['SE'], {'percent': 0.125, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['S'], {'percent': 0.125, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['SW'], {'percent': 0.125, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['W'], {'percent': 0.125, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['NW'], {'percent': 0.125, 'mean_wind_speed': 10.0})

  # note that it all falls into E because 45 degrees
  # ends up rounding to E
  def test_4_bin_wind_rose_with_uneven_winds(self):
    a = WindRose(4)
    a.add_wind(10, 45, datetime.datetime.now())
    wind_rose = a.get_wind_rose()
    self.assertEqual(wind_rose['N'], {'percent': 0, 'mean_wind_speed': None})
    self.assertEqual(wind_rose['S'], {'percent': 0, 'mean_wind_speed': None})
    self.assertEqual(wind_rose['E'], {'percent': 1.0, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['W'], {'percent': 0, 'mean_wind_speed': None})

  # make sure that 44 degrees falls into north though
  def test_4_bin_wind_rose_with_44_degrees(self):
    a = WindRose(4)
    a.add_wind(10, 44, datetime.datetime.now())
    wind_rose = a.get_wind_rose()
    self.assertEqual(wind_rose['N'], {'percent': 1.0, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['S'], {'percent': 0, 'mean_wind_speed': None})
    self.assertEqual(wind_rose['E'], {'percent': 0, 'mean_wind_speed': None})
    self.assertEqual(wind_rose['W'], {'percent': 0, 'mean_wind_speed': None})
      
