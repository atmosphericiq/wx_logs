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

logger = logging.getLogger(__name__)

class RasterDistanceToVector:

  def __init__(self, raster_band_object):
    assert isinstance(raster_band_object, RasterBand)
    self.raster_band_object = raster_band_object

  def calculate(self):

    return vector_layer
