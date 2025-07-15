import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import matplotlib.lines as mlines

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 8)
ax.axis('off')

# Define colors
aws_color = '#FF9900'
ray_color = '#2196F3'
storage_color = '#4CAF50'
monitor_color = '#9C27B0'

# Title
ax.text(5, 7.5, 'Memory-Optimized RL System Architecture', 
        ha='center', va='center', fontsize=16, fontweight='bold')

# AWS EC2 Instance Box (main container)
aws_box = FancyBboxPatch((0.5, 1), 9, 5.5, 
                          boxstyle="round,pad=0.1",
                          facecolor='#FFF3E0',
                          edgecolor=aws_color,
                          linewidth=2,
                          linestyle='--')
ax.add_patch(aws_box)
ax.text(0.8, 6.2, 'AWS EC2 r7i.48xlarge (1.5TB RAM)', 
        fontsize=10, style='italic', color=aws_color)

# Ray Head Node
head_node = FancyBboxPatch((1, 4.5), 3, 1.5,
                           boxstyle="round,pad=0.05",
                           facecolor='#E3F2FD',
                           edgecolor=ray_color,
                           linewidth=2)
ax.add_patch(head_node)
ax.text(2.5, 5.25, 'Ray Head Node', ha='center', va='center', fontweight='bold')
ax.text(2.5, 4.85, 'Learner Process', ha='center', va='center', fontsize=9)

# Actor Workers (3 boxes to represent many)
actor_y = 2.5
for i in range(3):
    actor_x = 1 + i * 2.5
    actor = FancyBboxPatch((actor_x, actor_y), 2, 1.2,
                           boxstyle="round,pad=0.05",
                           facecolor='#E8F5E9',
                           edgecolor=ray_color,
                           linewidth=1.5)
    ax.add_patch(actor)
    ax.text(actor_x + 1, actor_y + 0.6, f'Actor {i+1}', 
            ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(actor_x + 1, actor_y + 0.3, '1.08GB RAM', 
            ha='center', va='center', fontsize=8, color='green')
    
    # Arrow from head to actor
    arrow = ConnectionPatch((2.5, 4.5), (actor_x + 1, actor_y + 1.2),
                           "data", "data",
                           arrowstyle="->",
                           shrinkA=5, shrinkB=5,
                           mutation_scale=20,
                           fc=ray_color,
                           alpha=0.6)
    ax.add_patch(arrow)

# Add ellipsis for more actors
ax.text(7.5, actor_y + 0.6, '...', ha='center', va='center', 
        fontsize=16, fontweight='bold')
ax.text(8.2, actor_y + 0.6, '60 actors', ha='center', va='center', 
        fontsize=9, style='italic')

# Memory Monitor
monitor = FancyBboxPatch((6.5, 4.5), 2.5, 1.5,
                        boxstyle="round,pad=0.05",
                        facecolor='#F3E5F5',
                        edgecolor=monitor_color,
                        linewidth=2)
ax.add_patch(monitor)
ax.text(7.75, 5.25, 'memray', ha='center', va='center', fontweight='bold')
ax.text(7.75, 4.85, 'Memory Profiler', ha='center', va='center', fontsize=9)

# S3 Storage (outside main box)
s3_box = FancyBboxPatch((0.5, 0.1), 4, 0.8,
                        boxstyle="round,pad=0.05",
                        facecolor='#E8F5E9',
                        edgecolor=storage_color,
                        linewidth=2)
ax.add_patch(s3_box)
ax.text(2.5, 0.5, 'Amazon S3 Storage', ha='center', va='center', fontweight='bold')
ax.text(2.5, 0.2, 'Checkpoints & Results', ha='center', va='center', fontsize=8)

# Local Development
local_box = FancyBboxPatch((5.5, 0.1), 4, 0.8,
                           boxstyle="round,pad=0.05",
                           facecolor='#FFF3E0',
                           edgecolor='#795548',
                           linewidth=2)
ax.add_patch(local_box)
ax.text(7.5, 0.5, 'Local Development', ha='center', va='center', fontweight='bold')
ax.text(7.5, 0.2, 'Analysis & Visualization', ha='center', va='center', fontsize=8)

# Arrows
# Head to S3
arrow_s3 = ConnectionPatch((2.5, 4.5), (2.5, 0.9),
                          "data", "data",
                          arrowstyle="<->",
                          shrinkA=5, shrinkB=5,
                          mutation_scale=20,
                          fc=storage_color,
                          alpha=0.6)
ax.add_patch(arrow_s3)
ax.text(2.8, 2.7, 'Checkpoints', ha='left', va='center', fontsize=8, rotation=-90)

# S3 to Local
arrow_local = ConnectionPatch((4.5, 0.5), (5.5, 0.5),
                             "data", "data",
                             arrowstyle="->",
                             shrinkA=5, shrinkB=5,
                             mutation_scale=20,
                             fc='#795548',
                             alpha=0.6)
ax.add_patch(arrow_local)
ax.text(5, 0.3, 'Download', ha='center', va='center', fontsize=8)

# Key innovations box
key_box = FancyBboxPatch((0.2, 7), 3, 0.8,
                        boxstyle="round,pad=0.05",
                        facecolor='#FFEBEE',
                        edgecolor='#F44336',
                        linewidth=1)
ax.add_patch(key_box)
ax.text(1.7, 7.6, 'Key Innovation:', ha='center', va='center', fontsize=9, fontweight='bold')
ax.text(1.7, 7.3, '95% Memory Reduction', ha='center', va='center', fontsize=8)

# Save as both PNG and PDF
plt.tight_layout()
output_path = 'patents/figures/FIG-1_system_overview'
plt.savefig(f'{output_path}.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.savefig(f'{output_path}.pdf', dpi=300, bbox_inches='tight', facecolor='white')
print(f"✓ Created {output_path}.png and {output_path}.pdf")

plt.close()