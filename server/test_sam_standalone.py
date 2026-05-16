import sys
import os
import torch
import numpy as np
from PIL import Image

# Add paths
sys.path.append('/Users/trohith/Documents/CAPSATONE PROJECT/drilldown-app/server')
sys.path.append('/Users/trohith/Documents/CAPSATONE PROJECT/sam2-test/sam2')

from app.services.sam2_service import SAM2Service

def test_sam2():
    print("Starting SAM2 Test...")
    # Use a real image if available, or create a dummy one
    image_path = "test_input.png"
    Image.new('RGB', (512, 512), (100, 150, 200)).save(image_path)
    
    output_path = "test_output.png"
    
    try:
        print("Calling segment_object...")
        result = SAM2Service.segment_object(image_path, 0.5, 0.5, output_path)
        print(f"Success! Result: {result}")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sam2()
