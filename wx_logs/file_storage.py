# file_storage.py
# this is a file storage class which is used to download
# a file from a URL and store it locally
# it also has a method to check the md5 hash of the file
# and if it doesn't match, it will raise an exception
# author: Tom Hayden

import json
import hashlib
import os
import platform
import logging
import datetime
import requests
import zipfile
import shutil

logger = logging.getLogger(__name__)

class FileStorage:

  def __init__(self):
    self.set_cache_dir()
    self.file_url = None
    self.expected_md5_hash = None
    self.relative_path = None

  def get_cache_dir(self):
    return self.cache_dir

  def set_file_url(self, file_url):
    self.file_url = file_url

    # figure out the relative_path from the http url
    self.relative_path = os.path.basename(self.file_url)

  def set_cache_dir(self):
    if platform.system() == 'Windows':
      self.cache_dir = os.getenv('LOCALAPPDATA')
    else:
      self.cache_dir = os.path.expanduser('~/.cache')
    self.cache_dir = os.path.join(self.cache_dir, 'wx_logs')
    if not os.path.exists(self.cache_dir):
      os.makedirs(self.cache_dir)
 
  def get_relative_path_to_file(self):
    return self.relative_path

  def get_full_path_to_file(self):
    return self.get_cache_dir() + '/' + self.get_relative_path_to_file()

  def set_expected_md5_hash(self, md5_hash):
    self.expected_md5_hash = md5_hash

  # return ONLY the relative_path of the file
  def get_file_name(self):
    return self.relative_path

  def get_file_size(self):
    return os.path.getsize(self.get_full_path_to_file())

  # md5 hash of the file
  def get_md5_hash(self):
    file_path = self.get_full_path_to_file()
    with open(file_path, 'rb') as f:
      return hashlib.md5(f.read()).hexdigest()

  # this function looks at the file (or at the contents of the zip file)
  # and determines what kind of file it is
  # supported: GPKG, GTIFF, GDB, SHP, GEOJSON
  def get_gis_file_type(self):
    if self.is_zip_file():
      contents = self.peek_zip_file_toplevel()
      for c in contents:
        if c.endswith('.gpkg'):
          return 'GPKG'
        elif c.endswith('.gdb'):
          return 'GDB'
        elif c.endswith('.shp'):
          return 'SHP'
        elif c.endswith('.geojson'):
          return 'GEOJSON'
        elif c.endswith('.tif') or c.endswith('.tiff'):
          return 'GTIFF'
    else:
      if self.relative_path.endswith('.gpkg'):
        return 'GPKG'
      elif self.relative_path.endswith('.gdb'):
        return 'GDB'
      elif self.relative_path.endswith('.shp'):
        return 'SHP'
      elif self.relative_path.endswith('.geojson'):
        return 'GEOJSON'
      elif self.relative_path.endswith('.tif') or self.relative_path.endswith('.tiff'):
        return 'GTIFF'
    return None

  def is_zip_file(self):
    return self.relative_path.endswith('.zip')

  # if the file is a zip file then peek into it
  # and return the list of contents
  def peek_zip_file(self):
    file_path = self.get_full_path_to_file()
    with zipfile.ZipFile(file_path, 'r') as z:
      return z.namelist()

  # peek into the zipfile and only return the top level
  def peek_zip_file_toplevel(self):
    all_items = self.peek_zip_file()
    top_level = {}
    for item in all_items:
      if '/' in item: # folder
        folder_name = item.split('/')[0]
        if folder_name not in top_level:
          top_level[folder_name] = 1
      else:
        top_level[item] = 1
    return top_level.keys()

  # extract the zip file to the cache directory
  # and return the main file name
  def unzip(self, overwrite=True):
    extract_dir = self.get_cache_dir()
    file_path = self.get_full_path_to_file()
    logger.info(f"Unzipping file: {file_path}")
    with zipfile.ZipFile(file_path, 'r') as z:
      contents = z.namelist()
      if self.zip_needs_subfolder() is False:
        # extract the single file to the cache directory
        z.extractall(extract_dir)
        self._autodetect_new_file(extract_dir)
      else:
        # extract the contents to a subfolder
        subfolder = self.relative_path.replace('.zip', '')
        subfolder = os.path.join(extract_dir, subfolder)
        if os.path.exists(subfolder):
          if overwrite:
            shutil.rmtree(subfolder)
          else:
            return subfolder
        os.makedirs(subfolder)
        z.extractall(subfolder)
        self._autodetect_new_file(subfolder)
  
  # updates the self.relative_path to point to the new
  def _autodetect_new_file(self, new_folder):
    if '.gdb' in new_folder:
      self.relative_path = new_folder
      return True
    if '.gpkg' in new_folder:
      self.relative_path = new_folder
      return True

    # if there is a gdb file in here, then grab that
    folder_contents = os.listdir(new_folder)
    for item in folder_contents:
      if item.endswith('.gdb'):
        new_relative_path = new_folder + '/' + item
        new_relative_path_relative_to_cache = new_relative_path.replace(self.cache_dir + '/', '')
        self.relative_path = new_relative_path_relative_to_cache
        return True

    # if the folder contains a .shp then that .shp file is teh relative_path
    folder_contents = os.listdir(new_folder)
    for item in folder_contents:
      if item.endswith('.shp'):
        new_relative_path = new_folder + '/' + item
        new_relative_path_relative_to_cache = new_relative_path.replace(self.cache_dir + '/', '')
        self.relative_path = new_relative_path_relative_to_cache
        return True

    # if we are here then we dont know what kind of
    # file we're trying to look at so throw exception
    raise ValueError("Could not autodetect new file")

  def zip_needs_subfolder(self):
    file_path = self.get_full_path_to_file()
    with zipfile.ZipFile(file_path, 'r') as z:
      contents = z.namelist()
      return len(contents) > 1

  def delete_file(self):
    file_name = self.get_file_name()
    if os.path.exists(file_name):
      os.remove(file_name)

  # this the main call to download the file, but we should also 
  # make sure to see if it's already there and if so, check the md5 hash
  # and in that case just return bc we are ok
  def download(self, unzip=True):
    if self.file_url is None:
      raise ValueError("No file URL set. call set_file_url()")
    file_name = self.get_full_path_to_file()
    if os.path.exists(file_name):
      if self.expected_md5_hash is not None:
        actual_md5_hash = self.get_md5_hash()
        if actual_md5_hash != self.expected_md5_hash:
          raise ValueError(f"MD5 hash mismatch for file: {self.file_url}")
      return
    logger.info(f"Downloading file: {self.file_url}")
    response = requests.get(self.file_url)
    if response.status_code != 200:
      raise ValueError(f"Invalid response code: {response.status_code}")

    with open(file_name, 'wb') as f:
      f.write(response.content)
    logger.info(f"Downloaded file: {self.file_url}")

    if self.expected_md5_hash is not None:
      actual_md5_hash = self.get_md5_hash()
      if actual_md5_hash != self.expected_md5_hash:
        raise ValueError(f"MD5 hash mismatch for file: {self.file_url}")
