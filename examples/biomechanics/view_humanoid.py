#!/usr/bin/env python3
"""
Simple viewer for the complete humanoid model loaded from MJCF.
"""

import genesis as gs
from pathlib import Path

# Initialize Genesis
gs.init(backend=gs.cpu)

# Create scene with viewer
scene = gs.Scene(
    show_viewer=True,
    rigid_options=gs.options.RigidOptions(
        dt=0.01,
        enable_joint_limit=True,
        gravity=(0, 0, -9.8),
    ),
    viewer_options=gs.options.ViewerOptions(
        camera_pos=(3.0, -3.0, 2.0),
        camera_lookat=(0.0, 0.0, 1.0),
        camera_fov=40,
    ),
)

# Load humanoid from MJCF
xml_path = Path(__file__).parent / "reference/humanoid_muscle_rl.xml"
humanoid = scene.add_entity(
    gs.morphs.MJCF(file=str(xml_path)),
)

# Build
print("Building scene...")
scene.build()

print(f"\n✓ Model loaded: {len(humanoid.links)} links, {len(humanoid.joints)} joints, {humanoid.n_dofs} DOFs")
print("\nViewer running. Close window to exit.\n")

# Run viewer
scene.viewer.run()