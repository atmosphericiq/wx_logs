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
