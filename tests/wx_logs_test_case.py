import unittest
import json
import pytz
import datetime
from src.wx_logs import wx_logs

class WxLogsTestCase(unittest.TestCase):

  def test_simple(self):
    a = wx_logs('BOUY')
    self.assertEqual(a.get_type(), 'BOUY')

    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), 1.5) 

  def test_temp_of_100c_throws_error(self):
    a = wx_logs('BOUY')
    a.set_on_error('IGNORE')
    a.add_temp_c(100, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'FAIL')

  def test_pm25(self):
    a = wx_logs('STATION')
    a.add_pm25(10, datetime.datetime.now())
    a.add_pm25(20, datetime.datetime.now())
    self.assertEqual(a.get_pm25('MEAN'), 15)

  def test_pm10(self):
    a = wx_logs('STATION')
    a.add_pm10(10, datetime.datetime.now())
    a.add_pm10(20, datetime.datetime.now())
    self.assertEqual(a.get_pm10('MEAN'), 15)

  def test_station_id_name_and_owner(self):
    a = wx_logs('STATION')
    a.set_station_id('BOUY')
    self.assertEqual(a.get_station_id(), 'BOUY')

    a.set_station_name('BOUY')
    self.assertEqual(a.get_station_name(), 'BOUY')

    a.set_station_owner('BOUY')
    self.assertEqual(a.get_station_owner(), 'BOUY')

  def test_serialize_summary_function(self):
    a = wx_logs('BOUY')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_pm25(10, datetime.datetime.now())
    a.add_pm10(10, datetime.datetime.now())
    a.set_location(41.87, -87.62)
    a.set_station_id('BOUY')
    a.set_station_name('BOUY NAME')
    a.set_station_owner('BOUY OWNER')
    a.set_timezone('UTC')
    a.set_on_error('IGNORE')

    summary = json.loads(a.serialize_summary())

    self.assertEqual(summary['type'], 'BOUY')
    self.assertEqual(summary['air']['temp_c']['mean'], 1.5)
    self.assertEqual(summary['air']['temp_c']['min'], 1)
    self.assertEqual(summary['air']['temp_c']['max'], 2)
    self.assertEqual(summary['air']['humidity']['mean'], 83.33)
    self.assertEqual(summary['air']['humidity']['min'], 50)
    self.assertEqual(summary['air']['humidity']['max'], 100)
    self.assertEqual(summary['air']['wind']['speed']['vector_mean'], 7.07)
    self.assertEqual(summary['air']['wind']['bearing']['vector_mean'], 45)
    self.assertEqual(summary['air']['wind']['bearing']['vector_string'], 'NE')
    self.assertEqual(summary['air']['pm25']['mean'], 10)
    self.assertEqual(summary['air']['pm10']['count'], 1)
    self.assertEqual(summary['station']['location']['latitude'], 41.87)
    self.assertEqual(summary['station']['location']['longitude'], -87.62)
    self.assertEqual(summary['station']['id'], 'BOUY')
    self.assertEqual(summary['station']['name'], 'BOUY NAME')
    self.assertEqual(summary['station']['owner'], 'BOUY OWNER')

  def set_timezones(self):
    a = wx_logs('BOUY')
    a.set_timezone("UTC")
    self.assertEqual(a.get_timezone(), "UTC")

  def test_dates_as_strings(self):
    a = wx_logs('BOUY')
    a.add_temp_c(1, '2018-01-01 00:00:00')
    a.add_temp_c(2, '2018-01-01 00:00:00')
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)

  def test_min_max_dates(self):
    a = wx_logs('BOUY')
    a.add_temp_c(1, '2018-01-01 00:00:00')
    a.add_temp_c(2, '2018-01-01 00:00:00')
    a.add_temp_c(3, '2014-01-01 00:00:00')
    (mind, maxd) = a.get_date_range('air_temp_c')
    self.assertEqual(mind, datetime.datetime(2014, 1, 1, 0, 0))
    self.assertEqual(maxd, datetime.datetime(2018, 1, 1, 0, 0))

  def test_invalid_humidity_values(self):
    a = wx_logs('STATION')
    a.set_on_error('IGNORE')
    a.add_humidity(101, datetime.datetime.now())
    a.add_humidity(-1, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'FAIL')

  def test_humidity_field(self):
    a = wx_logs('BOUY')
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), 83.33)

  def test_invalid_long_and_lat(self):
    a = wx_logs('BOUY')
    self.assertRaises(ValueError, a.set_location, 91, 180)
    self.assertRaises(ValueError, a.set_location, -91, -180)

  # test the wind speed and direction but note that were
  # using the dominant wind direction and speed
  # so for test case, use 0 and 90 and the vector mean is 45 deg
  def test_wind_speed_and_dir_to_vector(self):
    a = wx_logs('BOUY')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    wind_vector = a.get_wind('VECTOR_MEAN')
    self.assertEqual(wind_vector[0], 7.07)
    self.assertEqual(wind_vector[1], 45)
    self.assertEqual(wind_vector[2], 'NE')
    self.assertEqual(a.get_wind_speed('MEAN'), 10)

  def test_dont_all_merging_different_location(self):
    a = wx_logs('BOUY')
    a.set_location(41.87, -87.62)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': None})
    b = wx_logs('BOUY')
    b.set_location(41.87, -87.63)
    self.assertRaises(ValueError, a.merge_in, b)

  def test_create_two_wx_logs_and_merge_them(self):
    a = wx_logs('BOUY')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())

    b = wx_logs('BOUY')
    b.add_temp_c(2, datetime.datetime.now())
    b.add_temp_c(3, datetime.datetime.now())
    b.add_humidity(100, datetime.datetime.now())
    b.add_humidity(50, datetime.datetime.now())
    b.add_humidity(100, datetime.datetime.now())

    a.merge_in(b)
    self.assertEqual(a.get_temp_c('MEAN'), 2)
    self.assertEqual(a.get_humidity('MEAN'), 83.33)

  def test_location_field(self):
    a = wx_logs('STATION')
    a.set_location(41.87, -87.62)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': None})

    a.set_location('41.87', -87.62, 100)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': 100})
