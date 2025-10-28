#!/usr/bin/env python3
"""
Visualize the kinematic tree structure from the MuJoCo XML file.
Creates a comprehensive single-figure visualization with multiple layout options and ASCII tree.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import Dict, List, Tuple, Optional
import numpy as np

# Removed plotly imports - focusing on PNG outputs only

try:
    from treelib import Tree
    TREELIB_AVAILABLE = True
except ImportError:
    TREELIB_AVAILABLE = False


class KinematicTreeVisualizer:
    """Visualize kinematic tree structure from MuJoCo XML."""
    
    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        self.graph = nx.DiGraph()
        self.body_data = {}
        self.positions = {}
        
    def extract_tree_structure(self):
        """Extract the hierarchical structure from XML."""
        worldbody = self.root.find('worldbody')
        if worldbody is None:
            raise ValueError("No worldbody found in XML")
            
        # Find the pelvis as the root body
        pelvis = worldbody.find('.//body[@name="pelvis"]')
        if pelvis is not None:
            self._process_body_recursive(pelvis, None, "WORLDBODY")
            
    def _process_body_recursive(self, body_elem, parent_name: Optional[str], grandparent_name: str):
        """Recursively process body elements and build graph."""
        name = body_elem.get('name')
        if not name:
            return
            
        # Extract body information
        inertial = body_elem.find('inertial')
        mass = float(inertial.get('mass', '0')) if inertial is not None else 0
        
        pos = body_elem.get('pos', '0 0 0').split()
        position = [float(p) for p in pos]
        
        joints = body_elem.findall('joint')
        joint_count = len(joints)
        joint_names = [j.get('name', 'unnamed') for j in joints]
        
        geoms = body_elem.findall('geom[@type="mesh"]')
        mesh_count = len(geoms)
        
        # Store body data
        self.body_data[name] = {
            'mass': mass,
            'position': position,
            'joint_count': joint_count,
            'joint_names': joint_names,
            'mesh_count': mesh_count,
            'parent': parent_name or grandparent_name
        }
        
        # Add to graph
        if parent_name:
            self.graph.add_edge(parent_name, name)
        else:
            self.graph.add_edge(grandparent_name, name)
            
        # Process children
        children = body_elem.findall('body')
        for child in children:
            self._process_body_recursive(child, name, grandparent_name)
            
    def create_comprehensive_visualization(self, save_path: str = None):
        """Create a comprehensive visualization showing multiple layouts in one figure."""
        if not self.graph.nodes:
            self.extract_tree_structure()
            
        # Set default save path if not provided
        if save_path is None:
            save_path = self.xml_path.parent / "kinematic_tree_comprehensive.png"
            
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(24, 20))
        fig.suptitle("🦴 Humanoid Kinematic Tree - Multiple Layout Views", 
                    fontsize=20, fontweight='bold', y=0.95)
        
        layouts = [
            ("hierarchical", "Hierarchical Layout", axes[0, 0]),
            ("anatomical", "Anatomical Layout", axes[0, 1]), 
            ("spring", "Spring Layout", axes[1, 0]),
            ("circular", "Circular Layout", axes[1, 1])
        ]
        
        # Color nodes by body region (consistent across all plots)
        node_colors = self._get_node_colors()
        
        for layout_name, title, ax in layouts:
            # Set current axes
            plt.sca(ax)
            
            # Get layout positions
            if layout_name == "hierarchical":
                pos = self._create_hierarchical_layout()
            elif layout_name == "spring":
                pos = nx.spring_layout(self.graph, k=3, iterations=50)
            elif layout_name == "circular":
                pos = nx.circular_layout(self.graph)
            elif layout_name == "anatomical":
                pos = self._create_anatomical_layout()
            else:
                pos = nx.spring_layout(self.graph)
                
            # Draw edges
            nx.draw_networkx_edges(self.graph, pos, edge_color='gray', 
                                  arrows=True, arrowsize=15, alpha=0.6, ax=ax)
            
            # Draw nodes
            nx.draw_networkx_nodes(self.graph, pos, node_color=node_colors, 
                                  node_size=800, alpha=0.8, ax=ax)
            
            # Add labels (simplified for better readability in subplots)
            labels = {}
            for node in self.graph.nodes():
                if node in self.body_data:
                    joint_count = self.body_data[node]['joint_count']
                    if layout_name == "anatomical":
                        # More detailed labels for anatomical view
                        mass = self.body_data[node]['mass']
                        labels[node] = f"{node}\n({joint_count}J, {mass:.1f}kg)"
                    else:
                        # Simpler labels for other views
                        labels[node] = f"{node}\n({joint_count}J)"
                else:
                    labels[node] = node
                    
            nx.draw_networkx_labels(self.graph, pos, labels, font_size=6, 
                                   font_weight='bold', ax=ax)
            
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
            ax.axis('off')
        
        # Add a single legend for the entire figure
        legend_elements = [
            patches.Patch(color='#FF8C00', label='Head'),
            patches.Patch(color='#4169E1', label='Torso/Spine'),
            patches.Patch(color='#32CD32', label='Arms'),
            patches.Patch(color='#DC143C', label='Legs'),
            patches.Patch(color='#808080', label='Other')
        ]
        fig.legend(handles=legend_elements, loc='lower center', 
                  bbox_to_anchor=(0.5, 0.02), ncol=5, fontsize=12)
        
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])  # Leave space for suptitle and legend
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ Comprehensive tree visualization saved to: {save_path}")
        
    def _create_hierarchical_layout(self) -> Dict[str, Tuple[float, float]]:
        """Create a hierarchical layout for the tree."""
        pos = {}
        levels = {}
        
        # Calculate levels (depth) for each node
        def calculate_level(node, level=0):
            levels[node] = level
            for successor in self.graph.successors(node):
                calculate_level(successor, level + 1)
                
        # Start from root
        roots = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        for root in roots:
            calculate_level(root)
            
        # Group nodes by level
        level_groups = {}
        for node, level in levels.items():
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(node)
            
        # Position nodes
        max_width = max(len(group) for group in level_groups.values())
        
        for level, nodes in level_groups.items():
            y = -level * 2  # Vertical spacing
            width = len(nodes)
            
            for i, node in enumerate(nodes):
                if width == 1:
                    x = 0
                else:
                    x = (i - (width - 1) / 2) * (max_width / width) * 3
                pos[node] = (x, y)
                
        return pos
        
    def _create_anatomical_layout(self) -> Dict[str, Tuple[float, float]]:
        """Create an anatomical layout mimicking human body structure."""
        pos = {}
        
        # Define approximate anatomical positions (x, y coordinates)
        anatomical_positions = {
            'WORLDBODY': (0, -8),
            'pelvis': (0, 0),
            
            # Torso and head
            'torso': (0, 3),
            'head': (0, 6),
            
            # Right leg (viewer's left)
            'femur_r': (-1, -2),
            'tibia_r': (-1, -4), 
            'talus_r': (-1, -6),
            'calcn_r': (-1, -7),
            'toes_r': (-1, -8),
            
            # Left leg (viewer's right)
            'femur_l': (1, -2),
            'tibia_l': (1, -4),
            'talus_l': (1, -6), 
            'calcn_l': (1, -7),
            'toes_l': (1, -8),
            
            # Right arm (viewer's left)
            'humerus_r': (-3, 2),
            'ulna_r': (-5, 1),
            'radius_r': (-5, 0),
            'hand_r': (-6, -1),
            
            # Left arm (viewer's right)
            'humerus_l': (3, 2),
            'ulna_l': (5, 1), 
            'radius_l': (5, 0),
            'hand_l': (6, -1),
        }
        
        # Assign positions, with fallback for any missing nodes
        for node in self.graph.nodes():
            if node in anatomical_positions:
                pos[node] = anatomical_positions[node]
            else:
                # Fallback to hierarchical layout for any missing nodes
                pos[node] = (0, 0)
                
        return pos
        
    def _get_node_colors(self) -> List[str]:
        """Assign colors based on body regions."""
        colors = []
        for node in self.graph.nodes():
            if 'head' in node.lower() or 'skull' in node.lower():
                colors.append('#FF8C00')  # Orange for head
            elif any(part in node.lower() for part in ['torso', 'pelvis', 'spine']):
                colors.append('#4169E1')  # Blue for torso/spine
            elif any(part in node.lower() for part in ['arm', 'hand', 'elbow', 'wrist', 'humerus', 'ulna', 'radius']):
                colors.append('#32CD32')  # Green for arms
            elif any(part in node.lower() for part in ['femur', 'tibia', 'foot', 'toe', 'leg', 'ankle', 'calcn', 'talus']):
                colors.append('#DC143C')  # Red for legs
            else:
                colors.append('#808080')  # Gray for others
        return colors
        
    # Removed interactive plotly visualization and individual layout methods - using comprehensive view
    def create_ascii_tree(self) -> str:
        """Create an ASCII art tree representation."""
        if not TREELIB_AVAILABLE:
            print("❌ treelib not available for ASCII trees. Install with: pip install treelib")
            return ""
            
        if not self.graph.nodes:
            self.extract_tree_structure()
            
        tree = Tree()
        
        # Add root
        roots = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        for root in roots:
            tree.create_node(root, root)
            
        # Add all other nodes
        def add_children(parent):
            for child in self.graph.successors(parent):
                if child in self.body_data:
                    data = self.body_data[child]
                    label = f"{child} ({data['joint_count']}J, {data['mass']:.1f}kg)"
                else:
                    label = child
                tree.create_node(label, child, parent=parent)
                add_children(child)
                
        for root in roots:
            add_children(root)
            
        return tree.show(stdout=False)
        
    def print_summary_statistics(self):
        """Print summary statistics about the kinematic tree."""
        if not self.graph.nodes:
            self.extract_tree_structure()
            
        print("\n" + "="*60)
        print("📊 KINEMATIC TREE STATISTICS")
        print("="*60)
        
        print(f"Total Bodies: {len(self.body_data)}")
        
        total_joints = sum(data['joint_count'] for data in self.body_data.values())
        print(f"Total Joints: {total_joints}")
        
        total_mass = sum(data['mass'] for data in self.body_data.values())
        print(f"Total Mass: {total_mass:.2f} kg")
        
        # Tree depth
        depths = {}
        def calculate_depth(node, depth=0):
            depths[node] = depth
            for child in self.graph.successors(node):
                calculate_depth(child, depth + 1)
                
        roots = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        for root in roots:
            calculate_depth(root)
            
        max_depth = max(depths.values()) if depths else 0
        print(f"Tree Depth: {max_depth}")
        
        # Branching factor
        branching_factors = [self.graph.out_degree(n) for n in self.graph.nodes()]
        avg_branching = np.mean(branching_factors)
        max_branching = max(branching_factors)
        print(f"Average Branching Factor: {avg_branching:.2f}")
        print(f"Maximum Branching Factor: {max_branching}")
        
        print("\n🏗️ BODY REGIONS:")
        regions = {
            'Head': ['head'],
            'Torso/Spine': ['torso', 'pelvis'],
            'Arms': ['humerus', 'ulna', 'radius', 'hand'],
            'Legs': ['femur', 'tibia', 'talus', 'calcn', 'toes']
        }
        
        for region, keywords in regions.items():
            count = sum(1 for name in self.body_data.keys() 
                       if any(kw in name.lower() for kw in keywords))
            print(f"{region}: {count} bodies")


def main():
    """Main function to create visualizations."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    xml_path = script_dir / "humanoid_muscle_rl.xml"
    
    print("🦴 Creating Kinematic Tree Visualizations...")
    
    # Check if XML file exists
    if not xml_path.exists():
        print(f"❌ Error: XML file not found at {xml_path}")
        print(f"   Make sure you have the humanoid_muscle_rl.xml file in the same directory as this script.")
        return
    
    visualizer = KinematicTreeVisualizer(xml_path)
    
    try:
        # 1. Extract structure
        visualizer.extract_tree_structure()
        
        # 2. Print statistics
        visualizer.print_summary_statistics()
        
        # 3. Create comprehensive visualization with all layouts
        print("\n📈 Creating comprehensive tree visualization...")
        visualizer.create_comprehensive_visualization()
            
        # 5. ASCII tree
        print("\n🌳 ASCII Tree Structure:")
        ascii_tree = visualizer.create_ascii_tree()
        if ascii_tree:
            print(ascii_tree)
            
        print("\n✅ All visualizations complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
