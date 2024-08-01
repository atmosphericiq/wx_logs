import logging
import os
import numpy as np
import numpy.ma as ma
from osgeo import gdal, ogr
from .file_storage import FileStorage

logger = logging.getLogger(__name__)

class RasterBand:

  def __init__(self):
    self._tif = None
    self._band = None
    self._nodata = None
    self._cols = None
    self._rows = None
    self._x_origin = None
    self._y_origin = None
    self._pixel_w = None
    self._pixel_h = None

  def load_url(self, file_url, md5_hash=None):
    logger.debug("opening %s" % file_url)
    fs = FileStorage()
    fs.set_file_url(file_url)
    fs.download()
    self.loadf(fs.get_full_path_to_file())
  
  def loadf(self, gtif):
    logger.debug("opening %s" % gtif)
    if not os.path.exists(gtif):
      raise ValueError(f"File does not exist: {gtif}")
    self._tif = gdal.Open(gtif)

  def band_count(self):
    return self._tif.RasterCount

  def load_band(self, band_id=1):
    # make sure the band exists
    if band_id > self.band_count():
      raise ValueError(f"Invalid band id: {band_id}")
    self._band = self._tif.GetRasterBand(band_id)
    self._nodata = self._band.GetNoDataValue()
    logger.debug("nodata value = %s" % self._nodata)
    self._cols = self._tif.RasterXSize
    self._rows = self._tif.RasterYSize
    # geotransform is (top left x, w-e pixel resolution, rotation, top left y, rotation, n-s pixel resolution)
    transform = self._tif.GetGeoTransform()
    self._x_origin = transform[0] # top left x
    self._y_origin = transform[3] # top left y
    self._pixel_w = transform[1] # w-e pixel resolution
    self._pixel_h = -transform[5] # n-s pixel resolution, negative because y increases down
    self._we_res = transform[1] # w-e pixel resolution
    self._ns_res = transform[5] # n-s pixel resolution

  def shape(self):
    self._throw_except_if_band_not_loaded()
    return (self._cols, self._rows)

  def size(self):
    self._throw_except_if_band_not_loaded()
    return self._cols * self._rows

  def _throw_except_if_band_not_loaded(self):
    if self._band is None:
      raise ValueError("No band loaded")

  # returns the centroid for a given box, where the point
  # is the UL point
  def _centroid(self, x, y):
    center_x = x + (self._pixel_w/2)
    center_y = y + (self._pixel_h/2)
    return (center_x, center_y)

  def rows(self, return_centroids=False):
    for i in range(self._rows):
      y = self._y_origin - (i * self._pixel_h)
      x = self._x_origin
      if return_centroids is True:
        coords = [self._centroid(x + (j * self._pixel_w), y) \
          for j in range(self._cols)]
      else:
        coords = [(x + (j * self._pixel_w), y) for j in range(self._cols)]
      data = self._band.ReadAsArray(0, i, self._cols, 1)[0]
      data = [d if d != self._nodata else None for d in data]
      yield list(zip(coords, data))

  def get_bbox_polygon(self):
    self._throw_except_if_band_not_loaded()
    bbox = self.get_bbox()
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(bbox[0][0], bbox[0][1])
    ring.AddPoint(bbox[1][0], bbox[0][1])
    ring.AddPoint(bbox[1][0], bbox[1][1])
    ring.AddPoint(bbox[0][0], bbox[1][1])
    ring.AddPoint(bbox[0][0], bbox[0][1])
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly

  # return tupble of (ul, lr) coordinates
  def get_bbox(self):
    self._throw_except_if_band_not_loaded()
    ul = (self._x_origin, self._y_origin)
    lr = (self._x_origin + self._cols * self._pixel_w,
      self._y_origin - self._rows * self._pixel_h)
    return (ul, lr)

  # get the centerpoint of the raster in the coordinate system
  # the raster is in
  def get_center(self):
    self._throw_except_if_band_not_loaded()
    return (self._x_origin + (self._cols * self._pixel_w / 2.0),
            self._y_origin - (self._rows * self._pixel_h / 2.0))

  def get_nodata(self):
    return self._nodata

  def set_nodata(self, nodata):
    self._nodata = nodata

  # retrieve a single value at a location
  # the x,y values are in the coordinate system of the raster
  def get_value(self, x, y):
    self._throw_except_if_band_not_loaded()

    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(x, y)

    # get the bbox and determine if the point is inside of it
    # by using gdal functions + intersection
    bbox_polygon = self.get_bbox_polygon()
    if not bbox_polygon.Contains(point):
      raise ValueError(f"Point outside raster: {x}, {y}")

    # now we need to figure out which row and column we are in
    # make sure to consider resolution and negative y axis
    col = int(np.floor(np.abs(self._y_origin - y) / self._pixel_h)) 
    row = int(np.floor(np.abs(x - self._x_origin) / self._pixel_w))

    data = self._band.ReadAsArray(row, col, 1, 1).tolist()[0][0]

    if data == self._nodata:
      return None

    return data
