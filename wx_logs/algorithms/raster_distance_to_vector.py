# RasterDistanceToVector
# this algorith is primarily for taking an empty
# raster band and computing the distance to the 
# nearest vector object 
# 
# Example: Raster Distance to Ocean
# Example: Raster Distance to Roads

from ..raster_band import RasterBand
from ..vector_layer import VectorLayer
from osgeo import ogr, osr
import numpy as np
import logging
import os
from multiprocessing import Pool

logger = logging.getLogger(__name__)

class RasterDistanceToVector:

  def __init__(self, raster_band_object, cpus=None):
    assert isinstance(raster_band_object, RasterBand)
    self.raster_band = raster_band_object
    if cpus:
      self.pool = Pool(cpus)
    else:
      self.pool = Pool(os.cpu_count())

  def calculate_distances(self, vector_layer):

    # check if vector_layer is an instance of VectorLayer
    assert isinstance(vector_layer, VectorLayer), "vector_layer must be an instance of VectorLayer"

    # for reach row in the grid, we will pass it to another function
    # that will calculate the distance to the nearest vector object
    # and return the distance value
    total_rows = self.raster_band.height()
    logger.info(f"Calculating distances for {total_rows} rows")
    for row in self.raster_band.rows(True):
      result_row = self.pool.apply_async(self._calculate_row, args=(row,))
      print(result_row)

    # create a new band and we're going to add one row at a time into this band


    return vector_layer

  def _calculate_row(self, row_data):
    return row_data
