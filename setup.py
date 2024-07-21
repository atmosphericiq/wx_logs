from setuptools import setup, find_packages

setup(
  name='wx_logs',
  version='0.2.21',
  author='Tom Hayden',
  author_email='thayden@gmail.com',
  packages=find_packages(exclude=['tests', 'tests.*']),
  long_description="A weather logging library, useful for processing and analyzing weather data.",
  include_package_data=True,
  install_requires=['dateparser', 'numpy', 'pytz', 'gdal'],
  entry_points={
    'console_scripts': [],
  },
)

