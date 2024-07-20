import unittest
from wx_logs import wx_logs, wx_collection

class WxCollectionTestCase(unittest.TestCase):

  def test_wx_collection(self):
    a = wx_logs('STATION')
    a.set_station_id(1234)
    a.add_temp_c(1, '2020-01-01 00:00:00')
    a.add_temp_c(2, '2020-02-01 00:00:00')
    self.assertEqual(a.get_temp_c('MEAN'), 1.5)
    self.assertEqual(a.get_months('air_temp_c'), {1: 1, 2: 1, 3:0, 4:0, 5:0,
      6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0})
    self.assertEqual(a.is_full_year_of_data('air_temp_c'), False)

    c = wx_collection()
    c.add_station(a)
    self.assertEqual(c.num_stations(), 1)

  def test_wx_collection_add_and_find_station(self):
    a = wx_logs('STATION')
    a.set_station_id(1234)
    a.add_temp_c(1, '2020-01-01 00:00:00')
    a.add_temp_c(2, '2020-02-01 00:00:00')
    c = wx_collection()
    c.add_station(a)
    self.assertEqual(c.get_station_by_id(1234), a)
    self.assertEqual(c.get_station_by_id(1235), None)

  def test_wx_new_station_function(self):
    c = wx_collection()
    s = c.new_station('STATION', 1234)
    self.assertEqual(c.get_station_by_id(1234).get_station_id(), '1234')
    self.assertEqual(c.get_station_by_id(1234).get_station_type(), 'STATION')

  def test_collection_returns_generator_for_stations_call(self):
    c = wx_collection()
    c.new_station('STATION', 1234)
    c.new_station('STATION', 1235)
    c.new_station('STATION', 1236)
    self.assertEqual(len(list(c.stations())), 3)
