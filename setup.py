from setuptools import setup, find_packages

setup(
  name='wx_logs',
  version='0.5.10',
  author='Tom Hayden',
  author_email='thayden@gmail.com',
  packages=find_packages(exclude=['tests', 'tests.*']),
  long_description="A weather logging library, useful for processing and analyzing weather data.",
  include_package_data=True,
  install_requires=['dateparser', 'numpy', 'pytz', 'gdal', 'pyproj', 'gstools', 'windrose', 'matplotlib', 'joblib'],
  entry_points={
    'console_scripts': [],
  },
  classifiers=[
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
  ],
  python_requires='>=3.6',
)

