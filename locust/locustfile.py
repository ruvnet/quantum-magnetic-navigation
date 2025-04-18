"""
Locust load testing file for Quantum Magnetic Navigation API.
"""

import random
from locust import HttpUser, task, between


class QMagNavUser(HttpUser):
    """
    Simulated user for load testing the Quantum Magnetic Navigation API.
    """
    
    # Wait between 1 and 5 seconds between tasks
    wait_time = between(1, 5)
    
    @task(1)
    def health_check(self):
        """Test the health check endpoint."""
        with self.client.get("/healthz", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with status code: {response.status_code}")
    
    @task(5)
    def estimate_position(self):
        """Test the position estimation endpoint with random coordinates."""
        # Generate random latitude and longitude within reasonable bounds
        lat = random.uniform(-85, 85)
        lon = random.uniform(-180, 180)
        
        payload = {"lat": lat, "lon": lon}
        
        with self.client.post("/estimate", json=payload, catch_response=True) as response:
            if response.status_code == 200:
                # Verify the response contains expected fields
                try:
                    data = response.json()
                    if all(k in data for k in ["lat", "lon", "quality"]):
                        response.success()
                    else:
                        response.failure("Response missing required fields")
                except Exception as e:
                    response.failure(f"Invalid JSON response: {str(e)}")
            else:
                response.failure(f"Estimate failed with status code: {response.status_code}")


# To run:
# locust -f locustfile.py --host http://localhost:8000