import logging
import datetime
import os
import numpy as np
import numpy.ma as ma
from osgeo import gdal, ogr, osr
from .file_storage import FileStorage

logger = logging.getLogger(__name__)

class RasterBand:

  def __init__(self, projection=None):
    self._tif = None
    self._band = None
    self._epsg_projection = projection
    self._nodata = None
    self._cols = None
    self._rows = None
    self._x_origin = None
    self._y_origin = None
    self._pixel_w = None
    self._pixel_h = None
    self._storage_method = None
    self._extent = None
    self._metadata = None

  def load_url(self, file_url, md5_hash=None):
    logger.debug("opening %s" % file_url)
    fs = FileStorage()
    fs.set_file_url(file_url)
    fs.download()
    self.loadf(fs.get_full_path_to_file())
  
  # this clones the raster band, returning a new 
  # raster band (using load array) but with the 
  # current ones parameters like transforms, etc
  def clone_with_new_data(self, nparray):
    assert nparray.shape[0] == self._rows, "Rows do not match"
    assert nparray.shape[1] == self._cols, "Cols do not match"
    new_file = RasterBand()
    new_file.blank_raster(self._rows, self._cols, 
      (self._pixel_w, self._pixel_h),
      (self._x_origin, self._y_origin))
    new_file.load_array(nparray, self._nodata)
    new_file.set_projection(self._epsg_projection)
    return new_file

  def get_projection(self):
    return self._epsg_projection

  # sets the projection on the global tif/raster object
  def set_projection(self, epsg_code):
    if epsg_code is None:
      logger.warning("Can't set projection to None")
      return
    if epsg_code == self._epsg_projection:
      logger.warning(f"Projection already set to {epsg_code}")
      return

    # except if we already have a projection
    # and ask if user meant to reproject
    if self._epsg_projection is not None:
      raise ValueError(f"Projection already set to {self._epsg_projection}. Did you mean to reproject?")

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)
    self._tif.SetProjection(srs.ExportToWkt())
    self._epsg_projection = epsg_code

  def get_extent(self):
    self._throw_except_if_band_not_loaded()
    return self._extent

  # apply an arbitrary function over all grid cells
  # no idea how efficient this is
  def apply_function(self, func):
    self._throw_except_if_band_not_loaded()
    assert callable(func), "Function must be callable"
    self.load_array(func(self.values()))

  def get_bounds_from_epsg(self, epsg_code):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)
    area_of_use = srs.GetAreaOfUse()
    if area_of_use is not None:
      min_x = area_of_use.west_lon_degree
      min_y = area_of_use.south_lat_degree
      max_x = area_of_use.east_lon_degree
      max_y = area_of_use.north_lat_degree
      extent = (min_x, min_y, max_x, max_y)
    else:
      raise ValueError(f"Could not determine the extent for EPSG:{epsg_code}")
    return extent

  # reproject will return a new raster band in memory
  # that is in memory but has the new projection
  def reproject(self, epsg_code):
    self._throw_except_if_band_not_loaded()
    if not self._tif.GetProjection():
      raise ValueError("No projection set on current map. Cannot reproject")

    to_srs = osr.SpatialReference()
    to_srs.ImportFromEPSG(epsg_code)
    if epsg_code == 4326:
      to_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    from_srs = osr.SpatialReference()
    from_srs.ImportFromWkt(self._tif.GetProjection())
    if from_srs.GetAuthorityCode(None) == '4326':
      from_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    transform = osr.CoordinateTransformation(from_srs, to_srs)

    # use gdal warp which has better parallelism support
    in_memory_output = gdal.Warp(
      '', self._tif,
      dstSRS=to_srs.ExportToWkt(),
      format='MEM',
      warpOptions=[
        'NUM_THREADS=ALL_CPUS',
        'CONFIG GDAL_CACHEMAX 10000'
      ])

    new_raster = RasterBand()
    new_raster.blank_raster(self._rows, self._cols,
      (self._pixel_w, self._pixel_h),
      (self._x_origin, self._y_origin))
    new_raster._tif = in_memory_output
    new_raster.set_projection(epsg_code)
    new_raster.set_band(1)   
    return new_raster

  # This is important, it creates a blank in memory raster
  def blank_raster(self, rows, cols, pixel_widths=(1,1), ul=(0, 0), dtype=gdal.GDT_Float32):
    if type(pixel_widths) is int:
      pixel_widths = (pixel_widths, pixel_widths)
    self._tif = (gdal.GetDriverByName('MEM').Create('', cols, rows, 1, dtype))
    self._storage_method = "MEM"
    self._tif.SetGeoTransform((ul[0], pixel_widths[0], 0, ul[1], 0, -pixel_widths[1]))
    self._cols = cols
    self._rows = rows
    self._x_origin = ul[0]
    self._y_origin = ul[1]
    self._pixel_w = pixel_widths[0]
    self._pixel_h = pixel_widths[1]

  # load a numpy array into the raster band
  def load_array(self, nparray, nodata=-9999):
    if type(nparray) is list:
      nparray = np.array(nparray)

    if len(nparray.shape) != 2:
      raise ValueError("Array must be 2d")

    # if we dont yet have a tif set
    if self._tif is None:
      rows = nparray.shape[0]
      cols = nparray.shape[1]
      self.blank_raster(rows, cols)

    self._band = self._tif.GetRasterBand(1)
    logger.info(f"Writing array of shape {nparray.shape} to band")
    self._band.WriteArray(nparray)

    self.set_band(1) # working band
    if nodata is not None:
      self.set_nodata(nodata)

  def loadf(self, gtif):
    logger.debug("opening file %s" % gtif)
    if not os.path.exists(gtif):
      raise ValueError(f"File does not exist: {gtif}")
    self._tif = gdal.Open(gtif)
    self._storage_method = "FILE"
  
    # get projection from the file, in particular get the EPSG
    srs = osr.SpatialReference()
    srs.ImportFromWkt(self._tif.GetProjection())
    srs.AutoIdentifyEPSG()
    epsg_code = srs.GetAttrValue("AUTHORITY", 1)

    if epsg_code is not None:
      self._epsg_projection = int(epsg_code)
    else:
      raise ValueError("Could not determine EPSG code from file!")

  # number of bands in the whole file
  def band_count(self):
    return self._tif.RasterCount

  # upper left point
  def ul(self):
    return (self._x_origin, self._y_origin)

  def lr(self):
    return (self._x_origin + self._cols * self._pixel_w,
      self._y_origin - self._rows * self._pixel_h)

  def set_band(self, band_id):
    return self.load_band(band_id)

  def load_band(self, band_id=1):
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
    self._ns_res = abs(transform[5]) # n-s pixel resolution

    # set the extent of this band from the geotransform in native 
    # extent should be (minx, miny, maxx, maxy)
    self._extent = {'min_x': self._x_origin,
      'min_y': self._y_origin - (self._rows * self._pixel_h),
      'max_x': self._x_origin + (self._cols * self._pixel_w),
      'max_y': self._y_origin}

    # set any metadata from the field
    self._metadata = self._tif.GetMetadata()

  def get_metadata(self):
    return self._metadata

  def set_metadata(self, field, name):
    assert field is not None, "Field must not be None"
    self._metadata[field] = name
    self._tif.SetMetadata(self._metadata) # update underlying file

  def width(self):
    self._throw_except_if_band_not_loaded()
    return self._cols

  def height(self):
    self._throw_except_if_band_not_loaded()
    return self._rows

  # NOTE: if you call numpy.shape attribute on the band, it will
  # return you the shape of the numpy array which is (rows, cols)
  # this is the opposite of the shape method here
  def shape(self):
    return (self.width(), self.height())

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

  def write_to_file(self, output_filename, compress=False, overwrite=True):
    return self.save_to_file(output_filename, compress, overwrite)

  def save_to_file(self, output_filename, compress=False, overwrite=True):
    if os.path.exists(output_filename) and not overwrite:
      raise ValueError(f"File exists: {output_filename}")
    if self._epsg_projection is None:
      raise ValueError("No projection set on raster")
  
    options = []
    if compress:
      options = ['COMPRESS=LZW']

    driver = gdal.GetDriverByName('GTiff')
    out_raster = driver.Create(output_filename, 
      self._cols, self._rows, 1, gdal.GDT_Float32,
      options=options)
    out_raster.SetGeoTransform((self._x_origin, self._pixel_w, 0, 
      self._y_origin, 0, -self._pixel_h))
    out_raster.SetProjection(self._tif.GetProjection())

    # add some metadata with generation date
    from . import __version__
    now_dt = datetime.datetime.now().isoformat()
    self.set_metadata('GENERATION_DATE', now_dt)
    self.set_metadata('WXLOGS_VERSION', __version__)
    out_raster.SetMetadata(self.get_metadata())

    # now write the data to the file
    out_band = out_raster.GetRasterBand(1)
    if self._nodata is not None:
      out_band.SetNoDataValue(self._nodata)
    out_band.WriteArray(self._band.ReadAsArray())
    out_band.FlushCache()

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

  # get nodata from the band and the object here
  def get_nodata(self):
    self._throw_except_if_band_not_loaded()
    band_nodata = self._band.GetNoDataValue()
    assert band_nodata == self._nodata, "Nodata values do not match"
    return band_nodata

  # return the percentage of values that are nodata
  def percentage_nodata(self):
    self._throw_except_if_band_not_loaded()
    data = self.values()
    # count rows that are NOT nan
    nodata_count = np.count_nonzero(np.isnan(data))

    return nodata_count / data.size

  # return the values in the raster as a numpy array
  # note the values shape is rows + cols
  def values(self):
    self._throw_except_if_band_not_loaded()
    data = self._band.ReadAsArray()
    data = np.where(data == self._nodata, np.nan, data)
    return data

  # sum all the values in the array
  def sum(self):
    self._throw_except_if_band_not_loaded()
    return np.nansum(self.values())

  def gradients(self):
    self._throw_except_if_band_not_loaded()
    dx, dy = np.gradient(self.values())
    return dx, dy

  # dx = x resolution, dy = y resolution
  def periodic_gradients(self, dx=1.0, dy=1.0):
    self._throw_except_if_band_not_loaded()
    arr = self.values()
    grad_x = np.zeros_like(arr, dtype=float)
    grad_y = np.zeros_like(arr, dtype=float)
    grad_x = np.roll(arr, -1, axis=1) - np.roll(arr, 1, axis=1)
    grad_y = np.roll(arr, -1, axis=0) - np.roll(arr, 1, axis=0)
    grad_x /= (2 * dx)
    grad_y /= (2 * dy)
    return grad_x, grad_y
  
  # override the nodata value on everything
  def set_nodata(self, nodata):
    self._throw_except_if_band_not_loaded()

    if self._band.GetNoDataValue() is not None:
      if nodata != self._band.GetNoDataValue():
        logger.warning("NODATA value already set to %s" % self._band.GetNoDataValue())

    self._nodata = nodata
    if nodata is None:
      result_code = self._band.DeleteNoDataValue()
    else:
      result_code = self._band.SetNoDataValue(nodata)
    if result_code != 0:
      raise ValueError("Could not set nodata value")
    self._band.FlushCache()
    assert nodata == self._band.GetNoDataValue(), "NODATA not set"

  # note that this takes row, col notation, which is the standard
  # notation for this kind of stuff versus x,y
  def get_grid_value(self, row, col):
    self._throw_except_if_band_not_loaded()
    return self._band.ReadAsArray(col, row, 1, 1).tolist()[0][0]

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
