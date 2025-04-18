#!/usr/bin/env python3
"""Monte-Carlo simulation for quantum magnetic navigation.

This script generates random trajectories, adds realistic sensor noise,
and evaluates the performance of the navigation filter.

Usage:
    python sim_nav.py [--duration=300] [--num-runs=10] [--plot]

Options:
    --duration=SECONDS    Simulation duration in seconds [default: 300]
    --num-runs=N          Number of Monte-Carlo runs [default: 10]
    --plot                Generate plots of the results
"""

import argparse
import math
import random
import time
from typing import Callable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from qmag_nav.filter.ekf import NavEKF
from qmag_nav.models.geo import LatLon, MagneticVector
from qmag_nav.models.sensor import SensorSpec


class MagneticMapSimulator:
    """Simulated magnetic map for testing."""
    
    def __init__(self, complexity: float = 0.5, seed: int = 42):
        """Initialize the magnetic map simulator.
        
        Args:
            complexity: Controls the spatial frequency of the magnetic field
            seed: Random seed for reproducibility
        """
        self.complexity = complexity
        random.seed(seed)
        np.random.seed(seed)
        
        # Generate random coefficients for the magnetic field model
        self.coeffs = []
        for _ in range(20):  # Increased number of coefficients for more spatial variation
            amp = random.uniform(50, 500)  # Increased amplitude
            kx = random.uniform(-0.5, 0.5) * complexity  # Increased spatial frequency
            ky = random.uniform(-0.5, 0.5) * complexity
            phase = random.uniform(0, 2 * math.pi)
            self.coeffs.append((amp, kx, ky, phase))
    
    def get_field(self, lat: float, lon: float) -> float:
        """Get the magnetic field value at the specified location.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            
        Returns:
            Magnetic field value in nT
        """
        # Base field (typical Earth's field ~50,000 nT)
        field = 50000.0
        
        # Add spatial variations
        for amp, kx, ky, phase in self.coeffs:
            field += amp * math.sin(kx * lat + ky * lon + phase)
        
        return field
    
    def get_field_vector(self, lat: float, lon: float) -> MagneticVector:
        """Get the magnetic field vector at the specified location.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            
        Returns:
            Magnetic field vector in nT
        """
        # Base field components
        bx = 20000.0
        by = 0.0
        bz = 45000.0
        
        # Add spatial variations
        for amp, kx, ky, phase in self.coeffs:
            variation = amp * math.sin(kx * lat + ky * lon + phase)
            bx += variation * 0.2
            by += variation * 0.1
            bz += variation * 0.3
        
        return MagneticVector(bx=bx, by=by, bz=bz)


class TrajectoryGenerator:
    """Generates realistic vehicle trajectories."""
    
    def __init__(self, start_lat: float = 0.0, start_lon: float = 0.0, seed: int = None):
        """Initialize the trajectory generator.
        
        Args:
            start_lat: Starting latitude in degrees
            start_lon: Starting longitude in degrees
            seed: Random seed for reproducibility
        """
        self.lat = start_lat
        self.lon = start_lon
        self.heading = random.uniform(0, 360)  # degrees
        self.speed = random.uniform(5, 15)  # m/s
        
        # Maneuver parameters
        self.turn_rate = 0.0  # deg/s
        self.accel = 0.0  # m/s²
        
        # Time until next maneuver
        self.maneuver_time = random.uniform(10, 30)
        
        if seed is not None:
            random.seed(seed)
    
    def update(self, dt: float) -> Tuple[float, float, float, float, float, float]:
        """Update the trajectory for one time step.
        
        Args:
            dt: Time step in seconds
            
        Returns:
            Tuple of (lat, lon, heading, speed, turn_rate, accel)
        """
        # Update maneuver timer
        self.maneuver_time -= dt
        if self.maneuver_time <= 0:
            # Start a new maneuver
            self.turn_rate = random.uniform(-5, 5)  # deg/s
            self.accel = random.uniform(-0.5, 0.5)  # m/s²
            self.maneuver_time = random.uniform(10, 30)
        
        # Update heading and speed
        self.heading += self.turn_rate * dt
        self.heading %= 360
        self.speed += self.accel * dt
        self.speed = max(1, min(30, self.speed))  # Limit speed
        
        # Convert heading and speed to lat/lon changes
        heading_rad = math.radians(self.heading)
        
        # Earth radius in meters
        earth_radius = 6371000.0
        
        # Distance traveled in this time step
        distance = self.speed * dt
        
        # Convert to lat/lon changes
        dlat = distance * math.cos(heading_rad) / earth_radius * math.degrees(1)
        dlon = distance * math.sin(heading_rad) / (earth_radius * math.cos(math.radians(self.lat))) * math.degrees(1)
        
        # Update position
        self.lat += dlat
        self.lon += dlon
        
        return (self.lat, self.lon, self.heading, self.speed, self.turn_rate, self.accel)


class SensorSimulator:
    """Simulates sensor measurements with realistic noise."""
    
    def __init__(
        self,
        mag_map: MagneticMapSimulator,
        mag_noise_std: float = 5.0,  # Reduced noise
        imu_accel_noise_std: float = 0.05,  # Reduced noise
        imu_gyro_noise_std: float = 0.005,  # Reduced noise
    ):
        """Initialize the sensor simulator.
        
        Args:
            mag_map: Magnetic map simulator
            mag_noise_std: Magnetometer noise standard deviation in nT
            imu_accel_noise_std: Accelerometer noise standard deviation in m/s²
            imu_gyro_noise_std: Gyroscope noise standard deviation in rad/s
        """
        self.mag_map = mag_map
        self.mag_noise_std = mag_noise_std
        self.imu_accel_noise_std = imu_accel_noise_std
        self.imu_gyro_noise_std = imu_gyro_noise_std
    
    def get_magnetometer_reading(self, lat: float, lon: float) -> float:
        """Get a noisy magnetometer reading.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            
        Returns:
            Noisy magnetic field value in nT
        """
        true_field = self.mag_map.get_field(lat, lon)
        noise = random.gauss(0, self.mag_noise_std)
        return true_field + noise
    
    def get_magnetometer_vector(self, lat: float, lon: float) -> MagneticVector:
        """Get a noisy magnetometer vector reading.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            
        Returns:
            Noisy magnetic field vector in nT
        """
        true_vector = self.mag_map.get_field_vector(lat, lon)
        noise_x = random.gauss(0, self.mag_noise_std)
        noise_y = random.gauss(0, self.mag_noise_std)
        noise_z = random.gauss(0, self.mag_noise_std)
        
        return MagneticVector(
            bx=true_vector.bx + noise_x,
            by=true_vector.by + noise_y,
            bz=true_vector.bz + noise_z,
        )
    
    def get_imu_reading(
        self,
        heading: float,
        speed: float,
        turn_rate: float,
        accel: float,
    ) -> Tuple[Tuple[float, float], float]:
        """Get a noisy IMU reading.
        
        Args:
            heading: Current heading in degrees
            speed: Current speed in m/s
            turn_rate: Current turn rate in deg/s
            accel: Current acceleration in m/s²
            
        Returns:
            Tuple of (accelerometer, gyroscope) readings
        """
        # Convert heading to radians
        heading_rad = math.radians(heading)
        
        # True accelerometer readings (in vehicle frame)
        accel_forward = accel
        accel_right = speed * math.radians(turn_rate)  # centripetal acceleration
        
        # Convert to North-East frame
        accel_north = accel_forward * math.cos(heading_rad) - accel_right * math.sin(heading_rad)
        accel_east = accel_forward * math.sin(heading_rad) + accel_right * math.cos(heading_rad)
        
        # Add noise
        accel_north += random.gauss(0, self.imu_accel_noise_std)
        accel_east += random.gauss(0, self.imu_accel_noise_std)
        
        # Gyroscope reading (yaw rate)
        gyro = math.radians(turn_rate) + random.gauss(0, self.imu_gyro_noise_std)
        
        return ((accel_north, accel_east), gyro)


def run_simulation(
    duration: float = 300.0,
    dt: float = 0.1,
    use_imu: bool = True,
    use_vector: bool = False,
    initial_pos_error: float = 0.001,  # Reduced to ~100m
) -> Tuple[List[float], List[float], List[float], List[float], List[float]]:
    """Run a single simulation.
    
    Args:
        duration: Simulation duration in seconds
        dt: Time step in seconds
        use_imu: Whether to use IMU measurements
        use_vector: Whether to use vector magnetometer measurements
        initial_pos_error: Initial position error in degrees
        
    Returns:
        Tuple of (times, true_errors, estimated_errors, latitudes, longitudes)
    """
    # Create simulation components
    mag_map = MagneticMapSimulator()
    trajectory = TrajectoryGenerator()
    sensors = SensorSimulator(mag_map)
    
    # Initialize true position
    true_lat, true_lon, heading, speed, turn_rate, accel = trajectory.update(0)
    
    # Initialize EKF with error
    init_lat = true_lat + random.gauss(0, initial_pos_error)
    init_lon = true_lon + random.gauss(0, initial_pos_error)
    
    # Initialize with velocity if using IMU
    initial_vel = None
    if use_imu:
        # Convert speed and heading to lat/lon velocity
        heading_rad = math.radians(heading)
        earth_radius = 6371000.0
        dlat = speed * math.cos(heading_rad) / earth_radius * math.degrees(1)
        dlon = speed * math.sin(heading_rad) / (earth_radius * math.cos(math.radians(true_lat))) * math.degrees(1)
        initial_vel = (dlat, dlon)
    
    ekf = NavEKF(
        initial=LatLon(init_lat, init_lon),
        initial_velocity=initial_vel,
        process_noise=0.001,  # Reduced process noise
    )
    
    # Storage for results
    times = []
    true_positions = []
    estimated_positions = []
    true_errors = []
    estimated_errors = []
    
    # Run simulation
    t = 0.0
    while t < duration:
        # Update true trajectory
        true_lat, true_lon, heading, speed, turn_rate, accel = trajectory.update(dt)
        true_pos = LatLon(true_lat, true_lon)
        
        # Get sensor measurements
        mag_reading = sensors.get_magnetometer_reading(true_lat, true_lon)
        mag_vector = sensors.get_magnetometer_vector(true_lat, true_lon)
        (accel_north, accel_east), gyro = sensors.get_imu_reading(heading, speed, turn_rate, accel)
        
        # EKF prediction step
        if use_imu:
            ekf.predict_with_imu(dt, (accel_north, accel_east), gyro)
        else:
            ekf.predict(dt)
        
        # EKF update step
        if use_vector:
            ekf.update_vector(mag_vector, mag_map.get_field_vector)
        else:
            ekf.update(mag_reading, mag_map.get_field)
        
        # Get position estimate
        est_pos = ekf.estimate()
        
        # Calculate error
        true_error = true_pos.distance_to(est_pos)
        
        # Store results
        times.append(t)
        true_positions.append(true_pos)
        estimated_positions.append(est_pos)
        true_errors.append(true_error)
        estimated_errors.append(math.sqrt(ekf.P[0][0] + ekf.P[1][1]) * 111000)  # approx m
        
        # Increment time
        t += dt
    
    # Extract lat/lon for plotting
    latitudes = [pos.lat for pos in true_positions]
    longitudes = [pos.lon for pos in true_positions]
    
    return times, true_errors, estimated_errors, latitudes, longitudes


def run_monte_carlo(
    num_runs: int = 10,
    duration: float = 300.0,
    use_imu: bool = True,
    use_vector: bool = False,
    plot: bool = True,
) -> None:
    """Run multiple Monte-Carlo simulations and analyze results.
    
    Args:
        num_runs: Number of Monte-Carlo runs
        duration: Simulation duration in seconds
        use_imu: Whether to use IMU measurements
        use_vector: Whether to use vector magnetometer measurements
        plot: Whether to generate plots
    """
    print(f"Running {num_runs} Monte-Carlo simulations...")
    print(f"Duration: {duration} seconds")
    print(f"Using IMU: {use_imu}")
    print(f"Using vector magnetometer: {use_vector}")
    
    all_errors = []
    all_trajectories = []
    all_est_trajectories = []
    
    start_time = time.time()
    
    for i in range(num_runs):
        print(f"Run {i+1}/{num_runs}...")
        times, true_errors, estimated_errors, lats, lons = run_simulation(
            duration=duration,
            use_imu=use_imu,
            use_vector=use_vector,
        )
        all_errors.append(true_errors)
        all_trajectories.append((lats, lons))
    
    elapsed = time.time() - start_time
    print(f"Simulations completed in {elapsed:.1f} seconds")
    
    # Calculate statistics
    mean_errors = np.mean(all_errors, axis=0)
    std_errors = np.std(all_errors, axis=0)
    rms_error = np.sqrt(np.mean(np.square(mean_errors)))
    max_error = np.max(mean_errors)
    
    print(f"RMS Error: {rms_error:.2f} meters")
    print(f"Max Error: {max_error:.2f} meters")
    
    if plot:
        # Plot error over time
        plt.figure(figsize=(10, 6))
        plt.plot(times, mean_errors, 'b-', label='Mean Error')
        plt.fill_between(
            times,
            mean_errors - std_errors,
            mean_errors + std_errors,
            alpha=0.3,
            color='b',
            label='±1σ',
        )
        plt.xlabel('Time (s)')
        plt.ylabel('Error (m)')
        plt.title('Navigation Error vs. Time')
        plt.grid(True)
        plt.legend()
        plt.savefig('nav_error.png', dpi=300)
        
        # Plot trajectories
        plt.figure(figsize=(10, 8))
        for i, (lats, lons) in enumerate(all_trajectories):
            if i == 0:  # Only label the first one
                plt.plot(lons, lats, 'k-', alpha=0.3, label='True Trajectories')
            else:
                plt.plot(lons, lats, 'k-', alpha=0.3)
        plt.xlabel('Longitude (°)')
        plt.ylabel('Latitude (°)')
        plt.title('Monte-Carlo Trajectories')
        plt.grid(True)
        plt.legend()
        plt.axis('equal')
        plt.savefig('trajectories.png', dpi=300)
        
        print("Plots saved as 'nav_error.png' and 'trajectories.png'")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Monte-Carlo navigation simulation')
    parser.add_argument('--duration', type=float, default=300.0,
                        help='Simulation duration in seconds')
    parser.add_argument('--num-runs', type=int, default=10,
                        help='Number of Monte-Carlo runs')
    parser.add_argument('--plot', action='store_true',
                        help='Generate plots')
    parser.add_argument('--no-imu', action='store_true',
                        help='Disable IMU integration')
    parser.add_argument('--vector', action='store_true',
                        help='Use vector magnetometer')
    
    args = parser.parse_args()
    
    run_monte_carlo(
        num_runs=args.num_runs,
        duration=args.duration,
        use_imu=not args.no_imu,
        use_vector=args.vector,
        plot=args.plot,
    )


if __name__ == '__main__':
    main()