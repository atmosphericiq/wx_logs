# VectorLayer
# main vector layer code

import os
import json
import shutil
import logging
import numpy as np
from shapely.strtree import STRtree
from shapely.geometry import Point
from shapely import wkt
from pyproj import CRS
from osgeo import ogr, osr
from .file_storage import FileStorage

logger = logging.getLogger(__name__)

epsg3857 = osr.SpatialReference()
epsg3857.ImportFromEPSG(3857)
epsg4326 = osr.SpatialReference()
epsg4326.ImportFromEPSG(4326)
epsg4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

SHAPE_TYPES = ['POINT', 'LINE', 'POLYGON', 'MULTIPOLYGON']
PROJECTIONS = [4326, 3857]

class VectorLayer:

  def __init__(self):
    # basic file input/output stuff
    self._driver = None
    self._driver_name = None
    self._file_path = None
    self._datasource = None
    self._layer = None
    self._fields = {}

    # projection stuff
    self._datum = None
    self._epsg_code = None
    self._proj4_string = None
    self._projection_wkt = None

    # in memory stuff, note that they 
    # will be keyed by ID
    self._spatial_index = None
    self._features = {}
    self._geometries = {} # shapely geoms
    self._extent = {'min_x': None, 'max_x': None, 
      'min_y': None, 'max_y': None}

    # FID is the integer that tracks feature IDs
    self._max_fid = 0

  def get_layer(self):
    if self.get_driver_name() == 'MEMORY':
      return self._features.values()
    else:
      return self._layer

  def get_name(self):
    return self._layer.GetName()

  def set_spatial_filter(self, geom):
    if self.get_driver_name() == 'MEMORY':
      raise ValueError("Cannot set spatial filter on in-memory layer")
    self._layer.SetSpatialFilter(geom)

  def reset_spatial_filter(self):
    if self.get_driver_name() == 'MEMORY':
      raise ValueError("Cannot reset spatial filter on in-memory layer")
    self._layer.SetSpatialFilter(None)

  def load_url(self, file_url, md5_hash=None):
    logger.debug("opening %s" % file_url)
    fs = FileStorage()
    fs.set_file_url(file_url)
    fs.download()
     
    # if its a zip file, we need to unzip the file
    # and then pick the new path as the file we load
    if fs.is_zip_file() is True:
      fs.unzip()

    return self.loadf(fs.get_full_path_to_file())

  def get_feature_count(self):
    if self.get_driver_name() == 'MEMORY':
      return len(self._features)
    else:
      feature_count = self._layer.GetFeatureCount()
      self._layer.ResetReading()
      return feature_count

  # add a feature to the layer, note that we have to do
  # some checking on FIDs
  def add_feature(self, ogr_feature):
    ogr_feature.SetFID(self._max_fid)
  
    # if we're using MEMORY then put into local array
    if self.get_driver_name() == 'MEMORY':
      self._features[self._max_fid] = ogr_feature

      # also set any geometries 
      shapely_geom = wkt.loads(ogr_feature.GetGeometryRef().ExportToWkt())
      self._geometries[self._max_fid] = shapely_geom

      # also update the extents
      geom = ogr_feature.GetGeometryRef()
      min_x, max_x, min_y, max_y = geom.GetEnvelope()
      if self._extent['min_x'] is None or min_x < self._extent['min_x']:
        self._extent['min_x'] = min_x
      if self._extent['max_x'] is None or max_x > self._extent['max_x']:
        self._extent['max_x'] = max_x
      if self._extent['min_y'] is None or min_y < self._extent['min_y']:
        self._extent['min_y'] = min_y
      if self._extent['max_y'] is None or max_y > self._extent['max_y']:
        self._extent['max_y'] = max_y
    else:
      self._layer.CreateFeature(ogr_feature)

    self._max_fid += 1

    return ogr_feature

  def get_extent(self):
    if self.get_driver_name() == 'MEMORY':
      return self._extent
    else: # use the layer extent  
      extent = self._layer.GetExtent()
      min_x, max_x, min_y, max_y = extent
      payload = {'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y}
      return payload

  # copies an old feature, creates a new one but
  # with the proper layer defn
  def copy_feature(self, ogr_feature):
    old_defn = ogr_feature.GetDefnRef()
    feature_defn = self._layer.GetLayerDefn()
    new_feature = ogr.Feature(feature_def=feature_defn)
    old_geom = ogr_feature.GetGeometryRef()
    new_geom = old_geom.Clone()

    # if the SRS dont match, then we have to reproject
    old_authority = (old_defn.GetGeomFieldDefn(0)
      .GetSpatialRef()
      .GetAttrValue("AUTHORITY", 1))
    new_authority = (feature_defn.GetGeomFieldDefn(0)
      .GetSpatialRef()
      .GetAttrValue("AUTHORITY", 1))
    if old_authority != new_authority:
      new_geom = self.reproject_geom(old_geom.Clone(),
        int(old_authority), int(new_authority))
    new_feature.SetGeometry(new_geom)

    new_field_names = []
    for i in range(feature_defn.GetFieldCount()):
      new_name = feature_defn.GetFieldDefn(i).GetName()
      new_field_names.append(new_name)

    for i in range(old_defn.GetFieldCount()):
      old_name = old_defn.GetFieldDefn(i).GetName()
      if old_name in new_field_names:
        new_feature.SetField(old_name, ogr_feature.GetField(old_name))
    return new_feature

  # reproject a single geometry obj
  def reproject_geom(self, geom, old_epsg, new_epsg=4326):
    new_geom = geom.Clone()
    epsg_from = osr.SpatialReference()
    epsg_from.ImportFromEPSG(old_epsg)
    epsg_to = osr.SpatialReference()
    epsg_to.ImportFromEPSG(new_epsg)
    if old_epsg == 4269:
      epsg_from.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if new_epsg == 4326:
      epsg_to.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform_func = osr.CoordinateTransformation(epsg_from, epsg_to)
    new_geom.Transform(transform_func)
    return new_geom

  def blank_feature(self, geometry=None):
    feature_defn = self._layer.GetLayerDefn()
    feature = ogr.Feature(feature_def=feature_defn)
    if type(geometry) in [list, tuple]:
      geometry = (float(i) for i in geometry)
      point = ogr.Geometry(ogr.wkbPoint)
      point.AddPoint(*geometry)
      feature.SetGeometry(point)
    elif geometry is not None:
      feature.SetGeometry(geometry)
    return feature

  # clones the current object to an in-memory object
  # useful for speeding things up + testing 
  def clone_to_memory(self, old_layer, copy_features=True):
    assert type(old_layer) == VectorLayer, "Invalid layer type"
    mem_layer = VectorLayer()
    mem_layer.createmem(old_layer.get_name())
    mem_layer.copy_blank_layer(old_layer, old_layer.get_name())
    mem_layer.auto_set_projection()
    for feature in old_layer._layer:
      mem_layer.add_feature(feature.Clone())
    return mem_layer

  def reproject_epsg(self, new_epsg):
    crs = CRS.from_epsg(new_epsg)
    return self._reproject(crs.to_wkt())

  def reproject_proj4(self, proj4_string):
    crs = CRS.from_proj4(proj4_string)
    return self._reproject(crs.to_wkt())
  
  # return feature off the stack
  def get_feature(self, feature_id=None):
    if self.get_driver_name() == 'MEMORY':
      assert feature_id is not None, "Feature ID is required"
      return self._features[feature_id]
    return self._layer.GetNextFeature()

  def _reproject(self, projection_wkt):
    crs = CRS.from_wkt(projection_wkt)
    projection_wkt = crs.to_wkt()

    mem_layer = VectorLayer()
    mem_layer.createmem(self._layer.GetName())
    mem_layer.copy_blank_layer(self, self._layer.GetName(), projection_wkt)

    source_srs = self._layer.GetSpatialRef()
    target_srs = osr.SpatialReference()
    target_srs.ImportFromWkt(projection_wkt)
    transform = osr.CoordinateTransformation(source_srs, target_srs)

    # now reproject the individual features
    for feature in self.get_layer():
      geom = feature.GetGeometryRef()
      geom.Transform(transform)
      fid = feature.GetFID()
      feature.SetGeometry(geom)
      feature.SetFID(fid)
      mem_layer.add_feature(feature)

    # GDAL 3.7 will support the below
    # self._layer.SetActiveSRS(target_srs)
    mem_layer.auto_set_projection()
    return mem_layer

  # this will copy all the features from the current
  # layer to a new layer, including all the fields
  def copy_features(self, new_layer):
    assert self.get_projection_wkt() == new_layer.get_projection_wkt(), "Projections do not match"
    old_defn = self._layer.GetLayerDefn()
    new_defn = new_layer.get_layer().GetLayerDefn()
    old_field_names = [old_defn.GetFieldDefn(i).GetName() for i in range(old_defn.GetFieldCount())]
    new_field_names = [new_defn.GetFieldDefn(i).GetName() for i in range(new_defn.GetFieldCount())]
    assert old_field_names == new_field_names, "Field names do not match"

    # then copy the features
    for i in range(self.get_feature_count()):
      old_feature = self.get_feature(i)
      new_feature = new_layer.blank_feature()
      new_feature = self.copy_feature(old_feature)
      new_layer.add_feature(new_feature)

  def createmem(self, name):
    logger.info("creating an in-memory layer %s" % name)
    self._driver = ogr.GetDriverByName('MEMORY')
    self._driver_name = 'MEMORY'
    self._datasource = self._driver.CreateDataSource(name)

  def createf(self, vector_file, overwrite=False):
    logger.info("creating file @ %s" % vector_file)
    self._driver = self.auto_determine_driver(vector_file)
    self._driver_name = self._driver.GetName()
    if overwrite is True:
      if os.path.isfile(vector_file):
        os.remove(vector_file)
      if os.path.isdir(vector_file):
        shutil.rmtree(vector_file)
    self._datasource = driver.CreateDataSource(vector_file)

  def get_driver_name(self):
    return self._driver_name  

  def copy_blank_layer(self, old_vector_layer, new_name, projection_wkt=None):
    logger.info("Copying layer from %s" % old_vector_layer)
    assert self._datasource is not None, "No datasource set. call createf"

    # if projection wkt, use that else use the current layers ref
    if projection_wkt is not None:
      srs = osr.SpatialReference()
      srs.ImportFromWkt(projection_wkt)
    else:
      srs = old_vector_layer._layer.GetSpatialRef()

    geom_type = old_vector_layer._layer.GetGeomType()

    # copy the layer itself and the spatial reference
    old_layer_def = old_vector_layer._layer.GetLayerDefn()
    self._layer = self._datasource.CreateLayer(new_name, srs=srs, geom_type=geom_type)

    # copy the field definitions
    field_defs = [old_layer_def.GetFieldDefn(i) for i in range(old_layer_def.GetFieldCount())]
    for field_def in field_defs:
      self._layer.CreateField(field_def)

    logger.info("Layer copy completed")

  def create_layer_epsg(self, layer_name, shape_type='POINT', proj=4326):
    crs = CRS.from_epsg(proj)
    return self.create_layer(layer_name, shape_type, crs.to_wkt())

  def create_layer(self, layer_name, shape_type='POINT', projection_wkt=None):
    assert self._datasource is not None, "No datasource set. call createf"
    assert shape_type.upper() in SHAPE_TYPES, "Invalid shape type"
    logging.info("creating layer %s" % layer_name)

    if shape_type.upper() == 'POINT':
      use_shape = ogr.wkbPoint
    elif shape_type.upper() == 'LINE':
      use_shape = ogr.wkbLineString
    elif shape_type.upper() == 'POLYGON':
      use_shape = ogr.wkbPolygon
    elif shape_type.upper() == 'MULTIPOLYGON':
      use_shape = ogr.wkbMultiPolygon

    srs = osr.SpatialReference()
    if projection_wkt is None:
      srs.ImportFromEPSG(4326)
      projection_wkt = srs.ExportToWkt()
    else:
      srs.ImportFromWkt(projection_wkt)

    self._layer = self._datasource.CreateLayer(layer_name,
      srs=srs, geom_type=use_shape)
    self.auto_set_projection()

  def add_field_defn(self, field_name, field_type='int'):
    return self.add_field_def(field_name, field_type)

  def add_field_def(self, field_name, field_type='int'):
    for i in range(self._layer.GetLayerDefn().GetFieldCount()):
      field_def = self._layer.GetLayerDefn().GetFieldDefn(i)
      if field_def.GetName() == field_name:
        logger.info("field with name %s already exists" % field_name)
        return
    if field_name == '':
      logger.info("field name cannot be empty")
      return

    if field_type in (int, 'int', 'Integer', 'Integer64', ogr.OFTInteger):
      fd = ogr.FieldDefn(field_name, ogr.OFTInteger)
      fname = 'Integer'
    elif field_type in (float, 'float', 'Real', ogr.OFTReal):
      fd = ogr.FieldDefn(field_name, ogr.OFTReal)
      fname = 'Real'
    elif field_type in (str, 'str', 'String', ogr.OFTString):
      fd = ogr.FieldDefn(field_name, ogr.OFTString)
      fname = 'String'
    else:
      raise ValueError("Invalid field type, must be int, float or str. got %s" % field_type)
    self._fields[field_name] = {'type': fname}
    self._layer.CreateField(fd)

  def get_fields(self):
    return self._fields

  def get_file_path(self):
    return self._file_path

  # memoize - take a layer that is saved on disk
  # and convert it to an in memory layer for faster
  # processing
  def memoize(self):
    if self._driver_name == 'MEMORY':
      raise ValueError("Layer is already in memory")
    mem_layer = VectorLayer()
    mem_layer.createmem(self.get_name())
    mem_layer.copy_blank_layer(self, self.get_name())
    mem_layer.auto_set_projection()
    mem_layer.auto_set_fields()
    for feature in self.get_layer():
      mem_layer.add_feature(feature.Clone())
    return mem_layer

  # materialize - basically the same as saving to file
  # but updates the object so if you do queries against 
  # it, it goes against the layer on disk instead of
  # the layer in memory (can be used to save memory)
  def materialize(self, file_path, overwrite=True):
    self.save_to_file(file_path, overwrite)
    self.loadf(file_path)

  # this will save the layer out to file, which will
  # require opening the and then copying all the features
  def save_to_file(self, file_path, overwrite=True):
    if overwrite is True:
      if os.path.isfile(file_path):
        os.remove(file_path)
      if os.path.isdir(file_path):
        shutil.rmtree(file_path)
    driver = self.auto_determine_driver(file_path)
    logger.info("saving to %s using driver %s" % (file_path, driver.GetName()))
    out_ds = driver.CreateDataSource(file_path)
    out_layer = out_ds.CreateLayer(self._layer.GetName(),
      srs=self._layer.GetSpatialRef(),
      geom_type=self._layer.GetGeomType())
    for i in range(self._layer.GetLayerDefn().GetFieldCount()):
      field_def = self._layer.GetLayerDefn().GetFieldDefn(i)
      field_name = field_def.GetName()
      logger.info("adding field %s" % field_name)
      out_layer.CreateField(field_def)

    save_count = 0
    total_features = self.get_feature_count()
    logger.info("saving %s features to file" % total_features)
    for feature in self.get_layer():
      geom = feature.GetGeometryRef()
      new_feature = ogr.Feature(out_layer.GetLayerDefn())
      new_feature.SetGeometry(geom)
      for i in range(feature.GetFieldCount()):
        field_name = feature.GetFieldDefnRef(i).GetName()
        field_value = feature.GetField(i)
        new_feature.SetField(field_name, field_value)
      new_feature.SetFID(feature.GetFID())
      out_layer.CreateFeature(new_feature)
      save_count += 1
      if save_count % 1000 == 0:
        logger.info(f"saved {save_count}/{total_features} features")

  # figure out which type of file we are dealing with
  # so we can use the right ogr driver to open it
  def auto_determine_driver(self, filename):
    if 'gdb' in filename:
      return ogr.GetDriverByName('OpenFileGDB')
    elif 'gpkg' in filename:
      return ogr.GetDriverByName('GPKG')
    elif 'shp' in filename:
      return ogr.GetDriverByName('ESRI Shapefile')
    elif 'geojson' in filename:
      return ogr.GetDriverByName('GeoJSON')
    elif 'kml' in filename:
      return ogr.GetDriverByName('KML')
    elif 'vrt' in filename:
      return ogr.GetDriverByName('VRT')
    else:
      raise Exception("Unknown vector format for %s" % filename)

  def loadf(self, vector_file, layer_id=0):
    logger.info("opening %s" % vector_file)
    self._driver = self.auto_determine_driver(vector_file)
    self._driver_name = self._driver.GetName()
    self._source = self._driver.Open(vector_file, 0)
    self._file_path = vector_file
    num_layers = self._source.GetLayerCount()
    logger.info("found %s number of layers" % num_layers)
    if type(layer_id) == int:
      self._layer = self._source.GetLayer(layer_id)
    elif type(layer_id) == str:
      logger.info("fetching layer by name = %s" % layer_id)
      for idx in range(self._source.GetLayerCount()):
        candidate_layer = self._source.GetLayerByIndex(idx)
        candidate_layer_name = candidate_layer.GetName()
        if candidate_layer_name == layer_id:
          logger.info("found layer matching = %s" % idx)
          self._layer = self._source.GetLayer(idx)
    self.auto_set_fields()
    assert self._layer is not None, "cannot find layer id = %s" % layer_id
    self.auto_set_projection()

  # this will automatically look at the fields on the layer
  # and set the fields on this object properly
  def auto_set_fields(self):
    layer_defn = self._layer.GetLayerDefn()
    for i in range(layer_defn.GetFieldCount()):
      field_defn = layer_defn.GetFieldDefn(i)
      field_name = field_defn.GetName()
      field_type = field_defn.GetTypeName()
      self._fields[field_name] = {'type': field_type}

  # this will just set the variables on this object based
  # on what the projection is in the layer
  def auto_set_projection(self):
    projection_wkt = self._layer.GetSpatialRef().ExportToWkt()
    self._projection_wkt = projection_wkt
    crs = CRS.from_wkt(projection_wkt)
    self._datum = crs.datum
    self._epsg_code = crs.to_epsg()
    self._proj4_string = crs.to_proj4()

  def get_datum(self):
    return str(self._datum)

  def get_projection_wkt(self):
    return self._projection_wkt

  def get_projection_epsg(self):
    return self._epsg_code

  def get_projection_proj4(self):
    return self._proj4_string

  # applies an arbitrary function to all features
  def apply_to_features(self, func):
    for feature in self.get_layer():
      func(feature)
      self._layer.SetFeature(feature)

  def find_distance_m(self, geom1, geom2):
    if type(geom1) == tuple and len(geom1) == 2:
      (x, y) = geom1
      tmp_g = ogr.Geometry(ogr.wkbPoint)
      tmp_g.AddPoint_2D(x, y)
      geom1 = tmp_g
    if type(geom2) == tuple and len(geom2) == 2:
      (x, y) = geom2
      tmp_g = ogr.Geometry(ogr.wkbPoint)
      tmp_g.AddPoint_2D(x, y)
      geom2 = tmp_g
    transform_func = osr.CoordinateTransformation(epsg4326, epsg3857)
    geom1.Transform(transform_func)
    geom2.Transform(transform_func)
    return geom1.Distance(geom2)

  # for in memory layers, we maintain the spatial index in memory
  # so we can do fast queries
  def build_spatial_index(self):
    if self.get_driver_name() == 'MEMORY' and len(self._geometries) > 0:
      self._spatial_index = STRtree(list(self._geometries.values()))
    return

  # find nearest feature is useful in that it will return the
  # nearest feature, the distance to that feature and the nearest
  # point in that feature
  # note that find nearest feature uses the query_nearest method
  # with the point which only returns 1 thing
  def find_nearest_feature(self, xy, max_distance=None):
    if self.get_driver_name() == 'MEMORY':
      if self._spatial_index is None:
        self.build_spatial_index()
      if type(xy) == tuple and len(xy) == 2:
        point = Point(xy)
      elif type(xy) == ogr.Geometry:
        point = Point(xy.GetX(), xy.GetY())
      params = {'return_distance': True}
      if max_distance is not None:
        params['max_distance'] = max_distance
      (idxs, dists) = self._spatial_index.query_nearest([point], **params)
      dists = dists.tolist()
      if len(dists) > 0:
        dist = dists[0]
        tree_index = idxs.tolist()[1][0]
        feature = self._features[tree_index]
        paired = (feature, dist)
        return paired
      else:
        return (None, None)
    else:
      sorted_records = self.find_nearest_features(xy, max_distance)
      if len(sorted_records) > 0:
        closest = sorted_records[0][0]
        distance = sorted_records[0][1]
        return (closest, distance)
      return (None, None)

  # returns a list of all features and distances in the 
  # native projection 
  # xy = (x, y) or ogr.Geometry
  # n = number of nearest features to return
  # max_distance = max distance to search for
  def find_nearest_features(self, xy, n=1, max_distance=None):
    if self.get_driver_name() == 'MEMORY':
      if self._spatial_index is None:
        self.build_spatial_index()
      if type(xy) == tuple and len(xy) == 2:
        point = Point(xy)
      elif type(xy) == ogr.Geometry:
        point = Point(xy.GetX(), xy.GetY())

      # if max distance is none then determine the maximum
      # diagonal across the unit system this vector has
      # this is the theoretical max distance you can request
      if max_distance is None:
        min_x, max_x, min_y, max_y = self.get_extent().values()
        max_distance = np.sqrt((max_x - min_x)**2 + (max_y - min_y)**2)

      # configure the QUERY, in this case we take the
      # point and continually draw an intersecting circle
      # around it until we hit n items
      hits = {}
      distance = 1
      while len(hits) < n:
        params = {'return_distance': True, 
          'all_matches': True,
          'max_distance': distance}
        buffered_point = point.buffer(distance)
        (idxs, dists) = self._spatial_index.query_nearest([buffered_point], **params)
        dists = dists.tolist()
        if len(dists) > 0:
          for i in range(len(dists)):
            dist = dists[i] # this is zero because we are inside poly
            tree_index = idxs.tolist()[1][i]
  
            # now get the distance between point and feature
            matched_geom = self._geometries[tree_index]
            dist = matched_geom.distance(point)
            hits[tree_index] = (self._features[tree_index], dist)

            if len(hits) >= n:
              return list(hits.values())
        distance *= 2
        if max_distance is not None and distance > max_distance:
          return list(hits.values())
      return list(hits.values())

    else: 
      if type(xy) == tuple and len(xy) == 2:
        (x, y) = xy
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint_2D(x, y)
      elif type(xy) == ogr.Geometry:
        point = xy

      if max_distance is not None:
        bounding_shape = point.Buffer(max_distance)
        self._layer.SetSpatialFilter(bounding_shape)

      dists = [(f, point.Distance(f.GetGeometryRef())) for f in self._layer]
      sorted_records = sorted(dists, key=lambda i: i[1])
      return sorted_records

  # method which will serialize the entire object into something
  # that can be deserialized and reloaded. Features is optional and
  # will be included as geojsons
  def serialize(self, include_features=False):
    payload = {
      'projection_wkt': self.get_projection_wkt(),
      'name': self.get_name(),
      'feature_count': self.get_feature_count(),
      'extent': self.get_extent(),
      'fields': self.get_fields(),
      'storage': {
        'driver': self.get_driver_name(),
        'file_path': self.get_file_path()
      }
    }

    is_memory_layer = self.get_driver_name() == 'MEMORY'

    if include_features is True:
      features = []
      for feature in self.get_layer():
        geom = feature.GetGeometryRef()
        geom_json = geom.ExportToJson()
        feature_json = {
          'geometry': geom_json,
          'fields': {feature.GetFieldDefnRef(i).GetName(): feature.GetField(i) for \
              i in range(feature.GetFieldCount())}
        }
        features.append(feature_json)
      payload['features'] = features
    return json.dumps(payload)
  
  # deserialize will load this into memory
  def deserialize(self, payload):
    payload = json.loads(payload)
    projection_wkt = payload['projection_wkt']
    layer_name = payload['name']
    extent = payload['extent']
    fields = payload['fields']

    self.createmem(layer_name)
    self.create_layer(layer_name, 'POINT', projection_wkt)
    logger.info("loading layer %s" % layer_name)
    field_list = []
    for (field_name, field) in fields.items():
      self.add_field_defn(field_name, field['type'])
      field_list.append(field_name)

    self.auto_set_projection()

    # if we have features in here, then create all the features
    if 'features' in payload:
      for feature in payload['features']:
        geom = ogr.CreateGeometryFromJson(feature['geometry'])
        new_feature = self.blank_feature(geom)
        for field_name in field_list:
          field_value = feature['fields'].get(field_name)
          new_feature.SetField(field_name, field_value)
        self.add_feature(new_feature)

    # if we dont have features then we're probably using a
    # layer that is stored on disk
    else:
      self.loadf(payload['storage']['file_path'])

    return self
