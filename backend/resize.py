from PIL import Image
import os

input_path = r"c:\programming_project\github\MemoryJournal\extension\assets\icon.png"
output_path = r"c:\programming_project\github\MemoryJournal\extension\assets\icon128.png"

with Image.open(input_path) as img:
    resized_img = img.resize((128, 128), Image.Resampling.LANCZOS)
    resized_img.save(output_path)
    print(f"Resized image saved to {output_path}")
