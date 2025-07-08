# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import logging_config
import requests

import config as cfg

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


# FOV based on zoom input
def fov_zoom(z):
    if z == 0:
        return 54.2
    return 55.59044 - 2.00815 * z + 0.01886 * z**2


# API Communication
def send_api_request(FASTAPI_URL, endpoint: str):
    try:
        response = requests.post(f"{FASTAPI_URL}{endpoint}")
        return response.json().get("message", "Unknown response")
    except requests.exceptions.RequestException:
        return "Error: Could not reach API server."


def minimal_angle_diff(a, b):
    """Compute the minimal signed angular difference between two azimuths."""
    diff = (a - b) % 360
    if diff > 180:
        diff -= 360
    return diff


def find_closest_camera_pose(target_azimuth, pi_cameras):
    closest_info = None
    min_abs_diff = float("inf")
    signed_shift = 0

    for cam_name, cam_data in pi_cameras.items():
        ip = cam_data.get("ip")
        azimuths = cam_data.get("azimuths", [])
        poses = cam_data.get("poses", [])

        # Skip cameras with missing or mismatched data
        if not azimuths or not poses or len(azimuths) != len(poses):
            continue

        for pose_id, az in zip(poses, azimuths, strict=True):
            # Ensure numeric comparison with float conversion
            try:
                az = float(az)
                target = float(target_azimuth)
            except (ValueError, TypeError):
                continue

            raw_diff = minimal_angle_diff(target, az)
            abs_diff = abs(raw_diff)

            logger.debug(
                f"[find_closest_camera_pose] Checking cam '{cam_name}', pose {pose_id}, azimuth={az:.2f}, "
                f"target={target:.2f}, raw_diff={raw_diff:.2f}, abs_diff={abs_diff:.2f}"
            )

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

                # Early exit if perfect match
                if abs_diff == 0:
                    break

    if closest_info is None:
        logger.warning("[find_closest_camera_pose] No valid camera found")
        return None, 0

    return closest_info, signed_shift
