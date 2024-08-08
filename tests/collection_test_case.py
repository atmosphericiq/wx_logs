import unittest
from wx_logs import WeatherStation, Collection

class CollectionTestCase(unittest.TestCase):

  def test_Collection(self):
    a = WeatherStation('STATION')
    a.set_station_id(1234)
    a.add_temp_c(1, '2020-01-01 00:00:00')
    a.add_temp_c(2, '2020-02-01 00:00:00')
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)
    self.assertEqual(a.get_months('air_temp_c'), {1: 1, 2: 1, 3:0, 4:0, 5:0,
      6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0})
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), False)

    c = Collection()
    c.add_station(a)
    self.assertEqual(c.num_stations(), 1)

  def test_collection_append_elevations(self):
    dem_s3_path = 'https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif'
    dem_s3_md5 = 'cc5ed81758347a5fa3a4902974e532b8'
    a = WeatherStation('STATION')
    a.set_station_id(1234)
    a.set_location(41.10, -87.0, None)

    b = WeatherStation('STATION')
    b.set_station_id(1235)
    b.set_location(0, 0, None)

    c = Collection()
    c.add_station(a)
    c.add_station(b)
    c.append_elevations_from_dem(dem_s3_path, dem_s3_md5)

    # assert each station has the right elevation
    self.assertEqual(c.get_station_by_id(1234).get_elevation(), 208)
    self.assertEqual(c.get_station_by_id(1235).get_elevation(), None)

  def test_collection_append_elevation_but_dont_override_if_close(self):
    dem_s3_path = 'https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif'
    dem_s3_md5 = 'cc5ed81758347a5fa3a4902974e532b8'
    a = WeatherStation('STATION')
    a.set_station_id(1234)
    a.set_location(41.10, -87.0, 205)
    c = Collection()
    c.add_station(a)
    c.append_elevations_from_dem(dem_s3_path, dem_s3_md5)
    self.assertEqual(c.get_station_by_id(1234).get_elevation(), 205)

  def test_Collection_add_and_find_station(self):
    a = WeatherStation('STATION')
    a.set_station_id(1234)
    a.add_temp_c(1, '2020-01-01 00:00:00')
    a.add_temp_c(2, '2020-02-01 00:00:00')
    c = Collection()
    c.add_station(a)
    self.assertEqual(c.get_station_by_id(1234), a)
    self.assertEqual(c.get_station_by_id(1235), None)

  def test_wx_new_station_function(self):
    c = Collection()
    s = c.new_station('STATION', 1234)
    self.assertEqual(c.get_station_by_id(1234).get_station_id(), '1234')
    self.assertEqual(c.get_station_by_id(1234).get_station_type(), 'STATION')

  def test_collection_returns_generator_for_stations_call(self):
    c = Collection()
    c.new_station('STATION', 1234)
    c.new_station('STATION', 1235)
    c.new_station('STATION', 1236)
    self.assertEqual(len(list(c.stations())), 3)
