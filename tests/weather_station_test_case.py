import unittest
import os
import numpy as np
import json
import pytz
import datetime
from wx_logs import WeatherStation

class WeatherStationTestCase(unittest.TestCase):

  def test_simple(self):
    a = WeatherStation('BOUY')
    self.assertEqual(a.get_type(), 'BOUY')

    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), 1.5) 

  def test_simple_with_tow_single_day(self):
    a = WeatherStation('BOUY')
    a.enable_time_of_wetness()
    random_date = datetime.datetime(2020, 1, 1, 10, 0, 0)
    a.add_temp_c(25, random_date)
    a.add_humidity(100, random_date)
    tow = a.get_tow()
    years = tow.get_years()
    self.assertIn(2020, years.keys())

  def test_tow_and_enable_twice_make_sure_not_ovewritten(self):
    a = WeatherStation('BOUY')
    a.enable_time_of_wetness()
    random_date = datetime.datetime(2020, 1, 1, 10, 0, 0)
    a.add_temp_c(25, random_date)
    a.add_humidity(100, random_date)
    tow = a.get_tow()
    years = tow.get_years()
    self.assertIn(2020, years.keys())

    a.enable_time_of_wetness()
    years = a.get_tow().get_years()
    self.assertIn(2020, years.keys())

  def test_tow_with_weather_once_a_day(self):
    a = WeatherStation('STATION')
    a.enable_time_of_wetness()
    c = 0
    for i in range(1, 13):
      for j in range(1, 29):
        random_date = datetime.datetime(2021, i, j, 10, 0, 0)
        a.add_temp_c(25, random_date)
        a.add_humidity(100, random_date)
        c += 1

    # we only did months and days above, so it should be 336/8760
    # which is a QA fail
    years = a.get_tow().get_years()
    self.assertEqual(len(years), 1)
    self.assertIn(2021, years.keys())
    data_2021 = years[2021]
    self.assertEqual(data_2021['max_hours'], 8760)
    self.assertEqual(data_2021['percent_valid'], round(c/8760.0, 4))
    self.assertEqual(data_2021['total_hours'], c)
    self.assertEqual(data_2021['qa_state'], 'FAIL')
    self.assertEqual(data_2021['time_of_wetness'], None)

  def test_tow_with_a_full_year_data(self):
    a = WeatherStation('STATION')
    a.enable_time_of_wetness()
    c = 0
    for i in range(1, 13):
      for j in range(1, 29):
        for h in range(0, 24):
          t = -10
          if h % 2 == 0:
            t = 10 
          random_date = datetime.datetime(2021, i, j, h, 0, 0)
          a.add_temp_c(t, random_date)
          a.add_humidity(81, random_date)
          c += 1
    serialized = json.loads(a.serialize_summary())
    self.assertEqual(serialized['air']['time_of_wetness']['by_year']['2021']['time_of_wetness'], 8760 * 0.5)
    self.assertEqual(serialized['air']['time_of_wetness']['annual_time_of_wetness'], 8760 * 0.5)

  def test_set_field_with_elevation_custom(self):
    a = WeatherStation('BOUY')
    a.set_location(41.87, -87.62)
    a.set_field('elevation', 100)
    self.assertEqual(a.get_location(), {'latitude': 41.87,
      'longitude': -87.62, 'elevation': 100})

  def test_temp_of_100c_throws_error(self):
    a = WeatherStation('BOUY')
    a.set_on_error('FAIL_QA')
    a.add_temp_c(100, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'FAIL')

  def test_using_dewpoint_to_humidity(self):
    a = WeatherStation('BOUY')
    self.assertAlmostEqual(a._dewpoint_to_relative_humidity(10, 5), 71.04, places=2)
    self.assertEqual(a._dewpoint_to_relative_humidity(10, 10), 100)
    a.add_dewpoint_c(5, 10, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), 71.04)

  def test_pm25(self):
    a = WeatherStation('STATION')
    a.add_pm25(10, datetime.datetime.now())
    a.add_pm25(20, datetime.datetime.now())
    self.assertEqual(a.get_pm25('MEAN'), 15)

  def test_make_Sure_negative_temps_are_ok(self):
    a = WeatherStation('STATION')
    a.add_temp_c(-10, datetime.datetime.now())
    a.add_temp_c(-20, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), -15)

  def test_serialize_summary_when_no_wind_set(self):
    a = WeatherStation('BOUY')
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
    a = WeatherStation('STATION')
    a.add_pressure_hpa(1000, datetime.datetime.now())
    a.add_pressure_hpa(1000.0, datetime.datetime.now())
    a.add_pressure_hpa("1000.00", datetime.datetime.now())
    a.add_pressure_hpa("", datetime.datetime.now())
    a.add_pressure_hpa(None, datetime.datetime.now())
    self.assertEqual(a.get_pressure_hpa('MEAN'), 1000)

  def test_putting_nan_and_none_into_humidity_mean_still_works(self):
    a = WeatherStation('STATION')
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(None, datetime.datetime.now())
    a.add_humidity('', datetime.datetime.now())
    a.add_humidity(np.nan, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), 75)

  # add precipitation, but precip is tricky because its a measure
  # over the past N minutes so we need to be able to normalize
  # for that
  def test_adding_preciptiation(self):
    dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
    a = WeatherStation('STATION')
    a.add_precipitation_mm(10, 60, dt)
    self.assertEqual(a.get_precipitation_mm('SUM'), 10)

  def test_adding_two_hours_of_precip(self):
    dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
    dt_one_hour_later = datetime.datetime(2020, 1, 1, 1, 0, 0)
    a = WeatherStation('STATION')
    a.add_precipitation_mm(10, 60, dt)
    a.add_precipitation_mm(20, 60, dt_one_hour_later)
    self.assertEqual(a.get_precipitation_mm('SUM'), 30)

  def test_adding_two_with_same_hour(self):
    dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
    dt2 = datetime.datetime(2020, 1, 1, 0, 20, 0)
    a = WeatherStation('STATION')
    a.add_precipitation_mm(10, 60, dt)
    a.add_precipitation_mm(20, 60, dt2)
    self.assertEqual(a.get_precipitation_mm('SUM'), 20)

  def test_adding_three_hours_of_precip(self):
    dt = datetime.datetime(2020, 1, 1, 0, 0, 0)
    dt_one_hour_later = datetime.datetime(2020, 1, 1, 1, 0, 0)
    dt_two_hours_later = datetime.datetime(2020, 1, 1, 2, 0, 0)
    a = WeatherStation('STATION')
    a.add_precipitation_mm(0, 60, dt)
    a.add_precipitation_mm(20, 60, dt_one_hour_later)
    a.add_precipitation_mm(30, 60, dt_two_hours_later)
    self.assertEqual(a.get_precipitation_mm('SUM'), 50)
    self.assertAlmostEqual(a.get_precipitation_mm('MEAN'), 16.666, 2)

  def test_putting_nans_and_nones_into_temperature_too(self):
    a = WeatherStation('STATION')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    a.add_temp_c(None, datetime.datetime.now())
    a.add_temp_c('', datetime.datetime.now())
    a.add_temp_c(np.nan, datetime.datetime.now())
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)

  def test_setting_elevation(self):
    a = WeatherStation('STATION')
    a.set_location(41.87, -87.62, 100)
    a.set_elevation(200)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': 200})
    self.assertEqual(a.get_elevation(), 200)

  def test_wind_rose_one_direction(self):
    a = WeatherStation('STATION')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 0, datetime.datetime.now())
    wind_rose = a.get_wind_rose()
    self.assertEqual(wind_rose['N'], {'percent': 100.0, 'mean_wind_speed': 10.0})

    s = json.loads(a.serialize_summary())
    serialized_rose = s['air']['wind']['rose']
    self.assertEqual(serialized_rose['N'], {'percent': 100.0, 'mean_wind_speed': 10.0})

  def test_wind_rose_two_directions(self):
    a = WeatherStation('STATION')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    wind_rose = a.get_wind_rose()
    self.assertEqual(wind_rose['N'], {'percent': 50.0, 'mean_wind_speed': 10.0})
    self.assertEqual(wind_rose['E'], {'percent': 50.0, 'mean_wind_speed': 10.0})

    s = json.loads(a.serialize_summary())
    serialized_rose = s['air']['wind']['rose']
    self.assertEqual(serialized_rose['N'], {'percent': 50.0, 'mean_wind_speed': 10.0})
    self.assertEqual(serialized_rose['E'], {'percent': 50.0, 'mean_wind_speed': 10.0})

  def test_months_in_the_dates_fields(self):
    a = WeatherStation('STATION')
    a.add_temp_c(1, '2020-01-01 00:00:00')
    a.add_temp_c(2, '2020-02-01 00:00:00')
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)
    self.assertEqual(a.get_months('air_temp_c'), {1: 1, 2: 1, 3:0, 4:0, 5:0, 
      6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0})
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), False)

  def test_elevation_record_on_station(self):
    a = WeatherStation('STATION')
    a.set_location(41.87, -87.62, 100)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': 100})

  def test_elevation_negative_throw_exception(self):
    a = WeatherStation('STATION')
    self.assertRaises(ValueError, a.set_location, 41.87, -87.62, -100)

  def test_elevation_as_string(self):
    a = WeatherStation('STATION')
    a.set_location(41.87, -87.62, '100')
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': 100})

  def test_elevation_as_none(self):
    a = WeatherStation('STATION')
    a.set_location(41.87, -87.62, None)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': None})

  def test_elevation_cannot_be_gt_than_mt_everest(self):
    a = WeatherStation('STATION')
    self.assertRaises(ValueError, a.set_location, 41.87, -87.62, 9000)

  def test_set_elevation_function(self):
    a = WeatherStation('STATION')
    a.set_elevation(100)
    self.assertEqual(a.get_location(), {'latitude': None, 
      'longitude': None, 'elevation': 100})

  def test_is_full_year_any_month_of_zero_means_no(self):
    a = WeatherStation('STATION')
    a.add_temp_c(1, '2020-01-01 00:00:00')
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), False)

  def test_is_full_year_of_data_to_be_true(self):
    a = WeatherStation('STATION')
    for i in range(1, 13):
      a.add_temp_c(10, f'2020-{i}-01 00:00:00')
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), True)

  def test_is_full_year_of_data_with_one_month_two_x(self):
    a = WeatherStation('STATION')
    for i in range(1, 13):
      a.add_temp_c(10, f'2020-{i}-01 00:00:00')
    a.add_temp_c(10, f'2021-01-01 00:00:00')
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), True)

  def test_nans_and_nones_in_wind_variables(self):
    a = WeatherStation('STATION')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    a.add_wind(None, 180, datetime.datetime.now())
    a.add_wind('', 180, datetime.datetime.now())
    a.add_wind(np.nan, 180, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 10)
    self.assertEqual(a.get_wind('VECTOR_MEAN'), (7.07, 45, 'NE'))

  def test_pressure_value_as_string(self):
    a = WeatherStation('STATION')
    a.add_pressure_hpa(1000, '2020-04-02 12:33:09')
    a.add_pressure_hpa('1000', '2020-04-02 12:34:09')
    a.add_pressure_hpa('1000', datetime.datetime.now())
    self.assertEqual(a.get_pressure_hpa('MEAN'), 1000)

  def test_negative_pressure_throws_Exception(self):
    a = WeatherStation('STATION')
    self.assertRaises(ValueError, a.add_pressure_hpa, -10, datetime.datetime.now())

  def test_is_qa_pass(self):
    a = WeatherStation('STATION')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    self.assertEqual(a.get_qa_status(), 'PASS')
    self.assertEqual(a.is_qa_pass(), True)

  def test_zero_pressure_throws_Exception(self):
    a = WeatherStation('STATION')
    self.assertRaises(ValueError, a.add_pressure_hpa, 0, datetime.datetime.now())

  def test_add_wind_speed_knots(self):
    a = WeatherStation('STATION')

    # these will convert to m/s
    a.add_wind_speed_knots(10, datetime.datetime.now())
    a.add_wind_speed_knots(20, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 7.72)

  def test_negative_pm25_throws_exception(self):
    a = WeatherStation('STATION')
    self.assertRaises(ValueError, a.add_pm25, -20, datetime.datetime.now())

  def test_more_complex_pm25(self):
    a = WeatherStation('STATION')
    a.add_pm25(10, datetime.datetime.now())
    a.add_pm25(20, datetime.datetime.now())
    a.add_pm25(30, datetime.datetime.now())
    self.assertEqual(a.get_pm25('MEAN'), 20)

  def test_pm10(self):
    a = WeatherStation('STATION')
    a.add_pm10(10, datetime.datetime.now())
    a.add_pm10(20, datetime.datetime.now())
    self.assertEqual(a.get_pm10('MEAN'), 15)

  def test_station_id_name_and_owner(self):
    a = WeatherStation('STATION')
    a.set_station_id('BOUY')
    self.assertEqual(a.get_station_id(), 'BOUY')

    a.set_station_name('BOUY')
    self.assertEqual(a.get_station_name(), 'BOUY')

    a.set_station_owner('BOUY')
    self.assertEqual(a.get_station_owner(), 'BOUY')

  def test_serialize_with_tow_included(self):
    a = WeatherStation('STATION')
    a.enable_time_of_wetness()
    random_date = datetime.datetime(2020, 1, 1, 10, 0, 0)
    a.add_temp_c(25, random_date)
    a.add_humidity(100, random_date)
    years = a.get_tow().get_years()
    self.assertIn(2020, years.keys())

    summary = json.loads(a.serialize_summary())
    self.assertEqual(summary['air']['time_of_wetness']['by_year']['2020']['time_of_wetness'], None)
    self.assertEqual(summary['air']['time_of_wetness']['by_year']['2020']['qa_state'], 'FAIL')
    self.assertEqual(summary['air']['time_of_wetness']['by_year']['2020']['percent_valid'], round(1.0/8760.0, 4))
    self.assertEqual(summary['air']['time_of_wetness']['by_year']['2020']['max_hours'], 366 * 24) # leap
    self.assertEqual(summary['air']['time_of_wetness']['by_year']['2020']['total_hours'], 1)


  def test_serialize_with_precipitation(self):
    a = WeatherStation('STATION')
    dt0 = datetime.datetime(2020, 1, 1, 0, 0, 0)
    total = 0 
    for i in range(0, 24):
      a.add_precipitation_mm(1, 60, dt0 + datetime.timedelta(hours=i))
      total += 1 
    summary = a.serialize_summary()
    summary = json.loads(summary)
    self.assertEqual(summary['air']['precipitation']['sum'], total)
    self.assertEqual(summary['air']['precipitation']['annual_mean'], None)

  def test_serialize_summary_function(self):
    a = WeatherStation('BOUY')
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
    a = WeatherStation('BOUY')
    a.set_timezone("UTC")
    self.assertEqual(a.get_timezone(), "UTC")

  def test_dates_as_strings(self):
    a = WeatherStation('BOUY')
    a.add_temp_c(1, '2018-01-01 00:00:00')
    a.add_temp_c(2, '2018-02-01 00:00:00')
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)

  def test_min_max_dates(self):
    a = WeatherStation('BOUY')
    a.add_temp_c(1, '2018-01-01 00:00:00')
    a.add_temp_c(2, '2018-01-01 00:00:00')
    a.add_temp_c(3, '2014-01-01 00:00:00')
    (mind, maxd) = a.get_date_range('air_temp_c', False)
    self.assertEqual(mind, datetime.datetime(2014, 1, 1, 0, 0))
    self.assertEqual(maxd, datetime.datetime(2018, 1, 1, 0, 0))

  def test_invalid_humidity_values(self):
    a = WeatherStation('STATION')
    a.set_on_error('FAIL_QA')
    a.add_humidity(111, datetime.datetime.now())
    a.add_humidity(-1, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'FAIL')

  def test_vector_sum_wind_speed_and_regular(self):
    a = WeatherStation('BOUY')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 10)
    self.assertEqual(a.get_wind('VECTOR_MEAN'), (7.07, 45, 'NE'))

  def test_invalid_humidity_is_ignored(self):
    a = WeatherStation('STATION')
    a.set_on_error('IGNORE')
    a.add_humidity(111, datetime.datetime.now())
    a.add_humidity(-1, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), None)
    self.assertEqual(a.get_qa_status(), 'PASS') 

  def test_humidity_field(self):
    a = WeatherStation('BOUY')
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    self.assertEqual(a.get_humidity('MEAN'), 83.33)

  def test_adding_a_none_to_pressure(self):
    a = WeatherStation('STATION')
    a.add_pressure_hpa(None, datetime.datetime.now())
    a.add_pressure_hpa(1015.02, datetime.datetime.now())
    self.assertEqual(a.get_pressure_hpa('MEAN'), 1015.02)

  def test_invalid_long_and_lat(self):
    a = WeatherStation('BOUY')
    self.assertRaises(ValueError, a.set_location, 91, 180)
    self.assertRaises(ValueError, a.set_location, -91, -180)

  # need to also support adding wind speed and direction
  # in separate calls instead of a single one
  def test_wind_speed_and_dir_separate(self):
    a = WeatherStation('BOUY')
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
    a = WeatherStation('BOUY')
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
    a = WeatherStation('BOUY')
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
    a = WeatherStation('BOUY')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    wind_vector = a.get_wind('VECTOR_MEAN')
    self.assertEqual(wind_vector[0], 7.07)
    self.assertEqual(wind_vector[1], 45)
    self.assertEqual(wind_vector[2], 'NE')
    self.assertEqual(a.get_wind_speed('MEAN'), 10)

  def test_dont_all_merging_different_location(self):
    a = WeatherStation('BOUY')
    a.set_location(41.87, -87.62)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': None})
    b = WeatherStation('BOUY')
    b.set_location(41.87, -87.63)
    self.assertRaises(ValueError, a.merge_in, b)

  def test_create_two_WeatherStation_and_merge_them(self):
    a = WeatherStation('BOUY')
    a.add_temp_c(1, datetime.datetime.now())
    a.add_temp_c(2, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())
    a.add_humidity(50, datetime.datetime.now())
    a.add_humidity(100, datetime.datetime.now())

    b = WeatherStation('BOUY')
    b.add_temp_c(2, datetime.datetime.now())
    b.add_temp_c(3, datetime.datetime.now())
    b.add_humidity(100, datetime.datetime.now())
    b.add_humidity(50, datetime.datetime.now())
    b.add_humidity(100, datetime.datetime.now())

    a.merge_in(b)
    self.assertEqual(a.get_temp_c('MEAN'), 2)
    self.assertEqual(a.get_humidity('MEAN'), 83.33)

  def test_serialize_both_vector_mean_and_mean_for_wind(self):
    a = WeatherStation('BOUY')
    a.add_wind(10, 0, datetime.datetime.now())
    a.add_wind(10, 90, datetime.datetime.now())
    self.assertEqual(a.get_wind_speed('MEAN'), 10)
    self.assertEqual(a.get_wind('VECTOR_MEAN'), (7.07, 45, 'NE'))

    serialized = json.loads(a.serialize_summary())
    self.assertEqual(serialized['air']['wind']['speed']['mean'], 10)
    self.assertEqual(serialized['air']['wind']['speed']['vector_mean'], 7.07)

  def test_save_and_load_methods(self):
    a = WeatherStation('BOUY')
    a.add_temp_c(1, '2020-04-02 12:33:09')
    a.add_temp_c(2, datetime.datetime.now())
    a.add_humidity(100, '2020-04-02 12:33:09')
    a.add_humidity(50, datetime.datetime.now())
    a.save('test.joblib')
    a2 = WeatherStation.load('test.joblib')
    self.assertEqual(a2.get_temp_c('MEAN'), 1.5)
    self.assertEqual(a2.get_humidity('MEAN'), 75)
    os.remove('test.joblib')

  def test_location_field(self):
    a = WeatherStation('STATION')
    a.set_location(41.87, -87.62)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': None})

    a.set_location('41.87', -87.62, 100)
    self.assertEqual(a.get_location(), {'latitude': 41.87, 
      'longitude': -87.62, 'elevation': 100})
