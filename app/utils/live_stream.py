# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import requests


# API Communication
def send_api_request(FASTAPI_URL, endpoint: str):
    try:
        response = requests.post(f"{FASTAPI_URL}{endpoint}")
        return response.json().get("message", "Unknown response")
    except requests.exceptions.RequestException:
        return "Error: Could not reach API server."


def fetch_cameras(pi_api_url):
    """Fetch camera data from pi

    Args:
        pi_api_url (_type_): live stream api ruinig on pi
    """
    try:
        response = requests.get(f"{pi_api_url}/camera_infos")
        response.raise_for_status()
        data = response.json()
        cameras = {}
        for cam in data.get("cameras", []):
            name = cam.get("name", f"Camera {cam.get('id')}")
            if name:
                cameras[name] = {
                    "ip": cam.get("ip"),
                    "poses": cam.get("poses", []),
                    "azimuths": cam.get("azimuths", []),
                }
        return cameras
    except Exception as e:
        print(f"Error fetching cameras: {e}")
        return {}


def find_closest_camera_pose(target_azimuth, pi_cameras):
    closest_info = None
    min_abs_diff = float("inf")
    signed_shift = 0

    for cam_name, cam_data in pi_cameras.items():
        ip = cam_data["ip"]
        azimuths = cam_data["azimuths"]
        poses = cam_data["poses"]

        for pose_id, az in zip(poses, azimuths, strict=True):
            raw_diff = (target_azimuth - az + 540) % 360 - 180
            abs_diff = abs(raw_diff)

            if abs_diff < min_abs_diff:
                min_abs_diff = abs_diff
                signed_shift = raw_diff
                closest_info = {
                    "name": cam_name,
                    "ip": ip,
                    "azimuth": az,
                    "pose_id": pose_id,
                    "azimuths": azimuths,
                    "poses": poses,
                }

    return closest_info, signed_shift
