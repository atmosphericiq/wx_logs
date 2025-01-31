# WX Logs

WX Logs is a comprehensive Python library designed for processing, analyzing, and managing weather data. It provides an array of tools for working with weather stations, raster and vector geospatial data, as well as processing environmental conditions like windrose and time of wetness.

## Features

- **Weather Station Management**: Create and manage weather stations with functionality to store and analyze temperature, humidity, wind speed, and more.
- **Kriging Interpolation**: Use the `Kriger` class to interpolate spatial data points using various variogram models.
- **Windrose Analysis**: Analyze wind direction and speed distributions with the `WindRose` class.
- **Tow Calculation**: Compute the time of wetness (TOW) which is crucial for evaluating corrosion on materials.
- **Raster and Vector Conversion**: Convert raster geolocation data to vector formats and compute distances between them.
- **Hourly Data Handling**: Store and process data with hourly granularity including precipitation accumulation.
- **Data Storage & Retrieval**: Handle downloading, storing, and verifying geospatial files with the `FileStorage` class.

## Installation

Ensure you have Python 3.6 or later. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Getting Started

Here is a simple example to create a weather station, add some data, and perform an analysis:

```python
from wx_logs.weather_station import WeatherStation

# Create a weather station
station = WeatherStation(reading_type='STATION')

# Set station metadata
station.set_station_id("001")
station.set_station_name("Sample Station")

# Add weather data
station.add_temp_c(22.5, "2023-10-12T14:00:00Z")
station.add_humidity(55.0, "2023-10-12T14:00:00Z")
station.add_wind(5.0, 180, "2023-10-12T14:00:00Z")

# Retrieve a wind rose analysis
wind_rose = station.get_wind_rose()
print(wind_rose)
```

## Scripts and Tools

1. **Kriging**: For advanced interpolation of geospatial data points using different models: Exponential, Gaussian, Matern, Spherical.
2. **WindRose**: Analyze wind speed and direction, generating distributions.
3. **Grid-to-Point Conversion**: Convert raster grids to vector points for analysis with `GridToPoint`.
4. **Raster Distance Computation**: Compute distance from raster band to nearest vector object using `RasterDistanceToVector`.
5. **Time of Wetness (TOW)**: Calculate TOW for a given year or period to estimate corrosion rates.
6. **Data Storage**: Efficiently download and store files with checksums and type detection.

## Running Unit Tests

The WX Logs project includes a comprehensive suite of unit tests designed to verify the functionality of the library across a range of scenarios. These tests ensure that the modules perform as expected when analyzing and processing weather data.

### Prerequisites

Ensure your environment is set up with Python 3.6 or later, and all dependencies installed (see the **Installation** section).

### Running All Tests

You can run all the unit tests from the terminal using:

```bash
python3 -m unittest discover tests
```

This command will automatically discover and run all test cases found within the `tests` directory.

### Running a Specific Test

To run a specific test case, specify the test file or class directly. For example, to run the WindRose tests, use:

```bash
python3 -m unittest tests.wind_rose_test_case.WindRoseTestCase
```

### Example Test Cases

- **Grid to Point Test:** Verifies grid-to-point conversion functionality.
  ```bash
  python3 -m unittest tests.grid_to_point_test_case.GridToPointTestCase
  ```
- **WindRose Analysis Test:**
  ```bash
  python3 -m unittest tests.wind_rose_test_case.WindRoseTestCase
  ```
- **Kriging Functionality Test:**
  ```bash
  python3 -m unittest tests.kriger_test_case.KrigerTestCase
  ```

Consult individual test files for additional details on assertions and scenarios covered.

## Contributors

- Tom Hayden (Author)

## License

This project is licensed under the MIT License.
