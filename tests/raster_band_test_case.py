import unittest
import os
from osgeo import ogr, osr
import numpy as np
import numpy.testing as npt
from wx_logs import RasterBand
from wx_logs import VectorLayer

class RasterBandTestCase(unittest.TestCase):

  def test_RasterBand(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    self.assertEqual(b.band_count(), 1)

  def test_file_does_not_exist(self):
    b = RasterBand()
    self.assertRaises(ValueError, b.load_url,
      'https://public-images.engineeringdirector.com/dem/snowfall.2017bad.tif')

  def test_loading_band_not_there(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    self.assertEqual(b.band_count(), 1)
    self.assertRaises(ValueError, b.load_band, 2)

  def test_loading_raster_with_good_values(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.shape(), (1500, 850))
    self.assertEqual(b.values().shape, (850, 1500)) # numpy shape is rows, cols

  def test_load_raster_with_dem_data(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection_epsg(), 4326)
    self.assertEqual(b.get_nodata(), -9999)
    extent = b.get_extent()
    self.assertAlmostEqual(extent['min_x'], -180.0001389, places=4)
    self.assertAlmostEqual(extent['min_y'], -82.9998611, places=4)
    self.assertAlmostEqual(extent['max_x'], 179.9998611, places=4)
    self.assertAlmostEqual(extent['max_y'], 83.0001389, places=4)
    self.assertAlmostEqual(b.percentage_nodata(), 1.0 - 0.3834, places=2)

  def test_load_raster_with_dem_data_and_project_to_mollweide(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    b.set_nodata(-9999)
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_b = b.reproject_proj4(MOLLWEIDE, 3600, 1660)
    self.assertEqual(new_b.get_projection_epsg(), None)
    self.assertEqual(new_b.get_projection_proj4(), MOLLWEIDE)
    self.assertEqual(new_b.shape(), (3600, 1660))

  def test_load_Raster_with_dem_do_pgradient_and_write(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    b.set_nodata(-9999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (3600, 1660))

    # and now load this into its own shape and save to file
    b2 = RasterBand()
    b2 = b.clone_with_new_data(gx)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (3600, 1660))
    b2.write_to_file('/tmp/test_pgradient.tif', True, True)

    # now do the same with y
    b3 = RasterBand()
    b3 = b.clone_with_new_data(gy)
    self.assertEqual(b3.band_count(), 1)
    self.assertEqual(b3.shape(), (3600, 1660))
    b3.write_to_file('/tmp/test_pgradient_y.tif', True, True)

    # load in Y and confirm shape and nodata
    b4 = RasterBand()
    b4.loadf('/tmp/test_pgradient_y.tif')
    b4.set_band(1)
    self.assertEqual(b4.shape(), (3600, 1660))
    self.assertEqual(b4.get_nodata(), -9999)

  def test_rows_function_which_returns_rows_in_yields(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    b.set_nodata(-9999)
    all_rows = list(b.rows())
    self.assertEqual(len(all_rows), 1660)
    #for row in b.rows():
    #  self.assertEqual(len(row), 3600)

  def test_rows_function_make_sure_nodata_come_back_as_nan(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.load_array([[-99.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    rows = list(b.rows())
    self.assertEqual(len(rows), 3)

    row0 = rows[0]
    self.assertEqual(len(row0), 3)
    (corner, value) = row0[0]
    self.assertTrue(np.isnan(value))
    self.assertEqual(corner, (-180.0, 90.0))

    (corner, value) = row0[1]
    self.assertEqual(value, 2.0)
    self.assertEqual(corner, (-60.0, 90.0))
    
    (corner, value) = row0[2]
    self.assertEqual(value, 3.0)
    self.assertEqual(corner, (60.0, 90.0))

  def test_rows_function_but_get_centroids_this_time(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.load_array([[-99.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    rows = list(b.rows(True))
    self.assertEqual(len(rows), 3)

    row0 = rows[0]
    self.assertEqual(len(row0), 3)
    (corner, value) = row0[0]
    self.assertTrue(np.isnan(value))
    self.assertEqual(corner, (-120.0, 60.0))

    (corner, value) = row0[1]
    self.assertEqual(value, 2.0)
    self.assertEqual(corner, (0.0, 60.0))
    
    (corner, value) = row0[2]
    self.assertEqual(value, 3.0)
    self.assertEqual(corner, (120.0, 60.0))

  def test_load_snow_raster_view_metadata(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection_epsg(), 4326)
    metadata = b.get_metadata()
    self.assertEqual(metadata['TIFFTAG_XRESOLUTION'], '100')
    self.assertEqual(metadata['TIFFTAG_YRESOLUTION'], '100')

  def test_loading_from_array_with_rectangle_shape(self):
    arr = [[1, 2, 3, 3], [1, 4, 5, 6], [12, 7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    self.assertEqual(b.shape(), (4, 3))
    self.assertEqual(b.values().shape, (3, 4))

  def test_array_of_ints_save_to_file_as_uint8(self):
    arr = [[1, 2, 3, 3], [1, 4, 5, 6], [12, 7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    b.set_nodata(0)
    b.set_projection_epsg(4326)
    b.write_to_file('/tmp/test_array_ints.tif', True, True, 'uint8')

  def test_get_coordinate_arrays(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    (lons, lats) = b.get_coordinate_arrays()
    self.assertEqual(lons[0], -180.0)
    self.assertEqual(lons[1], -60.0)
    self.assertEqual(lons[2], 60.0)
    self.assertEqual(lats[0], 90.0)
    self.assertEqual(lats[1], 30.0)
    self.assertEqual(lats[2], -30.0)

    # now do centroids
    (lons, lats) = b.get_coordinate_arrays(True)
    self.assertEqual(lons[0], -120.0)
    self.assertEqual(lons[1], 0.0)
    self.assertEqual(lons[2], 120.0)
    self.assertEqual(lats[0], 60.0)
    self.assertEqual(lats[1], 0.0)
    self.assertEqual(lats[2], -60.0)

  def test_flatten_function(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    flat = b.flatten()
    self.assertEqual(flat[0], 1.0)
    self.assertEqual(flat[1], 2.0)
    self.assertEqual(flat[2], 3.0)
    self.assertEqual(len(flat), 9)
    self.assertEqual(flat.shape, (9,))
    self.assertEqual(flat.ndim, 1)

  def test_make_perioidic_gradients_from_snow_map(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (1500, 850))
    self.assertEqual(b.values().shape, (850, 1500)) # opposite bc it calls values() which is rows, cols
    self.assertEqual(gx.shape, (850, 1500)) # opposite bc it calls values() which is rows, cols
    self.assertEqual(gy.shape, (850, 1500)) # opposite bc it calls values() which is rows, cols
  
    # and now load this into its own shape and save to file
    b2 = RasterBand()
    b2.blank_raster(850, 1500, (1,1), (1,1))
    b2.load_array(gx, -99999)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (1500, 850))
    self.assertAlmostEqual(b2.sum(), 2*5020.1255, places=4)

  def test_raster_get_grid_value_at_position(self):
    b = RasterBand()
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    self.assertEqual(b.get_grid_value(1, 1), 5.0)

  def test_apply_arbitrary_function_to_cells_with_nodata(self):
    b = RasterBand()
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, -99.0], [7.0, 8.0, 9.0]], -99.0)
    b.apply_function(lambda x: x * 2)
    expected_values = [[2.0, 4.0, 6.0], [8.0, 10.0, np.nan], [14.0, 16.0, 18.0]]
    self.assertTrue(np.isnan(b.get_grid_value(1,2))) 

  def test_make_raster_in_4326_and_get_point(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    self.assertEqual(b.get_projection_epsg(), 4326)
    self.assertEqual(b.get_nodata(), -99.0)
    self.assertEqual(b.get_value(-176.0, 75.0), 1.0)
    self.assertEqual(b.get_value(178.0, -75.0), 9.0)
    self.assertEqual(b.get_value(0.0, 0.0), None)

  def test_reproject_map_with_no_projection_throws(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    self.assertRaises(ValueError, b.reproject, 3857)

  def test_extent_from_an_epsg_code(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)

    # get_extent_from_epsg
    extent = b.get_bounds_from_epsg(4326)
    self.assertEqual(extent, (-180.0, -90.0, 180, 90.0))
    extent_3857 = b.get_bounds_from_epsg(3857)
    self.assertEqual(extent_3857, (-180.0, -85.06, 180.0, 85.06))

  def test_get_extent_for_data(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    extent = b.get_extent()
    self.assertEqual(extent['min_x'], -180.0)
    self.assertEqual(extent['min_y'], -90.0)
    self.assertEqual(extent['max_x'], 180.0)
    self.assertEqual(extent['max_y'], 90.0)

  def test_save_to_file(self):
    r = RasterBand()
    r.blank_raster(3, 3, (1, 1), (1, 1))
    r.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    out_filepath = '/tmp/test.tif'
    r.set_projection_epsg(4326)
    r.save_to_file(out_filepath)
    self.assertTrue(os.path.exists(out_filepath))
    #cleanup file
    #os.remove(out_filepath)

  def test_save_to_file_compress_and_overwrite(self):
    r = RasterBand()
    r.blank_raster(3, 3, (1, 1), (1, 1))
    r.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    out_filepath = '/tmp/test_compressed.tif'
    r.set_projection_epsg(4326)
    r.save_to_file(out_filepath, True, True)
    self.assertTrue(os.path.exists(out_filepath))
    #os.remove(out_filepath)

  # we need to be able to split a raster into smaller chunks
  # and then write those chunks out to file
  def test_split_raster_into_even_sized_chunks(self):
    r = RasterBand()
    r.blank_raster(4, 4, (2, 2), (-4, 4))
    r.set_projection_epsg(4326)
    r.load_array([[1.0, 2.0, 3.0, 10.0], 
      [14.0, 11.0, 4.0, 5.0], 
      [15.0, 16.0, 17.0, 18.0],  
      [12.0, 7.0, 8.0, 9.0]])
    chunks = list(r.chunk_fixed_size(2, 2))
    self.assertEqual(len(chunks), 4)
  
    # confirm the extent
    extent = r.get_extent()
    self.assertEqual(extent['min_x'], -4)
    self.assertEqual(extent['min_y'], -4)
    self.assertEqual(extent['max_x'], 4)
    self.assertEqual(extent['max_y'], 4)

    for i, chunk in enumerate(chunks):
      self.assertEqual(chunk.shape(), (2, 2))
      self.assertEqual(chunk.get_projection_epsg(), 4326)

    chunk0 = chunks[0]
    extent = chunk0.get_extent()
    self.assertEqual(extent['min_x'], -4)
    self.assertEqual(extent['min_y'], 0)
    self.assertEqual(extent['max_x'], 0)
    self.assertEqual(extent['max_y'], 4)

    # confiurm chunk 1 has right extent
    chunk1 = chunks[1]
    extent = chunk1.get_extent()
    self.assertEqual(extent['min_x'], 0)
    self.assertEqual(extent['min_y'], 0)
    self.assertEqual(extent['max_x'], 4)
    self.assertEqual(extent['max_y'], 4)
 
  # note that what the overlap will do is potentially pull
  # in chunks from other chunks and adjust it slightly
  def test_chunking_but_with_1_box_overlap_reflection(self):
    r = RasterBand()
    r.blank_raster(4, 4, (2, 2), (-4, 4))
    r.set_projection_epsg(4326)
    r.load_array([[1.0, 2.0, 3.0, 10.0], 
      [14.0, 11.0, 4.0, 5.0], 
      [15.0, 16.0, 17.0, 18.0],  
      [12.0, 7.0, 8.0, 9.0]])
    chunks_with_border = list(r.chunk_fixed_size(3, 3, 1, 1))
    chunk0 = chunks_with_border[0]
    self.assertEqual(chunk0.shape(), (5, 5))
    self.assertEqual(chunk0.get_projection_epsg(), 4326)

    # chunk 1 should be 3x5 since its the right col
    chunk1 = chunks_with_border[1]
    self.assertEqual(chunk1.shape(), (3, 5))

    row0 = chunks_with_border[0].values()[0]
    col0 = chunks_with_border[0].values()[:,0]
    self.assertEqual(np.isnan(row0[0]), True)
    self.assertEqual(np.isnan(col0[0]), True)

    row1 = chunks_with_border[0].values()[1]
    col1 = chunks_with_border[0].values()[:,1]
    self.assertEqual(np.isnan(row1[0]), True)
    self.assertEqual(row1[1], 1.0)
    self.assertEqual(row1[2], 2.0)
    self.assertEqual(row1[3], 3.0)
    self.assertEqual(row1[4], 10.0)

  def test_chunking_with_padding_and_reflect(self):
    r = RasterBand()
    r.blank_raster(4, 4, (2, 2), (-4, 4))
    r.set_projection_epsg(4326)
    r.load_array([[1.0, 2.0, 3.0, 10.0], 
      [14.0, 11.0, 4.0, 5.0], 
      [15.0, 16.0, 17.0, 18.0],  
      [12.0, 7.0, 8.0, 9.0]])
    chunks_with_border = list(r.chunk_fixed_size(3, 3, 1, 1, 'reflect'))
    chunk0 = chunks_with_border[0]
    self.assertEqual(chunk0.shape(), (5, 5))
    self.assertEqual(chunk0.get_projection_epsg(), 4326)

    row1 = chunks_with_border[0].values()[1]
    col0 = chunks_with_border[0].values()[:,0]
    self.assertEqual(row1.tolist(), [2.0, 1.0, 2.0, 3.0, 10.0])
    self.assertEqual(col0.tolist(), [11.0, 2.0, 11.0, 16.0, 7.0]) # this is reflected

  def test_try_chunking_real_file_with_padding(self):
    r = RasterBand()
    r.load_url('https://public-images.engineeringdirector.com/dem/resized_10km.tif')
    r.load_band(1)

    # Size is 4008, 3870
    # confirm sizes
    self.assertEqual(r.width(), 4008)
    self.assertEqual(r.height(), 3870)
    self.assertEqual(r.get_nodata(), 127)
    self.assertEqual(r.get_projection_epsg(), 3857)
    self.assertEqual(r.sum(), 6653376128)

    chunks = list(r.chunk_fixed_size(1000, 1000, 100, 100, 'reflect'))
    self.assertEqual(len(chunks), 20)

    chunk0 = chunks[0]
    self.assertEqual(chunk0.shape(), (1200, 1200))
    self.assertEqual(chunk0.get_projection_epsg(), 3857)
    self.assertEqual(chunk0.get_nodata(), 127)

    # so chunk be 208x1200
    # normall 8 but padding by 200
    chunk4 = chunks[4]
    self.assertEqual(chunk4.shape(), (208, 1200))

  # public-images.engineeringdirector.com/dem/resized_10km.tif
  def test_try_chunking_on_a_real_file(self):
    r = RasterBand()
    r.load_url('https://public-images.engineeringdirector.com/dem/resized_10km.tif')
    r.load_band(1)

    # Size is 4008, 3870
    # confirm sizes
    self.assertEqual(r.width(), 4008)
    self.assertEqual(r.height(), 3870)
    self.assertEqual(r.get_nodata(), 127)
    self.assertEqual(r.get_projection_epsg(), 3857)
    self.assertEqual(r.sum(), 6653376128)

    # ok so on a 4008,3870 file, there should be 
    # 3 rows of 1000x1000
    # 4 cols of 1000x1000
    # the rightmost column will have width of 8
    # the bottommost row will have height of 870
    # so thats 4x5 = 20
    chunks = list(r.chunk_fixed_size(1000, 1000))
    self.assertEqual(len(chunks), 20)

    # chunk0 should be 1000x1000
    chunk0 = chunks[0]
    self.assertEqual(chunk0.shape(), (1000, 1000))
    self.assertEqual(chunk0.get_projection_epsg(), 3857)
    self.assertEqual(chunk0.get_nodata(), 127)

    # chunk3 should be 1000x870
    chunk3 = chunks[4]
    self.assertEqual(chunk3.shape(), (8, 1000))

    # chunk19 should be 
    chunk19 = chunks[19]
    self.assertEqual(chunk19.shape(), (8, 870))
    self.assertEqual(chunk19.get_projection_epsg(), 3857)
    self.assertEqual(chunk19.get_nodata(), 127)


  def test_save_to_file_and_load_from_file_check_upper_left(self):
    r = RasterBand()
    r.blank_raster(4, 4, (2, 2), (-4, 4))
    r.load_array([[1.0, 2.0, 3.0, 10.0], 
      [14.0, 11.0, 4.0, 5.0], 
      [15.0, 16.0, 17.0, 18.0],  
      [12.0, 7.0, 8.0, 9.0]])

    # test extents
    extent = r.get_extent()
    bbox = r.get_bbox()
    self.assertEqual((extent['min_x'], extent['max_y']), bbox[0])
    self.assertEqual((extent['max_x'], extent['min_y']), bbox[1])
    self.assertEqual(bbox[0], (-4, 4))
    self.assertEqual(bbox[1], (4, -4))

    # nwo write to file and reload it backin
    out_filepath = '/tmp/test_load_from_file.tif'
    r.set_projection_epsg(4326)
    r.save_to_file(out_filepath)

    self.assertTrue(os.path.exists(out_filepath))
    r2 = RasterBand()
    r2.loadf(out_filepath)
    r2.set_band(1)
    self.assertEqual(r2.width(), r.width())
    self.assertEqual(r2.height(), r.height())
    self.assertEqual(r2.get_projection_epsg(), 4326)
    npt.assert_array_equal(r.values(), r2.values())
    values_shp = r.values().shape
    values_shp2 = r2.values().shape
    self.assertEqual(values_shp, (4, 4))
    self.assertEqual(r.get_value(0,0), r2.get_value(0, 0))
    self.assertEqual(r.get_value(3.5, 3.5), 10.0)

  def test_simple_4326_to_3857_reprojection_small_area(self):
    b = RasterBand()
    b.blank_raster(3, 3, (2, 2), (-3, 3))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, -99.0, 6.0], [7.0, 8.0, 9.0]], -99.0)
    new_b = b.reproject_epsg(3857)
    self.assertEqual(new_b.get_projection_epsg(), 3857)
    self.assertEqual(new_b.get_value(0.0, 0.0), None) # dead middle is no data

    # test this by comparing to the actual points projected
    pt = ogr.Geometry(ogr.wkbPoint)
    pt.AddPoint(-3.0, 3.0)
    old_srs = osr.SpatialReference()
    old_srs.ImportFromEPSG(4326)
    old_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    to_srs = osr.SpatialReference()
    to_srs.ImportFromEPSG(3857)
    pt.Transform(osr.CoordinateTransformation(old_srs, to_srs))
    self.assertEqual(pt.GetX(), new_b.get_extent()['min_x'])
    self.assertEqual(pt.GetY(), new_b.get_extent()['max_y'])

  def test_reproject_real_map_from_3857_to_4326(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017_3857.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    new_b = b.reproject_epsg(4326)
    self.assertEqual(new_b.get_projection_epsg(), 4326)

  def test_real_raster_and_test_datum(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017_3857.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection_epsg(), 3857)
    self.assertEqual(b.get_datum(), 'World Geodetic System 1984')

  def test_clip_gdem_raster_to_north_america(self):
    north_america_ul = (-169.0, 84.0)
    north_america_lr = (-52.0, 24.0)
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection_epsg(), 4326)

    # now clip this to north america
    new_b = b.clip_to_extent(north_america_ul, north_america_lr)
    self.assertEqual(new_b.get_projection_epsg(), 4326)
    new_extent = new_b.get_extent()

    # these should be close enough due to clipping
    self.assertAlmostEqual(new_extent['max_x'], north_america_lr[0], places=1)
    self.assertAlmostEqual(new_extent['max_y'], north_america_ul[1], places=1)

  def test_raster_band_adding_one_row_at_a_time(self):
    row1 = [1, 2, 3]
    row2 = [4, 5, 6]
    row3 = [7, 8, 9]

    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (-1, 1))
    b.load_band(1, False) # not cached
    b.add_row(0, row1)
    b.add_row(1, row2)
    b.add_row(2, row3)

    self.assertEqual(b.get_projection_epsg(), None)
    self.assertEqual(b.sum(), 45)
    self.assertEqual(b.get_value(0, 0), 5)

  def test_raster_band_adding_one_row_at_a_time_with_caching_on(self):
    row1 = [1, 2, 3]
    row2 = [4, 5, 6]
    row3 = [7, 8, 9]

    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (-1, 1))
    b.load_band(1, True)
    b.add_row(0, row1)
    b.add_row(1, row2)
    b.add_row(2, row3)

    self.assertEqual(b.get_projection_epsg(), None)
    self.assertEqual(b.sum(), 45)
    self.assertEqual(b.get_value(0, 0), 5)

  def test_clip_map_to_a_specific_shapefile_extent(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)

    s = VectorLayer()
    s.load_url('https://public-images.engineeringdirector.com/dem/illinois.boundaries.gpkg')
    self.assertEqual(s.get_projection_epsg(), 4326)
    self.assertEqual(s.get_datum(), 'World Geodetic System 1984')
    self.assertEqual(s.get_feature_count(), 1)
    shape_extent = s.get_extent()

    # now clip the raster to the shapefile
    new_b = b.clip_to_vector_layer_extent(s)

    # confirm the extents line up
    extent = new_b.get_extent()
    self.assertAlmostEqual(extent['min_x'], shape_extent['min_x'], places=1)
    self.assertAlmostEqual(extent['min_y'], shape_extent['min_y'], places=1)
    self.assertAlmostEqual(extent['max_x'], shape_extent['max_x'], places=1)
    self.assertAlmostEqual(extent['max_y'], shape_extent['max_y'], places=1)

  def test_clipping_to_map_with_different_projection_throws_exception(self):
    vector_url = 'https://public-images.engineeringdirector.com/dem/illinois.boundaries.3857.gpkg'
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    
    s = VectorLayer()
    s.load_url(vector_url)

    # this should throw an exception
    self.assertRaises(ValueError, b.clip_to_vector_layer_extent, s)

  def test_clip_to_another_shapefile_gdb(self):
    vector_url = 'https://public-images.engineeringdirector.com/dem/Oregon_State_Boundary_6507293181691922778.zip'

    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)

    s = VectorLayer()
    s.load_url(vector_url)
    shape_extents = s.get_extent()

    # now clip the raster to the shapefile
    new_b = b.clip_to_vector_layer_extent(s)

    # confirm the extents line up, mostly
    extent = new_b.get_extent()
    self.assertAlmostEqual(extent['min_x'], shape_extents['min_x'], places=1)
    self.assertAlmostEqual(extent['min_y'], shape_extents['min_y'], places=1)
    self.assertAlmostEqual(extent['max_x'], shape_extents['max_x'], places=1)
    self.assertAlmostEqual(extent['max_y'], shape_extents['max_y'], places=1)

    # write this to a temp file
    new_b.write_to_file('/tmp/test_clip_to_oregon.tif', True, True)

  def test_clip_a_real_map_to_new_extent(self):
    illinois_ul = (-91.5131, 42.4951)
    illinois_lr = (-87.0199, 36.9869)
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection_epsg(), 4326)

    # now clip this to illinois
    new_b = b.clip_to_extent(illinois_ul, illinois_lr)
    self.assertEqual(new_b.get_projection_epsg(), 4326)
    new_extent = new_b.get_extent()

    # these should be close enough due to clipping
    self.assertAlmostEqual(new_extent['min_x'], illinois_ul[0], places=1)
    self.assertAlmostEqual(new_extent['min_y'], illinois_lr[1], places=1)
    self.assertAlmostEqual(new_extent['max_x'], illinois_lr[0], places=1)
    self.assertAlmostEqual(new_extent['max_y'], illinois_ul[1], places=1)

    # now save it to file
    new_b.write_to_file('/tmp/test_clip_to_illinois.tif', True, True)

  def test_reproject_mollweide_function(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, 9.0, 6.0], [7.0, 8.0, -99.0]], -99.0)
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_b = b.reproject_mollweide()
    self.assertEqual(new_b.get_projection_epsg(), None)
    self.assertEqual(new_b.get_projection_proj4(), MOLLWEIDE)
    self.assertEqual(new_b.get_value(0.0, 0.0), 9.0)

  def test_clip_to_extent_throws_exception_if_ul_is_not_ul_of_lr(self):
    b = RasterBand()
    b.blank_raster(3, 3, (360/3, 180/3), (-180,90))
    b.set_projection_epsg(4326)
    b.load_array([[1.0, 2.0, 3.0], [4.0, 9.0, 6.0], [7.0, 8.0, -99.0]], -99.0)
    self.assertRaises(ValueError, b.clip_to_extent, (180, 90), (-180, -90))

  def test_reproject_real_map_from_4325_to_mollweide(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_b = b.reproject_proj4(MOLLWEIDE)
    self.assertEqual(new_b.get_projection_epsg(), None)
    self.assertEqual(new_b.get_projection_proj4(), MOLLWEIDE)

  def test_reproject_map_to_mollweide_and_calculate_gradients(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    extent = b.get_extent()
    b.set_nodata(-99999)
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_b = b.reproject_proj4(MOLLWEIDE)
    self.assertEqual(new_b.get_projection_epsg(), None)
    self.assertEqual(new_b.get_projection_proj4(), MOLLWEIDE)
    (gx, gy) = new_b.central_diff_gradients()

    # this new map is in mollweide so will have a different width and height
    self.assertEqual(new_b.shape(), (2784, 1428))
    new_b.write_to_file('/tmp/test_mollweide.tif', True, True)

    # now load from the file
    b2 = RasterBand()
    b2.loadf('/tmp/test_mollweide.tif')
    b2.set_band(1)

    # reproject back to 4326 and check size
    new_b2 = b2.reproject_epsg(4326, 1500, 850)
    self.assertEqual(new_b2.get_projection_epsg(), 4326)
    self.assertEqual(new_b2.shape(), (1500, 850))
    
    # check extents match (note they wont match, looks like it gets clipped)
    #extent2 = new_b2.get_extent()
    #self.assertAlmostEqual(extent['min_x'], extent2['min_x'], places=4)
    #self.assertAlmostEqual(extent['min_y'], extent2['min_y'], places=4)
    #self.assertAlmostEqual(extent['max_x'], extent2['max_x'], places=4)
    #self.assertAlmostEqual(extent['max_y'], extent2['max_y'], places=4)

    # now write this out
    new_b2.write_to_file('/tmp/test_mollweide_back_to_4326_2.tif', True, True)

  def test_load_file_and_reproject_to_mollweide_and_save_as_moll(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_b = b.reproject_proj4(MOLLWEIDE)
    self.assertEqual(new_b.get_projection_epsg(), None)
    self.assertEqual(new_b.get_projection_proj4(), MOLLWEIDE)
    new_b.write_to_file('/tmp/test_mollweide_proj.tif', True, True)

    # now load from the file and confirm its still MOLLWEIDE
    b2 = RasterBand()
    b2.loadf('/tmp/test_mollweide_proj.tif')
    b2.set_band(1)
    self.assertEqual(b2.get_projection_epsg(), None)
    self.assertEqual(b2.get_projection_proj4(), MOLLWEIDE)
    self.assertEqual(b2.shape(), (2784, 1428))

  def test_reproject_real_map_from_4326_to_3857(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    new_b = b.reproject_epsg(3857)
    self.assertEqual(new_b.get_projection_epsg(), 3857)

  def test_apply_arbitrary_function_to_cells(self):
    b = RasterBand()
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    b.apply_function(lambda x: x * 2)
    expected_values = [[2.0, 4.0, 6.0], [8.0, 10.0, 12.0], [14.0, 16.0, 18.0]]
    npt.assert_array_equal(b.values(), expected_values)

  def test_central_diff_gradients_back_to_raster(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (1500, 850))

    # now make a new raster with this as the array input
    b2 = RasterBand()
    b2.blank_raster(850, 1500, (1,1), (1,1))
    b2.load_array(gx, -99999)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (1500, 850)) # same widths

  def test_rasterband_clone_method_to_make_a_new_one(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    (gx, gy) = b.central_diff_gradients()
    self.assertEqual(b.shape(), (1500, 850))

    # now make a new raster with this as the array input
    b2 = b.clone_with_new_data(gx)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (1500, 850))
    self.assertEqual(b2.get_projection_epsg(), 4326)

  def test_rasterband_projection(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.get_projection_epsg(), 4326)

  def test_raster_from_numpy_array(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    self.assertEqual(b.band_count(), 1)

  def test_raster_from_numpy_array_with_nodata(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.load_array(arr, -99)
    self.assertEqual(b.band_count(), 1)
    self.assertEqual(b.get_nodata(), -99)

  def test_central_diff_gradients(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    grad_y = np.array([[-3.0, -3.0, -3.0],
      [6, 6, 6],
      [-3, -3, -3]])
    grad_x = np.array([[-1.0,  2.0, -1.0],
      [-1.0, 2.0, -1.0],
      [-1.0, 2.0, -1.0]])
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.array_equal(gx, grad_x), "X gradients do not match")
    self.assertTrue(np.array_equal(gy, grad_y), "Y gradients do not match")

  def test_central_diff_gradients_with_nodata(self):
    arr = [[1, 2, 3], [4, -99, 6], [7, 8, 9]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.load_array(arr, -99.0)
    self.assertEqual(b.get_projection_epsg(), None)
    grad_y = np.array([[-3.0, np.nan, -3.0],
      [6.0, 6.0, 6.0],
      [-3.0, np.nan, -3.0]])
    grad_x = np.array([[-1.0,  2.0, -1.0],
      [np.nan, 2.0, np.nan],
      [-1.0, 2.0, -1.0]])
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.allclose(gx, grad_x, equal_nan=True),
      "X gradients do not match")
    self.assertTrue(np.allclose(gy, grad_y, equal_nan=True), 
      "Y gradients do not match")

  def test_central_diff_grads_with_nodata_on_edge(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, -99.0]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.load_array(arr, -99.0)
    grad_y = np.array([[-3, -3, np.nan],
      [6.0, 6.0, np.nan],
      [-3.0, -3.0, -3.0]])
    grad_x = np.array([[-1.0, 2.0, -1.0],
      [-1.0, 2.0, -1.0],
      [np.nan, np.nan, -1.0]])
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.allclose(gx, grad_x, equal_nan=True), "X gradients do not match")
    self.assertTrue(np.allclose(gy, grad_y, equal_nan=True), "Y gradients do not match")

  def test_raster_projects_with_correct_geotransforms(self):
    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (1, 1))
    b.load_array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    b.set_projection_epsg(4326)
    b2 = b.reproject_epsg(3857)
    self.assertEqual(b2.get_projection_epsg(), 3857)
    self.assertEqual(b2.width(), 3)
    self.assertEqual(b2.height(), 3)
    self.assertNotEqual(b2.get_pixel_width(), 1)
    self.assertNotEqual(b2.get_pixel_height(), 1)
    self.assertNotEqual(b2.ul()[0], b.ul()[0])
    self.assertAlmostEqual(b2.mean(), b.mean())

  def test_raster_gradient_slopes_on_real_dem_map(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)

    # this map is in units of radians (4326), convert to meters (3857)
    b2 = b.reproject_epsg(3857, b.width(), b.height())
    (gx, gy) = b2.central_diff_slopes()

    # confirm some stuff
    max_gx_value = np.nanmax(gx)
    min_gx_value = np.nanmin(gx)
    self.assertGreater(min_gx_value, -90.0)
    self.assertLess(max_gx_value, 90.0)

    max_gy_value = np.nanmax(gy)
    min_gy_value = np.nanmin(gy)
    self.assertGreater(min_gy_value, -90.0)
    self.assertLess(max_gy_value, 90.0)

    # and now load this into its own shape and save to file
    b3 = b2.clone_with_new_data(gx)
    self.assertEqual(b3.band_count(), 1)
    self.assertEqual(b3.shape(), (3600, 1660))
    self.assertEqual(b3.get_projection_epsg(), 3857)
    self.assertEqual(b3.get_no_data(), -9999) # make sure nodata flows thru
    self.assertAlmostEqual(np.nanmax(gx), b3.max(), places=4) # maxes should be same
    b3.write_to_file('/tmp/test_slopes_dem.tif', True, True)
    self.assertAlmostEqual(b3.max(), np.nanmax(gx), places=4)
    self.assertAlmostEqual(b3.max(), 23.72448, places=3)

  def test_real_reproject_to_mollweide_and_calculate_gx(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_b = b.reproject_proj4(MOLLWEIDE)
    self.assertEqual(new_b.get_projection_epsg(), None)
    self.assertEqual(new_b.get_projection_proj4(), MOLLWEIDE)
    (gx, gy) = new_b.central_diff_slopes()

    # this new map is in mollweide so will have a different width and height
    self.assertEqual(new_b.shape(), (3569, 1725))

    b3 = new_b.clone_with_new_data(gx)
    self.assertEqual(b3.band_count(), 1)
    self.assertEqual(b3.shape(), (3569, 1725))
    self.assertLess(b3.max(), 90.0)
    self.assertGreater(b3.min(), -90.0)

    # reproject back to 4326 and check size
    b4 = b3.reproject_epsg(4326, 1500, 850)
    
    # now write this out
    b4.write_to_file('/tmp/slopes_moll_to_4326.tif', True, True)

  def test_raster_gradient_slopes(self):
    arr = [[0, 0, 0], [10, 10, 10], [0, 0, 0]]
    b = RasterBand()
    b.load_array(arr)
    grad_y = [[10, 10, 10], [0, 0, 0], [-10, -10, -10]]
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.array_equal(gy, grad_y), "Y gradients do not match")

    expected_y_slope = [[45, 45, 45], [0, 0, 0], [-45, -45, -45]]
    (sx, sy) = b.central_diff_slopes(5, 5)
    self.assertTrue(np.array_equal(sy, expected_y_slope), "Y slopes do not match")
    expected_x_slope = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    self.assertTrue(np.array_equal(sx, expected_x_slope), "X slopes do not match")

  def test_blank_raster_with_dtype_float64(self):
    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (1, 1))
    b.set_projection_epsg(4326)
    fake_data = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]], dtype=np.float64)
    b.load_array(fake_data)
    self.assertEqual(b.band_count(), 1)
    self.assertEqual(b.max(), 9.0)
    self.assertEqual(b.min(), 1.0)

    # clone it with same data
    b2 = b.clone_with_new_data(fake_data)
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.max(), 9.0)
    self.assertEqual(b2.min(), 1.0)

  def test_raster_gradient_slopes_x(self):
    arr = [[0, 10, 0], [0, 10, 0], [0, 10, 0]]
    b = RasterBand()
    b.load_array(arr)
    grad_x = [[10, 0, -10], [10, 0, -10], [10, 0, -10]]
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.array_equal(gx, grad_x), "X gradients do not match")
    expected_x_slope = [[45, 0, -45], [45, 0, -45], [45, 0, -45]]
    (sx, sy) = b.central_diff_slopes(5, 5)
    self.assertTrue(np.array_equal(sx, expected_x_slope), "X slopes do not match")
    expected_y_slope = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    self.assertTrue(np.array_equal(sy, expected_y_slope), "Y slopes do not match")

  def test_raster_slopes_with_built_in_resolution(self):
    arr = [[0, 1, 0], [0, 1, 0], [0, 1, 0]]
    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (-1, 1))
    b.set_projection_epsg(3857)
    b.load_array(arr)
    grad_x = [[1, 0, -1], [1, 0, -1], [1, 0, -1]]
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.array_equal(gx, grad_x), "X gradients do not match")
    self.assertTrue(b.lr(), (1, -1))

    degree_change = np.degrees(np.arctan(1.0))
    expected_x_slope = np.array([np.degrees(np.arctan(1/2)), np.degrees(0/2), np.degrees(np.arctan(-1/2))])
    (sx, sy) = b.central_diff_slopes()
    self.assertTrue(np.allclose(sx[0], expected_x_slope), "X slopes do not match")
    expected_y_slope = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    self.assertTrue(np.allclose(sy, expected_y_slope), "Y slopes do not match")

  # N = 0 degrees, E = 90, etc.
  def test_raster_face_direction_instead_of_slope(self):
    arr = [[0, 0, 0], [1, 1, 1], [0, 0, 0]] # should be NNN NULLS SSS
    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (1, 1))
    b.set_projection_epsg(4326)
    b.load_array(arr)
    sb = b.central_diff_face_bearing()
    self.assertEqual(sb[0][0], 0.0)
    self.assertEqual(sb[2][0], 180.0)
    self.assertEqual(sb[2][2], 180.0)
    self.assertTrue(np.isnan(sb[1][1]))

  def test_slopes_edge_case_positive_and_negative(self):
    arr = [[0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    b = RasterBand()
    b.blank_raster(4, 4, (1, 1), (1, 1))
    b.set_projection_epsg(4326)
    b.load_array(arr)
    
    # facing east is positive
    # facing west is negative
    row_two_grad = [0, 1, 0, -1]
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.array_equal(gx[1], row_two_grad), "X gradients do not match")

    # facing south is positive
    # facing north is negative
    col_two_grad = [1, 0, -1, 0]
    gy_col_two = gy[:, 2]
    self.assertTrue(np.array_equal(gy_col_two, col_two_grad), "Y gradients do not match")

  def test_raster_face_inverted_pyramid_shape(self):
    arr = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (1, 1))
    b.set_projection_epsg(4326)
    b.load_array(arr)

    # confirm LR
    lr = b.lr()
    self.assertEqual(lr, (4, -2))

    # compute and confirm bearings
    sb = b.central_diff_face_bearing()
    self.assertTrue(np.isnan(sb[0][2]))
    self.assertEqual(sb[0][1], 180.0) # facing south
    self.assertEqual(sb[2][1], 0.0) # north
    self.assertEqual(sb[1][0], 90.0) # east
    self.assertEqual(sb[1][2], 270.0) # west

  def test_raster_face_pyramid_shape(self):
    arr = [[0, 0, 0], [0, 1, 0], [0, 0, 0]]
    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (1, 1))
    b.set_projection_epsg(4326)
    b.load_array(arr)

    # confirm LR
    lr = b.lr()
    self.assertEqual(lr, (4, -2))

    # compute and confirm bearings
    sb = b.central_diff_face_bearing()
    self.assertEqual(sb[0][1], 0.0)
    self.assertTrue(np.isnan(sb[0][2])) # nan for now bc corner
    self.assertEqual(sb[2][1], 180.0)
    self.assertEqual(sb[1][0], 270.0)
    self.assertEqual(sb[1][2], 90.0)
    self.assertTrue(np.isnan(sb[1][1]))

  def test_raster_face_more_complex_5x5_shape(self):
    arr = [[0, 0, 0, 0, 0], [0, 1, 1, 1, 0], [0, 1, 2, 1, 0], [0, 1, 1, 1, 0], [0, 0, 0, 0, 0]]
    b = RasterBand()
    b.blank_raster(5, 5, (1, 1), (1, 1))
    b.set_projection_epsg(4326)
    b.load_array(arr)

    sb = b.central_diff_face_bearing()
    self.assertTrue(np.isnan(sb[2][2])) # peak
    self.assertTrue(np.isnan(sb[0][0])) # corner
    self.assertEqual(sb[1][2], 0.0) # north face
    self.assertEqual(sb[2][1], 270.0) # west face
    self.assertEqual(sb[3][2], 180.0) # south face
    self.assertEqual(sb[2][3], 90.0) # east face
    self.assertEqual(sb[1][1], 360.0 - 45.0) # nw angled face
    self.assertAlmostEqual(sb[1][3], 45.0, 3) # ne angled face
    self.assertEqual(sb[3][3], 135.0) # se angled face
    self.assertEqual(sb[3][1], 225.0)

  def test_raster_face_bearings_with_real_map(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/global.gdem.2022-01.05res.tif')
    b.load_band(1)

    # convert to mollweide
    MOLLWEIDE = '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs +type=crs'
    new_b = b.reproject_proj4(MOLLWEIDE)
    sb = new_b.central_diff_face_bearing()

    # create a file with bearings and write to file
    b2 = new_b.clone_with_new_data(sb)
    b2.write_to_file('/tmp/test_face_bearings.tif', True, True)

  def test_raster_cloning_but_with_empty_data(self):
    b = RasterBand()
    b.blank_raster(3, 3, (1, 1), (1, 1))
    b.set_projection_epsg(4326)
    b.set_band(1)
    b.set_nodata(-99)
    b2 = b.clone_with_no_data()
    self.assertEqual(b2.band_count(), 1)
    self.assertEqual(b2.shape(), (3, 3))
    self.assertEqual(b2.get_projection_epsg(), 4326)

    values = b2.values()
    self.assertTrue(np.all(np.isnan(values)))

  def test_raster_gradient_slopes_nonequal_resolutions(self):
    arr = [[0, 1, 0], [0, 1, 0], [0, 1, 0]]
    b = RasterBand()
    b.load_array(arr)
    grad_x = [[1, 0, -1], [1, 0, -1], [1, 0, -1]]
    (gx, gy) = b.central_diff_gradients()
    self.assertTrue(np.array_equal(gx, grad_x), "X gradients do not match")
    degree_change = np.degrees(np.arctan(1/10))
    expected_x_slope = [[degree_change, 0, -degree_change], 
      [degree_change, 0, -degree_change],
      [degree_change, 0, -degree_change]]
    (sx, sy) = b.central_diff_slopes(5, 5)
    self.assertTrue(np.allclose(sx, expected_x_slope), "X slopes do not match")
    expected_y_slope = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    self.assertTrue(np.allclose(sy, expected_y_slope), "Y slopes do not match")

  def test_raster_gradients(self):
    arr = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    b = RasterBand()
    b.load_array(arr)
    grad_y = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
    grad_x = [[3, 3, 3], [3, 3, 3], [3, 3, 3]]
    (gx, gy) = b.gradients()
    self.assertTrue(np.array_equal(gx, grad_x), "X gradients do not match")
    self.assertTrue(np.array_equal(gy, grad_y), "Y gradients do not match")

  def test_raster_sum_array_with_nodatas(self):
    arr = [[1, 1, 1], [4, 4, 4], [1, 1, -99.0]]
    b = RasterBand()
    b.blank_raster(3, 3, (1,1), (1,1))
    b.set_band(1)
    b.load_array(arr, -99.0)
    self.assertEqual(b.sum(), 17)

  # Upper Left  (-126.0000000,  55.0000000) (126d 0' 0.00"W, 55d 0' 0.00"N)
  # Lower Left  (-126.0000000,  21.0000000) (126d 0' 0.00"W, 21d 0' 0.00"N)
  # Upper Right ( -66.0000000,  55.0000000) ( 66d 0' 0.00"W, 55d 0' 0.00"N)
  # Lower Right ( -66.0000000,  21.0000000) ( 66d 0' 0.00"W, 21d 0' 0.00"N)
  # Center      ( -96.0000000,  38.0000000) ( 96d 0' 0.00"W, 38d 0' 0.00"N)
  def test_get_coordinates(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    (ul, lr) = b.get_bbox()
    self.assertEqual(ul, (-126.0, 55.0))
    self.assertEqual(lr, (-66.0, 21.0))

  def test_get_center(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    (center_x, center_y) = b.get_center()
    self.assertEqual(center_x, -96.0)
    self.assertEqual(center_y, 38.0)
 
  # -88.6111, 47.1472 = None
  def test_get_value_at_location_with_nodata(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    b.set_nodata(-99999)
    value = b.get_value(-88.6111, 47.1472)
    self.assertEqual(value, None)

  # -88.4888, 48.1410 = 73.42019
  def test_get_value_at_location(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    value = b.get_value(-88.4888, 48.1410)
    self.assertEqual(value, 73.42019)

  # -97.449, 26.008 = 0 snow
  def test_get_value_at_location_with_zero(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    b.set_nodata(-99999)
    self.assertEqual(b.band_count(), 1)
    value = b.get_value(-97.449, 26.008) # So texas
    self.assertEqual(value, 0)

  def test_get_value_at_location(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    value = b.get_value(-95.724, 48.546)
    self.assertAlmostEqual(value, 47.079227, places=2)

  # -94.096, 48.973 = None
  def test_get_value_at_location_with_nodata_weird(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    b.set_nodata(-99999)
    value = b.get_value(-94.096, 48.973)
    self.assertEqual(value, None)

  def test_load_band_get_size(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    size = b.shape()
    self.assertEqual(size, (1500, 850))

  def test_nodata_value(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.get_nodata(), -99999)
    b.set_nodata(None)
    self.assertEqual(b.get_nodata(), None)

  # 0,0 should be null because it is a corner and set as nodata
  def test_get_value_outside_bounds_throws_exception(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    b.load_band(1)
    self.assertEqual(b.band_count(), 1)
    self.assertRaises(ValueError, b.get_value, 0, 0)

  def test_get_shape_but_didnt_load_band(self):
    b = RasterBand()
    b.load_url('https://public-images.engineeringdirector.com/dem/snowfall.2017.tif')
    self.assertRaises(ValueError, b.shape)
