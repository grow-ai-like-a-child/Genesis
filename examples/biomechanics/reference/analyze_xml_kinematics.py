#!/usr/bin/env python3
"""
Analyze the kinematic chain structure from the MuJoCo XML file.
This script extracts the complete skeletal hierarchy with positions, orientations, and joints.
"""

import xml.etree.ElementTree as ET
from pathlib import Path


def analyze_body_transforms(body_elem):
    """Extract position and orientation data from a body element."""
    pos = body_elem.get('pos', '0 0 0').split()
    quat = body_elem.get('quat', None)
    
    # Convert to floats for better formatting
    pos_floats = [float(p) for p in pos]
    
    result = {
        'position': pos_floats,
        'quaternion': quat.split() if quat else None
    }
    return result


def get_joint_info(body_elem):
    """Extract all joint information from a body."""
    joints = []
    joint_elements = body_elem.findall('joint')
    
    for joint in joint_elements:
        joint_data = {
            'name': joint.get('name'),
            'type': joint.get('type', 'hinge'),
            'axis': [float(x) for x in joint.get('axis', '0 0 1').split()],
            'pos': [float(x) for x in joint.get('pos', '0 0 0').split()],
            'range': joint.get('range'),
            'stiffness': joint.get('stiffness', '0'),
            'damping': joint.get('damping', '0')
        }
        joints.append(joint_data)
    
    return joints


def print_body_recursive(body_elem, level, parent_name):
    """Recursively print body hierarchy with detailed information."""
    indent = '  ' * level
    name = body_elem.get('name')
    
    # Get transform info
    transform = analyze_body_transforms(body_elem)
    joints = get_joint_info(body_elem)
    
    # Get mass from inertial
    inertial = body_elem.find('inertial')
    mass = float(inertial.get('mass', '0')) if inertial is not None else 0
    inertial_pos = inertial.get('pos', '0 0 0') if inertial is not None else '0 0 0'
    
    # Get meshes
    geoms = body_elem.findall('geom[@type="mesh"]')
    meshes = [geom.get('mesh', geom.get('name')) for geom in geoms]
    mesh_display = meshes[:3] + (['...'] if len(meshes) > 3 else [])
    
    # Print body header
    print(f'{indent}🏗️ BODY: {name.upper()}')
    print(f'{indent}├─ Parent: {parent_name}')
    print(f'{indent}├─ Mass: {mass:.3f} kg')
    print(f'{indent}├─ Position: [{transform["position"][0]:7.4f}, {transform["position"][1]:7.4f}, {transform["position"][2]:7.4f}]')
    
    if transform['quaternion']:
        quat = [float(q) for q in transform['quaternion']]
        print(f'{indent}├─ Quaternion: [{quat[0]:7.4f}, {quat[1]:7.4f}, {quat[2]:7.4f}, {quat[3]:7.4f}]')
    
    if inertial is not None and inertial_pos != '0 0 0':
        print(f'{indent}├─ COM offset: {inertial_pos}')
    
    print(f'{indent}├─ Meshes ({len(meshes)}): {mesh_display}')
    
    # Print joints
    if joints:
        print(f'{indent}└─ JOINTS ({len(joints)}):')
        for i, joint in enumerate(joints):
            is_last = (i == len(joints) - 1)
            joint_indent = f'{indent}   {"└─" if is_last else "├─"}'
            print(f'{joint_indent} {joint["name"]} [{joint["type"]}]')
            print(f'{indent}   {"   " if is_last else "│  "}   • Axis: [{joint["axis"][0]:6.3f}, {joint["axis"][1]:6.3f}, {joint["axis"][2]:6.3f}]')
            if joint["range"]:
                range_vals = [float(x) for x in joint["range"].split()]
                print(f'{indent}   {"   " if is_last else "│  "}   • Range: [{range_vals[0]:6.3f}, {range_vals[1]:6.3f}] rad')
            print(f'{indent}   {"   " if is_last else "│  "}   • Stiff: {joint["stiffness"]}, Damp: {joint["damping"]}')
    else:
        print(f'{indent}└─ No joints')
    
    print()
    
    # Process children
    children = body_elem.findall('body')
    for child in children:
        print_body_recursive(child, level + 1, name)


def analyze_kinematic_structure():
    """Analyze and print the complete kinematic structure."""
    
    # Load and parse XML (now in same directory)
    xml_path = Path('humanoid_muscle_rl.xml')
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    print('🦴 HUMANOID MUSCULOSKELETAL KINEMATIC CHAIN')
    print('=' * 80)
    print('📊 COORDINATE SYSTEM: X=Left/Right, Y=Forward/Back, Z=Up/Down')
    print('📐 UNITS: Position(m), Rotation(rad), Mass(kg)')
    print('🔄 QUATERNION FORMAT: [w, x, y, z] (scalar-first)')
    print('=' * 80)
    print()
    
    # Find worldbody and start analysis
    worldbody = root.find('worldbody')
    
    if worldbody is not None:
        # Start with pelvis (root body)
        pelvis = worldbody.find('.//body[@name="pelvis"]')
        if pelvis is not None:
            print_body_recursive(pelvis, 0, 'WORLDBODY')
    
    # Print summary
    print('=' * 80)
    print('📋 KINEMATIC CHAIN SUMMARY')
    print('=' * 80)
    
    # Count totals
    all_bodies = worldbody.findall('.//body') if worldbody else []
    all_joints = worldbody.findall('.//joint') if worldbody else []
    
    # Separate joint types
    free_joints = [j for j in all_joints if j.get('type') == 'free']
    hinge_joints = [j for j in all_joints if j.get('type') != 'free']
    
    total_dofs = len(hinge_joints) + (len(free_joints) * 6)
    
    print(f'📊 Bodies: {len(all_bodies)}')
    print(f'📊 Total Joints: {len(all_joints)}')
    print(f'   ├─ Free joints: {len(free_joints)} (6 DOF each)')
    print(f'   └─ Hinge joints: {len(hinge_joints)} (1 DOF each)')
    print(f'📊 Total DOFs: {total_dofs}')
    print()
    
    # Print joint list by body part
    print('🔗 JOINTS BY BODY REGION:')
    print('-' * 40)
    
    regions = {
        'Hip': ['hip_flexion_r', 'hip_adduction_r', 'hip_rotation_r', 'hip_flexion_l', 'hip_adduction_l', 'hip_rotation_l'],
        'Knee': ['knee_angle_r', 'knee_angle_l'],
        'Ankle': ['ankle_angle_r', 'subtalar_angle_r', 'ankle_angle_l', 'subtalar_angle_l'],
        'Toes': ['mtp_angle_r', 'mtp_angle_l'],
        'Spine': ['lumbar_extension', 'lumbar_bending', 'lumbar_rotation'],
        'Neck': ['neck_extension', 'neck_bending', 'neck_rotation'],
        'Shoulder': ['arm_flex_r', 'arm_add_r', 'arm_rot_r', 'arm_flex_l', 'arm_add_l', 'arm_rot_l'],
        'Elbow': ['elbow_flex_r', 'elbow_flex_l'],
        'Forearm': ['pro_sup_r', 'pro_sup_l'],
        'Wrist': ['wrist_flex_r', 'wrist_dev_r', 'wrist_flex_l', 'wrist_dev_l']
    }
    
    for region, joint_names in regions.items():
        existing_joints = [j.get('name') for j in all_joints if j.get('name') in joint_names]
        if existing_joints:
            print(f'{region:12}: {len(existing_joints):2d} joints - {existing_joints}')
    
    print()
    print('🎯 KEY OBSERVATIONS:')
    print('-' * 40)
    print(f'• Root body (pelvis) has quaternion rotation: 0.707107 0.707107 0 0')
    print(f'• This represents a 45° rotation around the X-axis')
    print(f'• Each leg has {len([j for j in hinge_joints if "_r" in j.get("name", "") and ("hip_" in j.get("name", "") or "knee_" in j.get("name", "") or "ankle_" in j.get("name", "") or "mtp_" in j.get("name", ""))])} DOFs')
    print(f'• Arms have complex joint axes (not simple X/Y/Z)')
    print('• Hand models contain detailed mesh files for each finger bone')


if __name__ == '__main__':
    analyze_kinematic_structure()
