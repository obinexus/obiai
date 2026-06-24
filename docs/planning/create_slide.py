import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
import matplotlib.patches as patches

# Set the style to a clean, modern look
plt.style.use('seaborn-v0_8-whitegrid')

# Create figure
fig = plt.figure(figsize=(12, 8))
gs = GridSpec(2, 2, figure=fig, width_ratios=[1, 1], height_ratios=[1, 1.2], wspace=0.3, hspace=0.4)

# Title for the entire slide
fig.suptitle('UNBIASED AI: The Critical Numbers', fontsize=24, fontweight='bold', y=0.98)

# ---- First chart: Misdiagnosis rates ----
ax1 = fig.add_subplot(gs[0, 0])

labels = ['Current AI', 'With Our Solution']
values = [35, 5]  # percentages
colors = ['#ff6961', '#77dd77']
  
x = np.arange(len(labels))
width = 0.6

bars = ax1.bar(x, values, width, color=colors)
ax1.set_ylim(0, 40)
ax1.set_ylabel('Misdiagnosis Rate (%)', fontsize=12)
ax1.set_title('Misdiagnosis Rates', fontsize=16, pad=15)
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=11)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
            f'{height}%', ha='center', va='bottom', fontsize=14, fontweight='bold')

# ---- Second chart: Market Size ----
ax2 = fig.add_subplot(gs[0, 1])

years = [2023, 2025, 2027, 2030]
market_size = [62, 90, 130, 188]  # billions
    
ax2.plot(years, market_size, marker='o', markersize=10, linewidth=3, color='#3a86ff')
ax2.set_ylabel('Market Size ($ Billions)', fontsize=12)
ax2.set_title('Healthcare AI Market Growth', fontsize=16, pad=15)
ax2.grid(True, linestyle='--', alpha=0.7)

# Annotate the final value
ax2.annotate(f'${market_size[-1]}B', 
            xy=(years[-1], market_size[-1]),
            xytext=(years[-1]-1, market_size[-1]+20),
            fontsize=14,
            fontweight='bold',
            arrowprops=dict(arrowstyle='->'))

# ---- Third element: Key Statistics ----
ax3 = fig.add_subplot(gs[1, :])
ax3.axis('off')

# Create a subtle background for the stats section
rect = patches.Rectangle((0.05, 0.05), 0.9, 0.9, linewidth=1, 
                         edgecolor='#dddddd', facecolor='#f8f8f8', alpha=0.5)
ax3.add_patch(rect)

# Add title for the stats section
ax3.text(0.5, 0.85, 'WHY THIS MATTERS', ha='center', fontsize=16, fontweight='bold')

# Stats to highlight
stats = [
    "47% of healthcare executives cite bias concerns as barrier to AI adoption",
    "85% gross margin on our technology solution",
    "$136 million - average cost of bias-related class action lawsuits",
    "94% of AI datasets lack demographic diversity representation"
]

# Add key stats text
y_pos = 0.7
for stat in stats:
    ax3.text(0.1, y_pos, "•", ha='left', va='center', fontsize=20, color='#3a86ff', fontweight='bold')
    ax3.text(0.15, y_pos, stat, ha='left', va='center', fontsize=14)
    y_pos -= 0.15

# Add a callout box for ROI
roi_box = patches.FancyBboxPatch((0.65, 0.35), 0.25, 0.2, boxstyle=patches.BoxStyle("Round", pad=0.02),
                              facecolor='#3a86ff', alpha=0.1, edgecolor='#3a86ff', linewidth=2)
ax3.add_patch(roi_box)
ax3.text(0.775, 0.45, "250%", ha='center', va='center', fontsize=24, fontweight='bold', color='#3a86ff')
ax3.text(0.775, 0.38, "3-Year ROI", ha='center', va='center', fontsize=14)

# Add OBINexus Computing logo placement
ax3.text(0.05, 0.05, "OBINexus Computing", fontsize=10, color='#666666')

# Save the figure
plt.savefig('unbiased_ai_stats_slide.png', dpi=300, bbox_inches='tight')
print("Slide created successfully as 'unbiased_ai_stats_slide.png'")
