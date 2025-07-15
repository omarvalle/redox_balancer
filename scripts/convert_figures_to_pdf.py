import matplotlib.pyplot as plt
from PIL import Image
import os

# Convert existing PNGs to PDFs
figures_dir = "patents/figures"

# Convert FIG-2 and FIG-3 to PDF
for fig_num in [2, 3]:
    png_path = f"{figures_dir}/FIG-{fig_num}_*.png"
    
    # Find the actual filename
    import glob
    png_files = glob.glob(png_path)
    if png_files:
        png_file = png_files[0]
        pdf_file = png_file.replace('.png', '.pdf')
        
        # Open and save as PDF
        img = Image.open(png_file)
        img.save(pdf_file, "PDF", resolution=300.0)
        print(f"✓ Converted {png_file} to {pdf_file}")

print("\nAll figures converted to PDF format!")