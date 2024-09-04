import unittest
import os
from osgeo import ogr, osr
from wx_logs import VectorLayer

class VectorLayerTestCase(unittest.TestCase):

  def test_layer_has_name(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    self.assertEqual(layer.get_name(), 'test')

  def test_layer_couple_features(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    feature1 = layer.blank_feature()
    feature2 = layer.blank_feature()

    # make a osgeo geom
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(1, 1)
    feature1.SetGeometry(point)
    layer.add_feature(feature1)

    self.assertEqual(layer.get_feature_count(), 1)

    # add another
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(2, 2)
    feature2.SetGeometry(point)
    layer.add_feature(feature2)

    self.assertEqual(layer.get_feature_count(), 2)

  def test_features_reproject_from_4326_to_3857(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint(1, 1)
    feature1 = layer.blank_feature(geom1)
    layer.add_feature(feature1)

    # add another feature
    geom2 = ogr.Geometry(ogr.wkbPoint)
    geom2.AddPoint(2, 2)
    feature2 = layer.blank_feature(geom2)
    layer.add_feature(feature2)
  
    # now reproject to MOLLWEIDE
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_layer = layer.reproject_proj4(MOLLWEIDE)
    
    # make sure we have 2
    self.assertEqual(new_layer.get_feature_count(), 2)

  def test_layer_create_and_save_to_file(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    layer.add_field_defn('name', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint(1, 1)
    feature1 = layer.blank_feature(geom1)
    feature1.SetField('name', 'pokonos')
    layer.add_feature(feature1)
    layer.save_to_file('/tmp/test.gpkg')
    self.assertTrue(os.path.exists('/tmp/test.gpkg'))
    
    # now load the gpkg file and count features
    layer2 = VectorLayer()
    layer2.loadf('/tmp/test.gpkg')
    self.assertEqual(layer2.get_feature_count(), 1)

  def test_layer_write_and_load_geojson_file(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    layer.add_field_defn('name', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint(1, 1)
    feature1 = layer.blank_feature(geom1)
    feature1.SetField('name', 'pokonos')
    layer.add_feature(feature1)

    layer.save_to_file('/tmp/test.geojson')
    self.assertTrue(os.path.exists('/tmp/test.geojson'))

    # load the geojson and count features
    layer2 = VectorLayer()
    layer2.loadf('/tmp/test.geojson')
    self.assertEqual(layer2.get_feature_count(), 1)

    for f in layer2.get_layer():
      feature = f

    self.assertEqual(feature.GetField('name'), 'pokonos')
    self.assertEqual(feature.GetGeometryRef().GetX(), 1)

  def test_loading_from_a_url(self):
    url = 'https://public-images.engineeringdirector.com/dem/wholefoods.gpkg'
    layer = VectorLayer()
    layer.load_url(url)
    self.assertEqual(layer.get_name(), 'wholefoods')
    self.assertEqual(layer.get_datum(), 'World Geodetic System 1984')
    self.assertEqual(layer.get_projection_epsg(), 4326)
    self.assertEqual(layer.get_feature_count(), 476)

  def test_load_from_url_clone_to_memory_object(self):
    url = 'https://public-images.engineeringdirector.com/dem/wholefoods.gpkg'
    layer = VectorLayer()
    layer.load_url(url)
    self.assertEqual(layer.get_name(), 'wholefoods')
    self.assertEqual(layer.get_datum(), 'World Geodetic System 1984')
    self.assertEqual(layer.get_projection_epsg(), 4326)
    self.assertEqual(layer.get_feature_count(), 476)

    # now clone the layer to memory
    layer2 = layer.clone_to_memory(layer)
    self.assertEqual(layer2.get_name(), 'wholefoods')
    self.assertEqual(layer2.get_datum(), 'World Geodetic System 1984')
    self.assertEqual(layer2.get_projection_epsg(), 4326)
    self.assertEqual(layer2.get_feature_count(), 476)

    # delete the original layer now make sure we dont lose features
    del layer
    self.assertEqual(layer2.get_feature_count(), 476)

  def test_spatial_filter_on_some_locations(self):
    url = 'https://public-images.engineeringdirector.com/dem/wholefoods.gpkg'
    layer = VectorLayer()
    layer.load_url(url)
 
    # make a point where chicago is and buffer
    chicago = ogr.Geometry(ogr.wkbPoint)
    chicago.AddPoint(-87.6298, 41.8781)
    buffer = chicago.Buffer(1)

    # now filter the layer and count features
    layer.set_spatial_filter(buffer)
    self.assertEqual(layer.get_feature_count(), 29)

    # nwo reset the filter
    layer.reset_spatial_filter()
    self.assertEqual(layer.get_feature_count(), 476)

  def test_reproject_4326_to_3857(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint(-87.6298, 41.8781)
    layer.add_field_defn('name', ogr.OFTString)

    feature1 = layer.blank_feature(geom1)
    feature1.SetField('name', 'pokonos')
    layer.add_feature(feature1)
    self.assertEqual(layer.get_projection_epsg(), 4326)

    # make sure we have 1 
    self.assertEqual(layer.get_feature_count(), 1)

    # now reproject to another projection
    new_layer = layer.reproject_epsg(3857)
    self.assertEqual(new_layer.get_projection_epsg(), 3857)
    
    # make sure we have 1
    self.assertEqual(new_layer.get_feature_count(), 1)

    # now make sure the point is in EPSG3857
    for f in new_layer.get_layer():
      feature = f
    #feature = new_layer.get_layer()[0]

    # feature shld be -9754904.71, 5142736.87
    self.assertAlmostEqual(feature.GetGeometryRef().GetX(), -9754904.71, places=2)
    self.assertAlmostEqual(feature.GetGeometryRef().GetY(), 5142736.87, places=2)
    self.assertEqual(feature.GetField('name'), 'pokonos')
    self.assertEqual(feature.GetFID(), 1)

  def test_feature_gets_added_properly(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint(1, 1)
    feature1 = layer.blank_feature(geom1)
    added_feature = layer.add_feature(feature1)
    self.assertEqual(layer.get_feature_count(), 1)
    self.assertEqual(geom1.GetX(), feature1.GetGeometryRef().GetX())
    self.assertEqual(geom1.GetY(), feature1.GetGeometryRef().GetY())
    self.assertEqual(geom1.GetX(), added_feature.GetGeometryRef().GetX())
    self.assertEqual(geom1.GetY(), added_feature.GetGeometryRef().GetY())

    # now get the first feature from the layer
    first_feature = layer.get_feature()
    self.assertEqual(first_feature.GetGeometryRef().GetX(), geom1.GetX())
    self.assertEqual(first_feature.GetGeometryRef().GetY(), geom1.GetY())

    # now test the layer extent, which should line up
    (ul, lr) = layer.get_extent()
    self.assertEqual(ul, (1, 1))
    self.assertEqual(lr, (1, 1))

  def test_extent_ul(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint(-1, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint(2, 2)

    self.assertEqual(point1.GetX(), -1)
    self.assertEqual(point1.GetY(), -1)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    self.assertEqual(layer.get_feature_count(), 2)

    (ul, lr) = layer.get_extent()
    self.assertEqual(ul, (-1, 2))
    self.assertEqual(lr, (2, -1))

  def test_apply_arbitrary_function_to_cells(self):
    b = VectorLayer()
    b.createmem('test')
    b.create_layer_epsg('test', 'POINT', 4326)
    b.add_field_defn('name', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint(1, 1)
    feature1 = b.blank_feature(geom1)
    feature1.SetField('name', 'pokonos')
    b.add_feature(feature1)

    # ok now assert the field is set to pokonos
    for f in b.get_layer():
      self.assertEqual(f.GetField('name'), 'pokonos')
    
    # rename the field to pikachu
    def rename(x):
      x.SetField('name', 'pikachu')
    b.apply_to_features(rename)

    # now assert the field is set to pikachu
    for f in b.get_layer():
      self.assertEqual(f.GetField('name'), 'pikachu')
