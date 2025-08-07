### 📋 **Embedded Systems Firmware Engineer - Take-Home Test**

------

#### **Objective:**

- Develop a **Linux kernel driver** for the **MPU-6050** sensor.
- Implement **unit regression tests** for the driver code.
- Set up a **CI/CD pipeline** on GitHub that automates the build, test, and deployment process.
- Create **end-to-end (E2E) functional tests** that verify the driver is working with the sensor in a real environment.

#### **Test Breakdown:**

------

### **Part 1: Writing the Kernel Device Driver for MPU-6050**

**Problem**: Write a **Linux kernel driver** that interacts with an **MPU-6050** sensor (using I2C). The driver should initialize the sensor, read sensor data (e.g., acceleration and gyroscope data), and expose that data to user-space via a simple interface (e.g., `/dev/mpu6050`).

**Requirements**:

1. **Initialization**:
   - Probe the I2C bus for the MPU-6050 sensor.
   - Configure the sensor for continuous reading (e.g., set the sample rate and power management).
   - Implement error handling for invalid sensor states.
2. **Read Data**:
   - Implement a read function to retrieve sensor data (accelerometer, gyroscope, and temperature readings) from the MPU-6050 and return it to user-space.
3. **Exposing Data to User-Space**:
   - Expose the data via a **character device** file, e.g., `/dev/mpu6050`.
   - Implement a `read()` function to allow user-space programs to access the sensor data.
   - Optionally, you may implement an `ioctl()` interface for configuring the sensor parameters (e.g., sample rate, power modes).

**Deliverables**:

- A working **MPU-6050 Linux kernel driver**.
- Code that initializes the driver and reads data from the sensor.
- Documentation on how to load, configure, and interact with the driver.

------

### **Part 2: Unit Regression Tests**

**Problem**: Write **unit tests** for the kernel driver functions. The tests should verify the correctness of the driver’s behavior in isolated, controlled conditions. Use **mocking** where appropriate to simulate interactions with the hardware.

**Requirements**:

1. Use **CUnit** or **Google Test** (or similar framework) to write the unit tests.
2. Mock out hardware interactions (e.g., I2C communication) using **mocking libraries** (e.g., **CMock**, **FakeIt**, or **Google Mock**).
3. Test the following aspects of the driver:
   - Correct initialization of the device.
   - Error handling when no device is found.
   - Correct data reading (valid data from the sensor should be returned, and invalid data should be properly handled).
   - Any configuration settings or adjustments (e.g., sample rate, sensor power mode).
4. Ensure tests are automated and runable in a CI/CD pipeline.

**Deliverables**:

- A set of **unit regression tests**.
- Instructions on running the tests using **CUnit** or **Google Test**.

------

### **Part 3: Setting Up the CI/CD Pipeline (GitHub Actions)**

**Problem**: Set up a **CI/CD pipeline** using **GitHub Actions** that automates the following:

1. **Build**: Build the kernel module whenever changes are pushed to the repository.
2. **Test**: Run the unit tests on the kernel driver.
3. **Linting**: Perform basic **C code linting** using `clang-format` or `cppcheck`.
4. **Push Artifacts**: Optionally, upload compiled kernel modules as build artifacts.
5. **Documentation**: Check for any broken or missing documentation and report errors.

**Requirements**:

1. Set up a **GitHub Actions workflow** (`.github/workflows/ci.yml`).
2. Include the following steps in the workflow:
   - Checkout the repository.
   - Set up the kernel build environment (e.g., use **Docker** to ensure consistency).
   - Compile the kernel module.
   - Run the unit regression tests.
   - Generate a **coverage report** (if applicable).
   - Run **clang-format** or other style checkers on the code.
3. Provide a **README** with instructions for setting up and running the CI/CD pipeline.

**Deliverables**:

- A **GitHub Actions pipeline** configuration file.
- Documentation on how to trigger the pipeline and interpret the results.

------

### **Part 4: End-to-End (E2E) Functional Test**

**Problem**: Create a **real-world functional test** that simulates the interaction between the kernel driver and the MPU-6050 sensor. The test should:

- **Initialize the driver** and confirm that the sensor is properly detected.
- **Read data** from the sensor.
- **Verify** that the data falls within expected ranges for acceleration, gyroscope, and temperature values.

**Requirements**:

1. Write a user-space test (e.g., using a C program or Python script) that:
   - Opens the `/dev/mpu6050` device file.
   - Reads data from the sensor and prints it to the console.
   - Verifies the data falls within expected physical ranges (e.g., acceleration should be between -16g to +16g).
2. The test should pass under typical conditions and produce a useful output in case of failure.

**Deliverables**:

- An **end-to-end functional test** that interacts with the sensor and verifies the data.
- Test results showing that the sensor operates within expected parameters.

------

### **Evaluation Criteria**:

1. **Functionality**: Does the kernel driver interact with the MPU-6050 sensor as expected? Is data returned correctly?
2. **Testing**: Are the unit tests comprehensive? Do they cover critical areas of the driver? Are the tests automated and integrated into the CI/CD pipeline?
3. **Code Quality**: Is the code clean, well-commented, and easy to understand? Does it follow best practices for kernel driver development?
4. **CI/CD Pipeline**: Is the CI/CD pipeline well-configured and automated? Does it handle builds, tests, and linting effectively?
5. **End-to-End Test**: Does the E2E test simulate realistic interactions with the hardware? Is it able to detect failures in the driver’s behavior?

------

### **Submission Instructions**:

- Provide a GitHub repository with the following:
  1. Kernel driver code
  2. Unit tests and test framework
  3. GitHub Actions CI/CD configuration
  4. E2E functional test code
  5. Documentation for setting up the environment and running tests
- Ensure that the repository is well-organized and includes a **README** with setup instructions.