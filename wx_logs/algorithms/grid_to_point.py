# this library is primary for taking 
# a raster file, which is a grid
# and convertint it to a point file, which
# is a vector
#
# 1 raster -> 1 vector
#
from ..raster_band import RasterBand
from ..vector_layer import VectorLayer
from osgeo import ogr, osr
import numpy as np
import logging

logger = logging.getLogger(__name__)

class GridToPoint:

  def __init__(self, raster_band_object):
    assert isinstance(raster_band_object, RasterBand)
    self.raster_band_object = raster_band_object

  # create a new in memory vector layer
  # keep the same SRS as the raster
  # add a field called value, which is the raster value
  def to_vector(self):
    vector_layer = VectorLayer()
    vector_layer.createmem('grid_to_point')
    vector_layer.create_layer('grid_to_point', 'POINT', 
      self.raster_band_object.get_projection_wkt())
    vector_layer.add_field_defn('value', 'float')

    total_rows = self.raster_band_object.height()

    # iterate through cols and make sure we use the centroid
    rows_completed = 0
    for cols in self.raster_band_object.rows(True): # centroid
      for (centroid_points, value) in cols:
        centroid = ogr.Geometry(ogr.wkbPoint)
        centroid.AddPoint_2D(centroid_points[0], centroid_points[1])

        feature = vector_layer.blank_feature()
        feature.SetGeometry(centroid)

        if value is not None and np.isnan(value) == False:
          feature.SetField('value', float(value))
          vector_layer.add_feature(feature)
      rows_completed += 1
      if rows_completed % 100 == 0:
        logger.info('Completed %s/%s rows', rows_completed, total_rows)

    return vector_layer
