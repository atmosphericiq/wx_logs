import unittest
import numpy as np
import json
import pytz
import datetime
from wx_logs import wx_logs

class WxLogsTestCase(unittest.TestCase):

  def test_simple(self):
    a = wx_logs('BOUY')
    self.assertEqual(a.get_type(), 'BOUY')

    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), 1.5) 

  def test_temp_of_100c_throws_error(self):
    a = wx_logs('BOUY')
    a.set_on_error('FAIL_QA')
    a.add_temp_c(100, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'FAIL')

  def test_using_dewpoint_to_humidity(self):
    a = wx_logs('BOUY')
    self.assertAlmostEqual(a._dewpoint_to_relative_humidity(10, 5), 71.04, places=2)
    self.assertEqual(a._dewpoint_to_relative_humidity(10, 10), 100)
    a.add_dewpoint_c(5, 10, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), 71.04)

  def test_pm25(self):
    a = wx_logs('STATION')
    a.add_pm25(10, datetime.datetime.now())
    a.add_pm25(20, datetime.datetime.now())
    self.assertEqual(a.get_pm25('MEAN'), 15)

  def test_make_Sure_negative_temps_are_ok(self):
    a = wx_logs('STATION')
    a.add_temp_c(-10, datetime.datetime.now())
    a.add_temp_c(-20, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), -15)

  def test_serialize_summary_when_no_wind_set(self):
    a = wx_logs('BOUY')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
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
    self.assertEqual(summary['air']['pm25']['mean'], 10)
    self.assertEqual(summary['air']['pm10']['count'], 1)
    self.assertEqual(summary['station']['location']['latitude'], 41.87)
    self.assertEqual(summary['station']['location']['longitude'], -87.62)
    self.assertEqual(summary['station']['id'], 'BOUY')
    self.assertEqual(summary['station']['name'], 'BOUY NAME')
    self.assertEqual(summary['station']['owner'], 'BOUY OWNER')

  def test_pressure_in_different_formats(self):
    a = wx_logs('STATION')
    a.add_pressure_hpa(1000, datetime.datetime.now())
    a.add_pressure_hpa(1000.0, datetime.datetime.now())
    a.add_pressure_hpa("1000.00", datetime.datetime.now())
    a.add_pressure_hpa("", datetime.datetime.now())
    a.add_pressure_hpa(None, datetime.datetime.now())
    self.assertEqual(a.get_pressure_hpa('MEAN'), 1000)

  def test_putting_nan_and_none_into_humidity_mean_still_works(self):
    a = wx_logs('STATION')
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(None, datetime.datetime.now())
    a.add_humidity('', datetime.datetime.now())
    a.add_humidity(np.nan, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), 75)

  def test_putting_nans_and_nones_into_temperature_too(self):
    a = wx_logs('STATION')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    a.add_temp_c(None, datetime.datetime.now())
    a.add_temp_c('', datetime.datetime.now())
    a.add_temp_c(np.nan, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)

  def test_4_bin_wind_rose(self):
    a = wx_logs('STATION')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_wind(10, 180, datetime.datetime.now())
    a.add_wind(10, 270, datetime.datetime.now())

    wind_rose = a.get_wind_rose(4)
    self.assertEqual(wind_rose['N'], 10)
    self.assertEqual(wind_rose['E'], 10)
    self.assertEqual(wind_rose['S'], 10)
    self.assertEqual(wind_rose['W'], 10)

  def test_bearing_to_direction_4_8_16_bins(self):
    a = wx_logs('STATION')
    self.assertEqual(a.bearing_to_direction(0, 4), 'N')
    self.assertEqual(a.bearing_to_direction(0, 8), 'N')
    self.assertEqual(a.bearing_to_direction(0, 16), 'N')
    self.assertEqual(a.bearing_to_direction(45, 4), 'E')
    self.assertEqual(a.bearing_to_direction(45, 8), 'NE')
    self.assertEqual(a.bearing_to_direction(45, 16), 'NE')
    self.assertEqual(a.bearing_to_direction(90, 4), 'E')
    self.assertEqual(a.bearing_to_direction(90, 8), 'E')
    self.assertEqual(a.bearing_to_direction(90, 16), 'E')
    self.assertEqual(a.bearing_to_direction(135, 4), 'S')
    self.assertEqual(a.bearing_to_direction(135, 8), 'SE')
    self.assertEqual(a.bearing_to_direction(135, 16), 'SE')

  def test_8_bin_wind_rose(self):
    a = wx_logs('STATION')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 45, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_wind(10, 135, datetime.datetime.now())
    a.add_wind(10, 180, datetime.datetime.now())
    a.add_wind(10, 225, datetime.datetime.now())
    a.add_wind(10, 270, datetime.datetime.now())
    a.add_wind(10, 315, datetime.datetime.now())

    wind_rose = a.get_wind_rose(8)
    self.assertEqual(wind_rose['N'], 10)
    self.assertEqual(wind_rose['NE'], 10)
    self.assertEqual(wind_rose['E'], 10)
    self.assertEqual(wind_rose['SE'], 10)
    self.assertEqual(wind_rose['S'], 10)
    self.assertEqual(wind_rose['SW'], 10)
    self.assertEqual(wind_rose['W'], 10)
    self.assertEqual(wind_rose['NW'], 10)

  # note that it all falls into E because 45 degrees
  # ends up rounding to E
  def test_4_bin_wind_rose_with_uneven_winds(self):
    a = wx_logs('STATION')
    a.add_wind(10, 45, datetime.datetime.now())
    wind_rose = a.get_wind_rose(4)
    self.assertEqual(wind_rose['N'], 0)
    self.assertEqual(wind_rose['E'], 10)
    self.assertEqual(wind_rose['S'], 0)
    self.assertEqual(wind_rose['W'], 0)

  def test_months_in_the_dates_fields(self):
    a = wx_logs('STATION')
    a.add_temp_c(1, '2020-01-01 00:00:00')
    a.add_temp_c(2, '2020-02-01 00:00:00')
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)
    self.assertEqual(a.get_months('air_temp_c'), {1: 1, 2: 1, 3:0, 4:0, 5:0, 
      6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0})
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), False)

  def test_is_full_year_any_month_of_zero_means_no(self):
    a = wx_logs('STATION')
    a.add_temp_c(1, '2020-01-01 00:00:00')
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), False)

  def test_is_full_year_of_data_to_be_true(self):
    a = wx_logs('STATION')
    for i in range(1, 13):
      a.add_temp_c(10, f'2020-{i}-01 00:00:00')
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), True)

  def test_is_full_year_of_data_with_one_month_two_x(self):
    a = wx_logs('STATION')
    for i in range(1, 13):
      a.add_temp_c(10, f'2020-{i}-01 00:00:00')
    a.add_temp_c(10, f'2021-01-01 00:00:00')
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), True)

  def test_nans_and_nones_in_wind_variables(self):
    a = wx_logs('STATION')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_wind(None, 180, datetime.datetime.now())
    a.add_wind('', 180, datetime.datetime.now())
    a.add_wind(np.nan, 180, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 10)
    self.assertEqual(a.get_wind('VECTOR_MEAN'), (7.07, 45, 'NE'))

  def test_pressure_value_as_string(self):
    a = wx_logs('STATION')
    a.add_pressure_hpa(1000, '2020-04-02 12:33:09')
    a.add_pressure_hpa('1000', '2020-04-02 12:34:09')
    a.add_pressure_hpa('1000', datetime.datetime.now())
    self.assertEqual(a.get_pressure_hpa('MEAN'), 1000)

  def test_negative_pressure_throws_Exception(self):
    a = wx_logs('STATION')
    self.assertRaises(ValueError, a.add_pressure_hpa, -10, datetime.datetime.now())

  def test_is_qa_pass(self):
    a = wx_logs('STATION')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    self.assertEqual(a.get_qa_status(), 'PASS')
    self.assertEqual(a.is_qa_pass(), True)

  def test_zero_pressure_throws_Exception(self):
    a = wx_logs('STATION')
    self.assertRaises(ValueError, a.add_pressure_hpa, 0, datetime.datetime.now())

  def test_add_wind_speed_knots(self):
    a = wx_logs('STATION')

    # these will convert to m/s
    a.add_wind_speed_knots(10, datetime.datetime.now())
    a.add_wind_speed_knots(20, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 7.72)

  def test_negative_pm25_throws_exception(self):
    a = wx_logs('STATION')
    self.assertRaises(ValueError, a.add_pm25, -20, datetime.datetime.now())

  def test_more_complex_pm25(self):
    a = wx_logs('STATION')
    a.add_pm25(10, datetime.datetime.now())
    a.add_pm25(20, datetime.datetime.now())
    a.add_pm25(30, datetime.datetime.now())
    self.assertEqual(a.get_pm25('MEAN'), 20)

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
    a.add_temp_c(2, '2018-02-01 00:00:00')
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)

  def test_min_max_dates(self):
    a = wx_logs('BOUY')
    a.add_temp_c(1, '2018-01-01 00:00:00')
    a.add_temp_c(2, '2018-01-01 00:00:00')
    a.add_temp_c(3, '2014-01-01 00:00:00')
    (mind, maxd) = a.get_date_range('air_temp_c', False)
    self.assertEqual(mind, datetime.datetime(2014, 1, 1, 0, 0))
    self.assertEqual(maxd, datetime.datetime(2018, 1, 1, 0, 0))

  def test_invalid_humidity_values(self):
    a = wx_logs('STATION')
    a.set_on_error('FAIL_QA')
    a.add_humidity(111, datetime.datetime.now())
    a.add_humidity(-1, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'FAIL')

  def test_vector_sum_wind_speed_and_regular(self):
    a = wx_logs('BOUY')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 10)
    self.assertEqual(a.get_wind('VECTOR_MEAN'), (7.07, 45, 'NE'))

  def test_invalid_humidity_is_ignored(self):
    a = wx_logs('STATION')
    a.set_on_error('IGNORE')
    a.add_humidity(111, datetime.datetime.now())
    a.add_humidity(-1, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'PASS') 

  def test_humidity_field(self):
    a = wx_logs('BOUY')
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), 83.33)

  def test_adding_a_none_to_pressure(self):
    a = wx_logs('STATION')
    a.add_pressure_hpa(None, datetime.datetime.now())
    a.add_pressure_hpa(1015.02, datetime.datetime.now())
    self.assertEqual(a.get_pressure_hpa('MEAN'), 1015.02)

  def test_invalid_long_and_lat(self):
    a = wx_logs('BOUY')
    self.assertRaises(ValueError, a.set_location, 91, 180)
    self.assertRaises(ValueError, a.set_location, -91, -180)

  # need to also support adding wind speed and direction
  # in separate calls instead of a single one
  def test_wind_speed_and_dir_separate(self):
    a = wx_logs('BOUY')
    a.add_wind_speed(10, '2020-04-02 12:33:09')
    a.add_wind_bearing(90, '2020-04-02 12:33:09')
    a.add_wind_speed(10, '2020-04-02 12:34:09')
    a.add_wind_bearing(0, '2020-04-02 12:34:09')
    wind_vector = a.get_wind('VECTOR_MEAN')
    self.assertEqual(wind_vector[0], 7.07)
    self.assertEqual(wind_vector[1], 45)
    self.assertEqual(wind_vector[2], 'NE')
    self.assertEqual(a.get_wind_speed('MEAN'), 10)
    self.assertEqual(a.get_wind_speed('MIN'), 10)
    self.assertEqual(a.get_wind_speed('MAX'), 10)

  def test_wind_speed_with_different_max_mins(self):
    a = wx_logs('BOUY')
    a.add_wind_speed(10, '2020-04-02 12:33:09')
    a.add_wind_bearing(90, '2020-04-02 12:33:09')
    a.add_wind_speed(20, '2020-04-02 12:34:09')
    a.add_wind_bearing(0, '2020-04-02 12:34:09')
    a.add_wind_speed(30, '2020-04-02 12:35:09')
    a.add_wind_bearing(-90, '2020-04-02 12:35:09')
    self.assertEqual(a.get_wind_speed('MEAN'), 20)
    self.assertEqual(a.get_wind_speed('MIN'), 10)
    self.assertEqual(a.get_wind_speed('MAX'), 30)

  def test_wind_speed_and_dir_seperate_more_complex(self):
    a = wx_logs('BOUY')
    a.add_wind_speed(10, '2020-04-02 12:33:09')
    a.add_wind_bearing(90, '2020-04-02 12:33:09')
    a.add_wind_speed(10, '2020-04-02 12:34:09')
    a.add_wind_bearing(0, '2020-04-02 12:34:09')
    a.add_wind_speed(10, '2020-04-02 12:35:09')
    a.add_wind_bearing(-90, '2020-04-02 12:35:09')
    a.add_wind_speed(14, '2023-04-02 14:35:09') # 2023
    wind_vector = a.get_wind('VECTOR_MEAN')
    self.assertEqual(wind_vector[0], 3.33)
    self.assertEqual(wind_vector[1], 0)
    self.assertEqual(wind_vector[2], 'N')

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

  def test_serialize_both_vector_mean_and_mean_for_wind(self):
    a = wx_logs('BOUY')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 10)
    self.assertEqual(a.get_wind('VECTOR_MEAN'), (7.07, 45, 'NE'))

    serialized = json.loads(a.serialize_summary())
    self.assertEqual(serialized['air']['wind']['speed']['mean'], 10)
    self.assertEqual(serialized['air']['wind']['speed']['vector_mean'], 7.07)

  def test_location_field(self):
    a = wx_logs('STATION')
    a.set_location(41.87, -87.62)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': None})

    a.set_location('41.87', -87.62, 100)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': 100})
