import logging
import datetime
import os
import numpy as np
from pyproj import CRS
from osgeo import gdal, ogr, osr
from .file_storage import FileStorage

logger = logging.getLogger(__name__)

MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'

class RasterBand:

  def __init__(self, projection=None):
    self._tif = None
    self._band = None
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

    # projection stuff 
    self._datum = None
    self._epsg_code = None
    self._proj4_string = None
    self._projection_wkt = None

  def load_url(self, file_url, md5_hash=None):
    logger.debug("opening %s" % file_url)
    fs = FileStorage()
    fs.set_file_url(file_url)
    fs.download()
    self.loadf(fs.get_full_path_to_file())
  
  # this clones the raster band, returning a new 
  # raster band (using load array) but with the 
  # current ones parameters like transforms, etc
  def clone_with_new_data(self, nparray=None):
    if nparray is not None: # if we have new data
      assert nparray.shape[0] == self._rows, "Rows do not match"
      assert nparray.shape[1] == self._cols, "Cols do not match"
    new_file = RasterBand()
    new_file.blank_raster(self._rows, self._cols, 
      (self._pixel_w, self._pixel_h),
      (self._x_origin, self._y_origin))

    if nparray is None:
      nparray = np.full((self._rows, self._cols), self._nodata)

    new_file.load_array(nparray, self._nodata)
    new_file.set_projection(self._projection_wkt)
    return new_file

  def clone_with_no_data(self):
    if self.get_nodata() is None:
      raise ValueError("No nodata set on parent")
    return self.clone_with_new_data(None)

  def get_datum(self):
    return str(self._datum)

  def get_projection(self):
    return self._projection_wkt

  def get_projection_wkt(self):
    return self.get_projection()

  def get_projection_epsg(self):
    projection_wkt = self.get_projection()
    if projection_wkt is None:
      return
    crs = CRS.from_wkt(projection_wkt)
    return crs.to_epsg()

  def get_projection_proj4(self):
    projection_wkt = self.get_projection()
    if projection_wkt is None:
      return
    crs = CRS.from_wkt(projection_wkt)
    return crs.to_proj4()

  # sets the projection on the global tif/raster object
  # this is only for EPSG projections, if you want others
  # then you need to call set_projection with full string
  def set_projection_epsg(self, code):
    if code is None:
      logger.warning("Can't set projection to None")
      return
    if code == self._epsg_code:
      logger.warning(f"Projection already set to {epsg_code}")
      return
    crs = CRS.from_epsg(code)
    projection_wkt = crs.to_wkt()
    self.set_projection(projection_wkt)

  def set_projection_proj4(self, proj_string):
    if proj_string is None:
      logger.warning("Can't set projection to None")
      return
    crs = CRS.from_proj4(proj_string)
    projection_wkt = crs.to_wkt()
    self.set_projection(projection_wkt)

  def set_projection(self, projection_wkt):
    srs = osr.SpatialReference()
    srs.ImportFromWkt(projection_wkt)
    self._tif.SetProjection(srs.ExportToWkt())

    # now set the datum, etc
    crs = CRS.from_wkt(projection_wkt)
    self._datum = crs.datum
    self._epsg_code = crs.to_epsg()
    self._proj4_string = crs.to_proj4()
    self._projection_wkt = srs.ExportToWkt()

  # clips a raster map to a vector layer
  # by creating a mask which is the layer and then
  # applying it to the raster
  def clip_to_vector_layer_extent(self, vector_layer):
    self._throw_except_if_band_not_loaded()

    # make sure vector_layer and raster are in the same projection
    vector_layer_epsg = vector_layer.get_projection_epsg()
    raster_epsg = self.get_projection_epsg()
    if raster_epsg and vector_layer_epsg != raster_epsg:
      err = f"Vector layer and raster are in different projections: {vector_layer_epsg} != {raster_epsg}"
      raise ValueError(err)
    else:
      vector_layer_proj = vector_layer.get_projection_proj4()
      raster_proj = self.get_projection_proj4()
      if vector_layer_proj != raster_proj:
        err = f"Vector layer and raster are in different projections: {vector_layer_proj} != {raster_proj}"
        raise ValueError(err)

    extent_dict = vector_layer.get_extent()
    ul = (extent_dict['min_x'], extent_dict['max_y'])
    lr = (extent_dict['max_x'], extent_dict['min_y'])
    return self.clip_to_extent(ul, lr)

  # clips a map to a new extent
  def clip_to_extent(self, ul, lr):
    self._throw_except_if_band_not_loaded()

    (ul_row, ul_col) = self._map_xy_to_rowcol(ul[0], ul[1])
    (lr_row, lr_col) = self._map_xy_to_rowcol(lr[0], lr[1])

    logger.info(f"ul_row={ul_row} ul_col={ul_col} lr_row={lr_row} lr_col={lr_col}")

    if ul_row > lr_row or ul_col > lr_col:
      raise ValueError("Invalid extent")

    # if any values are less than 0 or greater than the rows/cols
    # then we need to adjust them
    ul_row = max(0, ul_row)
    ul_col = max(0, ul_col)
    lr_row = min(self._rows, lr_row)
    lr_col = min(self._cols, lr_col)

    # ok so now grab only elements of the array
    # that are in the range above
    data = self._band.ReadAsArray(ul_col, ul_row, lr_col - ul_col, lr_row - ul_row)
    data = np.where(data == self._nodata, np.nan, data)

    # now create the new clipped raster
    new_raster = RasterBand()
    new_raster.blank_raster(lr_row - ul_row, lr_col - ul_col,
      (self._pixel_w, self._pixel_h),
      (ul[0], ul[1]))
    new_raster.load_array(data)
    new_raster.set_projection(self._projection_wkt)
    return new_raster

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

  def reproject_epsg(self, epsg_code, width=None, height=None):
    crs = CRS.from_epsg(epsg_code)
    proj_wkt = crs.to_wkt()
    return self.reproject(proj_wkt, width, height)

  def reproject_proj4(self, proj_string, width=None, height=None):
    crs = CRS.from_proj4(proj_string)
    proj_wkt = crs.to_wkt()
    return self.reproject(proj_wkt, width, height)

  def reproject_mollweide(self, width=None, height=None):
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    return self.reproject_proj4(MOLLWEIDE, width, height)

  # reproject will return a new raster band in memory
  # that is in memory but has the new projection
  def reproject(self, projection_wkt, width=None, height=None):
    self._throw_except_if_band_not_loaded()
    if not self._tif.GetProjection():
      raise ValueError("No projection set on current map. Cannot reproject")
    to_srs = osr.SpatialReference()
    to_srs.ImportFromWkt(projection_wkt)
    crs = CRS.from_wkt(projection_wkt)
    code = crs.to_epsg()
    if code == 4326:
      to_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    from_srs = osr.SpatialReference()
    from_srs.ImportFromWkt(self._tif.GetProjection())
    if from_srs.GetAuthorityCode(None) == '4326':
      from_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(from_srs, to_srs)

    params = {'dstSRS': to_srs.ExportToWkt(),
      'format': 'MEM',
      'resampleAlg': gdal.GRA_NearestNeighbour,
      'warpOptions': [
        'NUM_THREADS=ALL_CPUS',
        'CONFIG GDAL_CACHEMAX 10000'
      ]}
    if height is not None:
      params['height'] = height
    if width is not None:
      params['width'] = width
    in_memory_output = gdal.Warp('', self._tif, **params) # MAIN CALL

    # this new map has a new set of geotransforms, etc
    new_pixel_width = abs(in_memory_output.GetGeoTransform()[1])
    new_pixel_height = abs(in_memory_output.GetGeoTransform()[5])
    new_x_origin = in_memory_output.GetGeoTransform()[0]
    new_y_origin = in_memory_output.GetGeoTransform()[3]

    new_raster = RasterBand()
    new_raster.blank_raster(self._rows, self._cols,
      (new_pixel_width, new_pixel_height),
      (new_x_origin, new_y_origin))
    new_raster._tif = in_memory_output
    new_raster.set_projection(projection_wkt)
    new_raster.set_band(1)   
    return new_raster

  def get_pixel_width(self):
    return self._pixel_w

  def get_pixel_height(self):
    return self._pixel_h

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

  def mean(self):
    return np.nanmean(self.values())

  def max(self):
    return np.nanmax(self.values())

  def min(self):
    return np.nanmin(self.values())

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

  # load raster band from a file
  def loadf(self, gtif):
    logger.debug("opening file %s" % gtif)
    if not os.path.exists(gtif):
      raise ValueError(f"File does not exist: {gtif}")
    self._tif = gdal.Open(gtif)
    self._storage_method = "FILE"
  
    # get projection from the file, in particular get the EPSG
    srs = osr.SpatialReference()
    projection_wkt = self._tif.GetProjection()
    srs.ImportFromWkt(projection_wkt)

    # use pyproj to parse this projection
    crs = CRS.from_wkt(projection_wkt)
    datum = crs.datum
    epsg_code = crs.to_epsg()

    # we only work with WGS84 maps for now
    if str(datum) not in ('WGS 84', 'World Geodetic System 1984'):
      raise ValueError("Only WGS84 maps are supported. Got %s" % datum)

    # get epsg and proj string 
    epsg_code = crs.to_epsg()
    proj_string = crs.to_proj4()
    logger.info(f"Loaded raster with Datum: {datum} EPSG: {epsg_code}")
    
    self._datum = datum
    self._epsg_code = epsg_code
    self._proj4_string = proj_string
    self._projection_wkt = projection_wkt

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
    center_x = x + (self._pixel_w/2) # we go left to right
    center_y = y - (self._pixel_h/2) # we go from the top down
    return (center_x, center_y)

  def write_to_file(self, output_filename, compress=False, overwrite=True):
    return self.save_to_file(output_filename, compress, overwrite)

  def save_to_file(self, output_filename, compress=False, overwrite=True):
    if os.path.exists(output_filename) and not overwrite:
      raise ValueError(f"File exists: {output_filename}")
    if self._projection_wkt is None:
      raise ValueError("No projection set on raster")
  
    options = []
    if compress:
      options = ['COMPRESS=LZW', 'BIGTIFF=YES']

    driver = gdal.GetDriverByName('GTiff')
    out_raster = driver.Create(output_filename, 
      self._cols, self._rows, 1, gdal.GDT_Float32,
      options=options)
    out_raster.SetGeoTransform((self._x_origin, self._pixel_w, 0, 
      self._y_origin, 0, -self._pixel_h))
    out_raster.SetProjection(self._tif.GetProjection())

    # add some metadata with generation date
    now_dt = datetime.datetime.now().isoformat()
    self.set_metadata('GENERATION_DATE', now_dt)
    out_raster.SetMetadata(self.get_metadata())

    # now write the data to the file
    out_band = out_raster.GetRasterBand(1)
    if self._nodata is not None:
      out_band.SetNoDataValue(self._nodata)
    out_band.WriteArray(self._band.ReadAsArray())
    out_band.FlushCache()

  def add_row(self, row_number, row_data):
    self._throw_except_if_band_not_loaded()
    
    # make sure row has the right width
    if len(row_data) != self._cols:
      raise ValueError(f"Row data does not match width of raster. Got {len(row_data)} expected {self._cols}")

    # make sure row number is in bounds
    if row_number < 0 or row_number >= self._rows:
      raise ValueError("Row number out of bounds")

    # if its a list, convert to an numpy array
    # and reshape
    if type(row_data) is list:
      row_data = np.array(row_data)
      row_data = row_data.reshape(1, -1)

    # then replace the existing data with this new data
    self._band.WriteArray(row_data, 0, row_number)

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
      data = [d if d != self._nodata else np.nan for d in data]
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

  def get_no_data(self):
    return self.get_nodata()

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

  # return the difference between left and right
  def central_diff_gradients(self):
    self._throw_except_if_band_not_loaded()
    arr = self.values()
    grad_x = np.zeros_like(arr, dtype=float)
    grad_y = np.zeros_like(arr, dtype=float)
    grad_x = np.roll(arr, -1, axis=1) - np.roll(arr, 1, axis=1)
    grad_y = np.roll(arr, -1, axis=0) - np.roll(arr, 1, axis=0)
    return grad_x, grad_y

  # x_res = x resolution, y_res = y resolution
  # needs to be in the same units as the raster
  def central_diff_slopes(self, x_res=None, y_res=None):
    if x_res is None:
      x_res = self._pixel_w
    if y_res is None:
      y_res = self._pixel_h
    logger.info(f"Calculating slopes with x_res={x_res} y_res={y_res}")
    self._throw_except_if_band_not_loaded()
    grad_x, grad_y = self.central_diff_gradients()
    # tan theta = opposite / adj
    slope_x = np.degrees(np.arctan(grad_x / (2 * x_res)))
    slope_y = np.degrees(np.arctan(grad_y / (2 * y_res)))
    return (slope_x, slope_y)
  
  # this one computes the bearing, where
  # N=0, E=90, S=180, W=270
  # it needs to use the gradients first to get the 
  # delta x, delta y
  # keep in mind that with most projections Y is going down
  def central_diff_face_bearing(self):
    self._throw_except_if_band_not_loaded()
    delta_x, delta_y = self.central_diff_gradients() 
    
    # create a mask of cases where both delta x and delta y are not zero
    bearings = np.full(delta_x.shape, np.nan)
    non_zero_mask = (delta_x != 0) | (delta_y != 0)

    # compute the bearings only for elements masked
    # note that arctan2 a positive result is counterclockwise
    # and a negative result is clockwise
    bearing_rad = np.arctan2(-delta_x[non_zero_mask], delta_y[non_zero_mask])
    bearing_deg = np.degrees(bearing_rad) 
    bearing_deg = np.where(bearing_deg < 0, bearing_deg + 360, bearing_deg)
    bearings[non_zero_mask] = bearing_deg

    return bearings

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

  # this helper function takes an x,y coordate and returns
  # which row and column that it maps to, this is useful for 
  # value lookups or if we're doing some kind of extent clipping
  def _map_xy_to_rowcol(self, x, y):
    row = int(np.floor((self._y_origin - y) / self._pixel_h))
    col = int(np.floor((x - self._x_origin) / self._pixel_w))
    return row, col

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
    row, col = self._map_xy_to_rowcol(x, y)
    data = self._band.ReadAsArray(col, row, 1, 1).tolist()[0][0]

    if data == self._nodata:
      return None

    return data
