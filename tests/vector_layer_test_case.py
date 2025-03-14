import unittest
import json
import os
from osgeo import ogr, osr
from wx_logs import VectorLayer

class VectorLayerTestCase(unittest.TestCase):

  def test_layer_has_name(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    self.assertEqual(layer.get_file_path(), None)
    self.assertEqual(layer.get_driver_name(), 'MEMORY')
    self.assertEqual(layer.get_name(), 'test')

  def test_layer_couple_features(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    feature1 = layer.blank_feature()
    feature2 = layer.blank_feature()

    # make a osgeo geom
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint_2D(1, 1)
    feature1.SetGeometry(point)
    layer.add_feature(feature1)

    self.assertEqual(layer.get_feature_count(), 1)

    # add another
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint_2D(2, 2)
    feature2.SetGeometry(point)
    layer.add_feature(feature2)

    self.assertEqual(layer.get_feature_count(), 2)

  def test_features_reproject_from_4326_to_3857(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
    feature1 = layer.blank_feature(geom1)
    layer.add_feature(feature1)

    # add another feature
    geom2 = ogr.Geometry(ogr.wkbPoint)
    geom2.AddPoint_2D(2, 2)
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
    geom1.AddPoint_2D(1, 1)
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
    geom1.AddPoint_2D(1, 1)
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
    self.assertEqual(layer.get_driver_name(), 'GPKG')
    self.assertEqual(layer.get_name(), 'wholefoods')
    self.assertEqual(layer.get_datum(), 'World Geodetic System 1984')
    self.assertEqual(layer.get_projection_epsg(), 4326)
    self.assertEqual(layer.get_feature_count(), 476)

  def test_make_layer_and_materialize_and_confirm_driver(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    layer.add_field_defn('name', ogr.OFTString)
    self.assertEqual(layer.get_driver_name(), 'MEMORY')
    
    # make a feature for chicago
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(-87.6298, 41.8781)
    feature1 = layer.blank_feature(geom1)
    feature1.SetField('name', 'chicago')
    layer.add_feature(feature1)
    self.assertEqual(layer.get_feature_count(), 1)

    # make a second feature for milwaukee
    geom2 = ogr.Geometry(ogr.wkbPoint)
    geom2.AddPoint_2D(-87.9065, 43.0389)
    feature2 = layer.blank_feature(geom2)
    feature2.SetField('name', 'milwaukee')
    layer.add_feature(feature2)
    self.assertEqual(layer.get_feature_count(), 2)

    # now materialize it into a gpkg file
    layer.materialize('/tmp/test.gpkg', True)
    self.assertEqual(layer.get_driver_name(), 'GPKG')
    self.assertEqual(layer.get_file_path(), '/tmp/test.gpkg')

    # now get the one feature
    features = [f for f in layer.get_layer()]
    feature0 = features[0]
    self.assertEqual(feature0.GetField('name'), 'chicago')
    feature1 = features[1]
    self.assertEqual(feature1.GetField('name'), 'milwaukee')
      
    # now delete the test file
    os.remove('/tmp/test.gpkg')

  def test_create_single_file_per_shape(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    layer.add_field_defn('name', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
    feature1 = layer.blank_feature(geom1)
    feature1.SetField('name', 'pokonos')
    layer.add_feature(feature1)

    feature2 = layer.blank_feature(geom1)
    feature2.SetField('name', 'pikachu')
    layer.add_feature(feature2)

    # ok now call the function which will create a new
    # VectorLayer for each file, with each shape in memory
    # so you can independently save them
    vector_layers = list(layer.explode())
    self.assertEqual(len(vector_layers), 2)
    for l in vector_layers:
      self.assertEqual(l.get_feature_count(), 1)
      self.assertEqual(l.get_projection_epsg(), 4326)

  def test_create_file_per_shape_but_some_lines_with_single_points(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'LINE', 4326)

    # make a linestring w one point
    geom1 = ogr.Geometry(ogr.wkbLineString)
    geom1.AddPoint_2D(12, 12)
    feature1 = layer.blank_feature(geom1)
    layer.add_feature(feature1)

    # make a better line
    geom2 = ogr.Geometry(ogr.wkbLineString)
    geom2.AddPoint_2D(2, 2)
    geom2.AddPoint_2D(3, 3)
    geom2.AddPoint_2D(4, 4)
    feature2 = layer.blank_feature(geom2)
    layer.add_feature(feature2)

    # ok now call the function which will create a new
    # VectorLayer for each file, with each shape in memory
    # so you can independently save them
    vector_layers = list(layer.explode())
    self.assertEqual(len(vector_layers), 1)

  def test_shape_type(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'LINE', 4326)
    self.assertEqual(layer.get_shape_type(), ogr.wkbLineString)

  def test_create_single_file_per_shape_but_shapes_are_lines(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'LINE', 4326)
    layer.add_field_defn('name', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbLineString)
    geom1.AddPoint_2D(1, 1)
    geom1.AddPoint_2D(2, 2)
    feature1 = layer.blank_feature(geom1)
    feature1.SetField('name', 'pokonos')
    layer.add_feature(feature1)
    self.assertEqual(layer.get_shape_type(), ogr.wkbLineString)

    geom2 = ogr.Geometry(ogr.wkbLineString)
    geom2.AddPoint_2D(3, 3)
    geom2.AddPoint_2D(4, 4)
    feature2 = layer.blank_feature(geom2)
    feature2.SetField('name', 'pikachu')
    layer.add_feature(feature2)

    # ok now call the function which will create a new
    # VectorLayer for each file, with each shape in memory
    # so you can independently save them
    vector_layers = list(layer.explode())
    self.assertEqual(len(vector_layers), 2)
    for l in vector_layers:
      self.assertEqual(l.get_feature_count(), 1)
      self.assertEqual(l.get_projection_epsg(), 4326)
      self.assertEqual(l.get_shape_type(), ogr.wkbLineString)

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
    chicago.AddPoint_2D(-87.6298, 41.8781)
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
    geom1.AddPoint_2D(-87.6298, 41.8781)
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
    self.assertEqual(feature.GetFID(), 0)

  def test_feature_gets_added_properly(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
    feature1 = layer.blank_feature(geom1)
    added_feature = layer.add_feature(feature1)
    self.assertEqual(layer.get_feature_count(), 1)
    self.assertEqual(geom1.GetX(), feature1.GetGeometryRef().GetX())
    self.assertEqual(geom1.GetY(), feature1.GetGeometryRef().GetY())
    self.assertEqual(geom1.GetX(), added_feature.GetGeometryRef().GetX())
    self.assertEqual(geom1.GetY(), added_feature.GetGeometryRef().GetY())

    # now get the first feature from the layer
    first_feature = layer.get_feature(0)
    self.assertEqual(first_feature.GetGeometryRef().GetX(), geom1.GetX())
    self.assertEqual(first_feature.GetGeometryRef().GetY(), geom1.GetY())

    # now test the layer extent, which should line up
    extent_dict = layer.get_extent()
    ul = (extent_dict['min_x'], extent_dict['max_y'])
    lr = (extent_dict['max_x'], extent_dict['min_y'])
    self.assertEqual(ul, (1, 1))
    self.assertEqual(lr, (1, 1))

  def test_extent_ul(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(-1, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(2, 2)

    self.assertEqual(point1.GetX(), -1)
    self.assertEqual(point1.GetY(), -1)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    self.assertEqual(layer.get_feature_count(), 2)

    extent_dict = layer.get_extent()
    ul = (extent_dict['min_x'], extent_dict['max_y'])
    lr = (extent_dict['max_x'], extent_dict['min_y'])

    self.assertEqual(ul, (-1, 2))
    self.assertEqual(lr, (2, -1))

  def test_find_nearest_features_dont_run_forever(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 3857)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 2)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 3)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    self.assertEqual(layer.get_feature_count(), 3)

    # now find the 5 nearest features (but we only have 3)
    pt = (0, 0)
    distances = layer.find_nearest_features(pt, 5)
    self.assertEqual(len(distances), 3)

    # now find the one nearest feature and make sure its right
    (nearest, dist) = layer.find_nearest_feature(pt)
    self.assertEqual(nearest.GetGeometryRef().GetX(), 0.0)
    self.assertEqual(nearest.GetGeometryRef().GetY(), -1.0)
    self.assertEqual(dist, 1.0)

  def test_find_nearest_features_batch_call(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 3857)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 2)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 3)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    self.assertEqual(layer.get_feature_count(), 3)

    # now find the 5 nearest features of the two points
    pt0 = (0, 0)
    pt1 = (10, 10)
    pts = [pt0, pt1]
    distances = layer.find_nearest_feature_batch(pts, 5)

    # then what i should get back is a list
    # that is the same size that went in
    self.assertEqual(len(pts), len(distances))

    # then each point should have a (feature, distance) pair
    self.assertEqual(len(distances[0]), 2)
    self.assertEqual(len(distances[1]), 2)
    pt0_match = distances[0][0]
    pt0_dist = distances[0][1]
    pt1_match = distances[1][0]
    pt1_dist = distances[1][1]
      
    # the first point should be the first point
    self.assertEqual(pt0_match.GetGeometryRef().GetX(), 0.0)
    self.assertEqual(pt0_match.GetGeometryRef().GetY(), -1.0)
    self.assertEqual(pt0_dist, 1.0)

    # the second point should be the second point
    self.assertEqual(pt1_match, None)
    self.assertEqual(pt1_dist, None)

    # now do again but with no range limit
    distances = layer.find_nearest_feature_batch(pts)
    self.assertEqual(len(distances[0]), 2)
    self.assertEqual(len(distances[1]), 2)

    p0_match = distances[0][0]
    p0_dist = distances[0][1]
    p1_match = distances[1][0]
    p1_dist = distances[1][1]

    # the first point should be the first point
    self.assertEqual(p0_match.GetGeometryRef().GetX(), 0.0)
    self.assertEqual(p0_match.GetGeometryRef().GetY(), -1.0)

    # the second point should be the second point
    self.assertEqual(p1_match.GetGeometryRef().GetX(), 0.0)
    self.assertEqual(p1_match.GetGeometryRef().GetY(), 3.0)

  def test_batch_join_more_points(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 3857)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 2)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 3)
    point4 = ogr.Geometry(ogr.wkbPoint)
    point4.AddPoint_2D(0, 4)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    self.assertEqual(layer.get_feature_count(), 3)

    pt0 = (0, 0)
    pt1 = (10, 10)
    pt2 = (0, 0)
    pts = [pt0, pt1, pt2]
    distances = layer.find_nearest_feature_batch(pts, 5)

    # then what i should get back is a list
    # that is the same size that went in
    self.assertEqual(len(pts), len(distances))

    # then each point should have a (feature, distance) pair
    self.assertEqual(len(distances[0]), 2)
    self.assertEqual(len(distances[1]), 2)
    self.assertEqual(len(distances[2]), 2)

    self.assertEqual(distances[0][0].GetGeometryRef().GetX(), 0.0)
    self.assertEqual(distances[0][0].GetGeometryRef().GetY(), -1.0)

    self.assertEqual(distances[2][0].GetGeometryRef().GetX(), 0.0)
    self.assertEqual(distances[2][0].GetGeometryRef().GetY(), -1.0)


  def test_batch_join_but_make_100_random_points(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 3857)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 2)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 3)
    point4 = ogr.Geometry(ogr.wkbPoint)
    point4.AddPoint_2D(0, 4)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    layer.add_feature(layer.blank_feature(point4))
    self.assertEqual(layer.get_feature_count(), 4)

    # now make 100 random points
    pts = []
    for i in range(100):
      pt = (0, i)
      pts.append(pt)

    # now do search on those 100 pts
    distances = layer.find_nearest_feature_batch(pts)
    self.assertEqual(len(distances), 100)

  def test_find_nearest_features(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 3857)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, -1)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 2)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 3)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    self.assertEqual(layer.get_feature_count(), 3)

    # now find the nearest feature to 0,0
    pt = (0, 0)
    distances = layer.find_nearest_features(pt)
    (nearest, dist) = layer.find_nearest_feature(pt)

    self.assertEqual(nearest.GetGeometryRef().GetX(), 0.0)
    self.assertEqual(nearest.GetGeometryRef().GetY(), -1)
    self.assertEqual(dist, 1.0)

    # now find the distances from all features
    distances = layer.find_nearest_features(pt, 3)
    self.assertEqual(len(distances), 3)
    
    # first object should be distance 1 away
    self.assertEqual(distances[0][1], 1.0)
    self.assertEqual(distances[1][1], 2.0)
    self.assertEqual(distances[2][1], 3.0)

  def test_nearest_feature_with_geom_instead_of_xy(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, 3)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 1)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 2)

    point0 = ogr.Geometry(ogr.wkbPoint)
    point0.AddPoint_2D(0, 0)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    self.assertEqual(layer.get_feature_count(), 3)

    # now find the nearest feature to 0,0
    (nearest, dist) = layer.find_nearest_feature(point0)
    self.assertEqual(nearest.GetGeometryRef().GetX(), 0.0)
    self.assertEqual(nearest.GetGeometryRef().GetY(), 1.0)

  def test_nearest_features_with_spatial_filter_saying_too_far_away(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, 0)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 1)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 2)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    self.assertEqual(layer.get_feature_count(), 3)

    # now find the nearest feature to 0,0
    pt = (10, 10)
    distances = layer.find_nearest_features(pt, 2, 1.0)
    self.assertEqual(len(distances), 0)

    # nearest should return None, None
    (nearest, dist) = layer.find_nearest_feature(pt, 1.0)
    self.assertEqual(nearest, None)
    self.assertEqual(dist, None)

  def test_nearest_feature_with_spherical_projection(self):
    layer = VectorLayer()
    layer.createmem('test')
    layer.create_layer_epsg('test', 'POINT', 4326)
    point1 = ogr.Geometry(ogr.wkbPoint)
    point1.AddPoint_2D(0, 0)
    point2 = ogr.Geometry(ogr.wkbPoint)
    point2.AddPoint_2D(0, 1)
    point3 = ogr.Geometry(ogr.wkbPoint)
    point3.AddPoint_2D(0, 2)

    layer.add_feature(layer.blank_feature(point1))
    layer.add_feature(layer.blank_feature(point2))
    layer.add_feature(layer.blank_feature(point3))
    self.assertEqual(layer.get_feature_count(), 3)

    # now find the nearest feature to 0,0
    (nearest, dist) = layer.find_nearest_feature((41.8781, -87.6298))
    self.assertEqual(nearest.GetGeometryRef().GetX(), 0.0)
    self.assertEqual(nearest.GetGeometryRef().GetY(), 0.0)

  def test_apply_arbitrary_function_to_cells(self):
    b = VectorLayer()
    b.createmem('test')
    b.create_layer_epsg('test', 'POINT', 4326)
    b.add_field_defn('name', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
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

  def test_adding_field_defn_with_bad_type_throws(self):
    b = VectorLayer()
    b.createmem('test')
    b.create_layer_epsg('test', 'POINT', 4326)
    with self.assertRaises(ValueError):
      b.add_field_defn('name', 'badtype')

  # we have a serialize method which will serialize the 
  # definition of the vector layer but leave off any of the
  # non-threadsafe Swig objects. If it's an in-memory layer
  # then we basically serialize the whole feature set
  # as a geojson
  def test_serialize_method(self):
    b = VectorLayer()
    b.createmem('test')
    b.create_layer_epsg('test', 'POINT', 4326)
    b.add_field_defn('something', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
    feature1 = b.blank_feature(geom1)
    feature1.SetField('something', 'pokonos')
    b.add_feature(feature1)

    # test the get_fields method returns
    fields = b.get_fields()
    something_field = fields['something']
    self.assertEqual(something_field['type'], 'String')

    # now serialize the layer
    serialized = b.serialize(True)
    serialized_json = json.loads(serialized)
    self.assertEqual(serialized_json['name'], 'test')

    deserialize = VectorLayer()
    deserialize.deserialize(serialized)
    self.assertEqual(deserialize.get_name(), b.get_name())
    self.assertEqual(deserialize.get_datum(), b.get_datum())
    self.assertEqual(deserialize.get_fields(), b.get_fields())
    self.assertEqual(deserialize.get_projection_epsg(), b.get_projection_epsg())
    self.assertEqual(deserialize.get_feature_count(), b.get_feature_count())

  def test_serialize_file_on_disk_and_reload(self):
    b = VectorLayer()
    b.createmem('test')
    b.create_layer_epsg('test', 'POINT', 4326)
    b.add_field_defn('something', ogr.OFTString)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
    feature1 = b.blank_feature(geom1)
    feature1.SetField('something', 'pokonos')
    b.add_feature(feature1)

    # materialize to disk
    b.materialize('/tmp/test.materialized.gpkg')
    s = b.serialize(False)

    # now deserialize
    deserialize = VectorLayer()
    deserialize.deserialize(s)
    self.assertEqual(deserialize.get_name(), b.get_name())
    self.assertEqual(deserialize.get_datum(), b.get_datum())
    self.assertEqual(deserialize.get_fields(), b.get_fields())
    self.assertEqual(deserialize.get_projection_epsg(), b.get_projection_epsg())
    self.assertEqual(deserialize.get_feature_count(), b.get_feature_count())
    self.assertEqual(deserialize.get_driver_name(), 'GPKG')
    self.assertEqual(deserialize.get_file_path(), b.get_file_path())

    # delete the file
    os.remove('/tmp/test.materialized.gpkg')

  def test_memoize_function_with_moves_hard_file_into_memory(self):
    vector_url = 'https://public-images.engineeringdirector.com/dem/Oregon_State_Boundary_6507293181691922778.zip'
    s = VectorLayer()
    s.load_url(vector_url)
    shape_extents = s.get_extent()
    self.assertEqual(s.get_feature_count(), 1703)
    self.assertEqual(len(s.get_fields()), 4)

    for feature in s.get_layer():
      self.assertEqual(feature.GetField('SUBJ_STATE'), 'OREGON')

    # memoize, move this to a new layer in memory
    s2 = s.memoize()
    self.assertEqual(s2.get_feature_count(), 1703)
    self.assertEqual(s2.get_driver_name(), 'MEMORY')
    self.assertEqual(len(s2.get_fields()), 4)
    for feature in s2.get_layer():
      self.assertEqual(feature.GetField('SUBJ_STATE'), 'OREGON')

    # make sure fields are teh same
    self.assertEqual(s.get_fields(), s2.get_fields())

    # okay now try to memoize the memoize and make sure it throws
    # an exception that you can't do that
    with self.assertRaises(ValueError):
      s2.memoize()
    
    # now try to serialize a memory layer
    serialized = s2.serialize(True)
    serialized_json = json.loads(serialized)
    self.assertEqual(serialized_json['name'], 'Oregon_State_Boundary')
    self.assertEqual(len(serialized_json['features']), 1703)

    s3 = VectorLayer()
    s3.deserialize(serialized)
    self.assertEqual(s3.get_feature_count(), 1703)
    self.assertEqual(s3.get_driver_name(), 'MEMORY')
    self.assertEqual(len(s3.get_fields()), 4)

    # compare fields
    self.assertEqual(s.get_fields(), s3.get_fields())

    # look at one of the features
    for feature in s3.get_layer():
      self.assertEqual(feature.GetField('SUBJ_STATE'), 'OREGON')
  
  def test_add_field_and_use_function_to_set_all_values_to_one(self):
    b = VectorLayer()
    b.createmem('test')
    b.create_layer_epsg('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
    feature1 = b.blank_feature(geom1)
    b.add_feature(feature1)

    # add a field and set all values to 1
    b.add_field_defn('v', 'int')
    def set_value_to_one(x):
      x.SetField('v', 1)
    b.apply_to_features(set_value_to_one)

    # now assert the field is set to 1
    for f in b.get_layer():
      self.assertEqual(f.GetField('v'), 1)

  def test_add_memory_layer_make_sure_features_in_features(self):
    b = VectorLayer()
    b.createmem('test')
    b.create_layer_epsg('test', 'POINT', 4326)
    geom1 = ogr.Geometry(ogr.wkbPoint)
    geom1.AddPoint_2D(1, 1)
    feature1 = b.blank_feature(geom1)
    b.add_feature(feature1)
    self.assertEqual(len(b._features), 1)
    self.assertEqual(b.get_feature_count(), 1)
    self.assertEqual(len(b.get_layer()), 1)
    self.assertEqual(len(b.get_extent()), 4)
    self.assertEqual(b.get_driver_name(), 'MEMORY')
    self.assertEqual(len(b._geometries), 1)
  
  def test_shapefile_that_is_simple_but_gdb(self):
    vector_url = 'https://public-images.engineeringdirector.com/dem/Oregon_State_Boundary_6507293181691922778.zip'
    s = VectorLayer()
    s.load_url(vector_url)
    shape_extents = s.get_extent()

    self.assertEqual(s.get_feature_count(), 1703)
    self.assertEqual(shape_extents['min_x'], -124.7038190439999426)
    self.assertEqual(shape_extents['max_x'], -116.4630390559999569)
    self.assertEqual(shape_extents['min_y'], 41.9920871570000713)
    self.assertEqual(shape_extents['max_y'], 46.2923973030000298)
