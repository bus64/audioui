#File:  src/performances/blob.py © 2025 projectemergence. All rights reserved.
import os
import configparser
import requests
import json

# Constants for JSON Blob
JSONBLOB_API_URL = "https://jsonblob.com/api/jsonBlob"

class BlobManager:
    """Handles interactions with JSON Blob."""

    def __init__(self, blob_id="1294281086207909888"):
        """
        Initialize the BlobManager with an optional blob ID.
        If no blob ID is provided, it can be set later.
        """
        self.blob_id = blob_id
        self.base_url = JSONBLOB_API_URL if not blob_id else f"{JSONBLOB_API_URL}/{self.blob_id}"

    def create_blob(self, data):
        """
        Create a new JSON Blob.

        Args:
            data (dict): The JSON data to store.

        Returns:
            str: The blob ID if creation is successful, else None.
        """
        try:
            response = requests.post(
                JSONBLOB_API_URL,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                data=json.dumps(data)
            )
            if response.status_code == 201:
                location = response.headers.get('Location', '')
                self.blob_id = location.split('/')[-1]
                self.base_url = f"{JSONBLOB_API_URL}/{self.blob_id}"
                print(f"Blob created successfully with ID: {self.blob_id}")
                return self.blob_id
            else:
                print(f"Error creating blob: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception during POST: {e}")
            return None

    def get_blob(self):
        """
        Retrieve the current JSON Blob data.

        Returns:
            dict: The JSON data if retrieval is successful, else None.
        """
        if not self.blob_id:
            print("Blob ID is not set.")
            return None

        try:
            response = requests.get(
                self.base_url,
                headers={"Accept": "application/json"}
            )
            if response.status_code == 200:
                #print("Blob retrieved successfully.")
                return response.json()
            elif response.status_code == 404:
                print("Blob not found.")
                return None
            else:
                print(f"Error retrieving blob: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception during GET: {e}")
            return None

    def update_blob(self, data):
        """
        Update the JSON Blob with new data.

        Args:
            data (dict): The new JSON data to store.

        Returns:
            bool: True if update is successful, else False.
        """
        if not self.blob_id:
            print("Blob ID is not set.")
            return False

        try:
            response = requests.put(
                self.base_url,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                data=json.dumps(data)
            )
            if response.status_code == 200:
                #print("Blob updated successfully.")
                return True
            elif response.status_code == 404:
                print("Blob not found.")
                return False
            else:
                print(f"Error updating blob: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Exception during PUT: {e}")
            return False

    def delete_blob(self):
        """
        Delete the JSON Blob.

        Returns:
            bool: True if deletion is successful, else False.
        """
        if not self.blob_id:
            print("Blob ID is not set.")
            return False

        try:
            response = requests.delete(
                self.base_url,
                headers={"Accept": "application/json"}
            )
            if response.status_code == 200:
                print("Blob deleted successfully.")
                self.blob_id = None
                self.base_url = JSONBLOB_API_URL
                return True
            elif response.status_code == 404:
                print("Blob not found.")
                return False
            elif response.status_code == 405:
                print("Deleting blobs is not enabled.")
                return False
            else:
                print(f"Error deleting blob: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Exception during DELETE: {e}")
            return False

    def get_custom_url(self, custom_path):
        """
        Retrieve blob data using a custom URL path.

        Args:
            custom_path (str): The custom URL path after /api/.

        Returns:
            dict: The JSON data if retrieval is successful, else None.
        """
        custom_url = f"https://jsonblob.com/api/{custom_path}"
        try:
            response = requests.get(
                custom_url,
                headers={"Accept": "application/json"}
            )
            if response.status_code == 200:
                print("Blob retrieved successfully using custom URL.")
                return response.json()
            elif response.status_code == 404:
                print("Blob not found at the custom URL.")
                return None
            else:
                print(f"Error retrieving blob via custom URL: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Exception during GET with custom URL: {e}")
            return None

    def set_blob_id(self, blob_id):
        """
        Set the blob ID manually.

        Args:
            blob_id (str): The blob ID to set.
        """
        self.blob_id = blob_id
        self.base_url = f"{JSONBLOB_API_URL}/{self.blob_id}"
        print(f"Blob ID set to: {self.blob_id}")
