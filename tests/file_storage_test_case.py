import unittest
from wx_logs import FileStorage

class FileStorageTestCase(unittest.TestCase):

  def test_FileStorage(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = FileStorage()
    s.set_file_url(f)
    s.download()
    self.assertEqual(s.get_file_name(), 'snowfall.2017.tif')
    
    # test that the file is downloaded
    #-rw-rw-r-- 1 tom tom 4919964 Jul 20 17:36 /tmp/snowfall.2017.tif
    self.assertEqual(s.get_file_size(), 4919964)

  def test_fileStorage_with_expected_md5_hash(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = FileStorage()
    s.set_file_url(f)
    s.set_expected_md5_hash('6f3da1356a9992c1348c384f87b3ef6d')
    s.download()
    self.assertEqual(s.get_md5_hash(), '6f3da1356a9992c1348c384f87b3ef6d')
    self.assertEqual(s.is_zip_file(), False)
    file_type = s.get_gis_file_type()
    self.assertEqual(file_type, 'GTIFF')
    self.assertEqual(s.get_relative_path_to_file(), 'snowfall.2017.tif')

  # test this file 
  # vector_url = 'https://public-images.engineeringdirector.com/dem/Oregon_State_Boundary_6507293181691922778.zip'
  def test_state_boundary_file_is_gdb(self):
    f = 'https://public-images.engineeringdirector.com/dem/Oregon_State_Boundary_6507293181691922778.zip'
    s = FileStorage()
    s.set_file_url(f)
    s.download()
    self.assertEqual(s.is_zip_file(), True)

    # this is a zip file so lets extract the list of contents
    file_contents = s.peek_zip_file()
    num_files = len(file_contents)
    self.assertEqual(num_files, 49)

    self.assertEqual(len(s.peek_zip_file_toplevel()), 1)

    # try to figure out what kind of GIS file this is
    file_type = s.get_gis_file_type()
    self.assertEqual(file_type, 'GDB')
    self.assertEqual(s.zip_needs_subfolder(), True)

    # new relative path
    s.unzip()
    relative_path = 'Oregon_State_Boundary_6507293181691922778/fb21f407-5d50-45c8-91ab-f626e3c9d203.gdb'
    target_file = s.get_cache_dir() + '/' + relative_path
    self.assertEqual(s.get_relative_path_to_file(), relative_path)
    self.assertEqual(s.get_full_path_to_file(), target_file)


  def test_zipfile_unzip_into_folder(self):
    f = 'https://public-images.engineeringdirector.com/dem/simple-boundaries.zip'
    s = FileStorage()
    s.set_file_url(f)
    s.download()
    s.set_expected_md5_hash('0925413e53bebe4afa7aea70e02f65b0')
    self.assertEqual(s.is_zip_file(), True)

    file_contents = s.peek_zip_file()
    num_files = len(file_contents)
    self.assertEqual(num_files, 7)

    top_level_files = s.peek_zip_file_toplevel()
    self.assertEqual(len(top_level_files), 7)
    self.assertEqual(s.get_gis_file_type(), 'SHP')
    self.assertEqual(s.zip_needs_subfolder(), True)

    # get the original cache directory, which may vary by host
    cache_dir = s.get_cache_dir()
    s.unzip() 

    # ne_10m_admin_0_boundary_lines_land.shp
    relative_path = 'simple-boundaries/ne_10m_admin_0_boundary_lines_land.shp'
    target_file = cache_dir + '/' + relative_path
    self.assertEqual(s.get_relative_path_to_file(), relative_path)
    self.assertEqual(s.get_full_path_to_file(), target_file)

  def test_filestorage_download_zip_and_expand_zip_file(self):
    f = 'https://public-images.engineeringdirector.com/dem/Oregon_State_Boundary_6507293181691922778.zip'
    s = FileStorage()
    s.set_file_url(f)
    s.download()
    s.set_expected_md5_hash('9aaa99d2f92a162035a91cb36df5ef5a')
    self.assertEqual(s.is_zip_file(), True)

    # this is a zip file so lets extract the list of contents
    file_contents = s.peek_zip_file()
    num_files = len(file_contents)
    self.assertEqual(num_files, 49)

    self.assertEqual(len(s.peek_zip_file_toplevel()), 1)

    # try to figure out what kind of GIS file this is
    file_type = s.get_gis_file_type()
    self.assertEqual(file_type, 'GDB')

  def test_bad_url_throws_exception(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017bad.tif'
    s = FileStorage()
    s.set_file_url(f)
    self.assertRaises(ValueError, s.download)

  def test_fileStorage_with_bad_expected_md5_hash(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = FileStorage()
    s.set_file_url(f)
    s.set_expected_md5_hash('BAD HASH')
    self.assertRaises(ValueError, s.download)

  def test_md5_hash_of_the_file(self):
    f = 'https://public-images.engineeringdirector.com/dem/snowfall.2017.tif'
    s = FileStorage()
    s.set_file_url(f)
    s.download()
    self.assertEqual(s.get_md5_hash(), '6f3da1356a9992c1348c384f87b3ef6d')

  def test_fileStorage_always_download_so_deletes_old_file(self):
    f = 'https://public-images.engineeringdirector.com/test/prism.tif'
    s = FileStorage()
    s.set_expected_md5_hash('e4d80e4c5b8be08045119f56a558f323')
    s.set_file_url(f)
    s.delete_file()

    # now download the file
    s.download()
    self.assertEqual(s.get_relative_path_to_file(), 'prism.tif')
    self.assertEqual(s.get_md5_hash(), 'e4d80e4c5b8be08045119f56a558f323')
