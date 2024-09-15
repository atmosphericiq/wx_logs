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

# for each row, we're going to want to open up the 
# vector file in read mode, filter it and then find
# distances
def calculate_row(row_data):
  row_output = []
  for (center_pt, col) in row_data:
    center_geom = ogr.Geometry(ogr.wkbPoint)
    center_geom.AddPoint(center_pt[0], center_pt[1])
    row_output.append(1)
  return row_output

class RasterDistanceToVector:

  def __init__(self, raster_band_object, cpus=None):
    assert isinstance(raster_band_object, RasterBand)
    self.raster_band = raster_band_object

  def calculate_distances(self, vector_layer):
    # check if vector_layer is an instance of VectorLayer
    assert isinstance(vector_layer, VectorLayer), "vector_layer must be an instance of VectorLayer"

    with Pool(processes=os.cpu_count()) as pool:
      # for reach row in the grid, we will pass it to another function
      # that will calculate the distance to the nearest vector object
      # and return the distance value
      total_rows = self.raster_band.height()
      logger.info(f"Calculating distances for {total_rows} rows")
      pool_of_rows = []
      for row in self.raster_band.rows(True):

        # serialize the vector object so we can use it in workers

        result_row = pool.apply_async(calculate_row, args=(row,))
        pool_of_rows.append(result_row)
        if len(pool_of_rows) % 100 == 0:
          logging.info(f"Putting {len(pool_of_rows)}/{total_rows} rows into queue")

      # create a new band and we're going to add one row at a time into this band
      b2 = self.raster_band.clone_with_no_data()
      count = 0
      for row in pool_of_rows:
        try:
          result = row.get()
        except Exception as e:
          logger.error(f"Error calculating row: {e}")
          raise e

        print(result)
        b2.add_row(count, result)
        count += 1
        if count % 100 == 0:
          logger.info(f"Processed {count}/{total_rows} rows")

      return b2
