import json
import os
import joblib
import logging
import datetime
from .weather_station import WeatherStation
from .kriger import Kriger
from .raster_band import RasterBand
from .file_storage import FileStorage

logger = logging.getLogger(__name__)

MISMATCH_THRESH_M = 25

class Collection:

  def __init__(self):
    self._stations = {}
    self._dem_band = None

  def add_station(self, station):
    if not isinstance(station, WeatherStation):
      logger.error("Invalid station type")
      return
    station_id = station.get_station_id()
    if station_id is None:
      raise Exception("Cannot add station without an ID!")
    station_id = str(station_id)
    self._stations[station_id] = station

  # downloads the DEM data
  def _get_dem_band(self, file_location, file_md5):
    s = FileStorage()
    s.set_file_url(file_location)
    s.set_expected_md5_hash(file_md5)
    s.download()
    self._dem_band = RasterBand()
    self._dem_band.loadf(s.get_full_path_to_file())
    self._dem_band.load_band(1)

  # append elevation will combine DEM elevation rasters
  # with the station data, to make sure we can set the right
  # elevation on all the points
  def append_elevations_from_dem(self, dem_s3_path, dem_md5, none_to_zero=True):
    if self._dem_band is None:
      logger.warning("DEM Band needs to download. Please wait.")
      self._get_dem_band(dem_s3_path, dem_md5)
    for (station_id, station) in self._stations.items():
      location = station.get_location()
      latitude = location['latitude']
      longitude = location['longitude']
      current_elevation = station.get_elevation()
      matched_val = self._dem_band.get_value(longitude, latitude)

      # if matched_val is None, that usually means ocean, so elev = 0
      if none_to_zero and matched_val is None:
        matched_val = 0.0

      if current_elevation is not None and matched_val is not None:
        if abs(current_elevation - matched_val) > MISMATCH_THRESH_M:
          station.set_elevation(matched_val)
      else:
        station.set_elevation(matched_val)

  # use joblib to save to file, use gzip
  def save(self, filename):
    assert filename is not None, "Filename cannot be None"
    joblib.dump(self, filename, compress=3)

  # load from file
  @staticmethod
  def load(filename):
    assert filename is not None, "Filename cannot be None"
    return joblib.load(filename)

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
