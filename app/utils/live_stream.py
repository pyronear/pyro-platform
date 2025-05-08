import requests



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
    min_diff = float("inf")

    for cam_name, cam_data in pi_cameras.items():
        ip = cam_data["ip"]
        for pose_id, az in zip(cam_data["poses"], cam_data["azimuths"]):
            diff = min(abs(az - target_azimuth), 360 - abs(az - target_azimuth))  # circular difference
            if diff < min_diff:
                min_diff = diff
                closest_info = {
                    "camera": cam_name,
                    "ip": ip,
                    "azimuth": az,
                    "pose": pose_id,
                }

    return closest_info
