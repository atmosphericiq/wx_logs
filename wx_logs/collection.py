import json
import logging
import datetime
from .weather_station import WeatherStation
from .kriger import Kriger
from .raster_band import RasterBand
from .file_storage import FileStorage

logger = logging.getLogger(__name__)

class Collection:

  def __init__(self):
    self._stations = {}

  def add_station(self, station):
    if not isinstance(station, WeatherStation):
      logger.error("Invalid station type")
      return
    station_id = station.get_station_id()
    if station_id is None:
      raise Exception("Cannot add station without an ID!")
    station_id = str(station_id)
    self._stations[station_id] = station

  # append elevation will combine DEM elevation rasters
  # with the station data, to make sure we can set the right
  # elevation on all the points
  def append_elevation_data(self):
    pass

  # this will take a single variable on all stations
  # and krige it over some period of time
  def krige_single_variable(self, variable_name):
    pass

  def new_station(self, station_type, station_id):
    station_id = str(station_id)
    s = WeatherStation(station_type)
    s.set_station_id(station_id)
    self.add_station(s)
    return s

  def num_stations(self):
    return len(self._stations)

  def get_station_by_id(self, station_id):
    station_id = str(station_id)
    return self._stations.get(station_id)

  def stations(self):
    for (station_id, station) in self._stations.items():
      yield station
