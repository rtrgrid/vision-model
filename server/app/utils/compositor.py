from PIL import Image, ImageDraw, ImageEnhance
import os

class ImageCompositor:
    @staticmethod
    def draw_spotlight(image_path: str, x: float, y: float, output_path: str, radius: int = 150, brightness: float = 0.2):
        """
        Spotlight effect for focused Vision AI attention.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found: {image_path}")

        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            width, height = img.size
            cx, cy = int(x * width), int(y * height)
            
            enhancer = ImageEnhance.Brightness(img)
            dimmed = enhancer.enhance(brightness)
            
            mask = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(mask)
            
            for r in range(radius, 0, -1):
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=255)

            result = Image.composite(img, dimmed, mask)
            result.save(output_path, "PNG")
        
        return output_path

    @staticmethod
    def draw_red_ring(image_path: str, x: float, y: float, output_path: str, thickness: int = 3):
        """
        Draws a resolution-aware red ring with a center dot.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found: {image_path}")

        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            width, height = img.size
            cx, cy = int(x * width), int(y * height)
            
            # Dynamic Radius Logic: 2% of image width, clamped between 15 and 100
            radius = max(15, min(100, width // 50))
            
            draw = ImageDraw.Draw(img)
            
            # 1. Draw Ring
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline="red", width=thickness)
            
            # 2. Draw Center Dot
            dot_r = thickness * 2
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill="red")
            
            img.save(output_path, "PNG")
        
        return output_path

    @staticmethod
    def draw_crosshairs(image_path: str, x: float, y: float, output_path: str, color="red", thickness: int = 2):
        """
        Draws vertical and horizontal lines intersecting at (x, y).
        Best for models like Qwen2-VL.
        """
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            width, height = img.size
            cx, cy = int(x * width), int(y * height)
            
            draw = ImageDraw.Draw(img)
            
            # Horizontal line
            draw.line([(0, cy), (width, cy)], fill=color, width=thickness)
            # Vertical line
            draw.line([(cx, 0), (cx, height)], fill=color, width=thickness)
            
            img.save(output_path, "PNG")
        return output_path

    @staticmethod
    def draw_glow(image_path: str, x: float, y: float, output_path: str):
        """
        Creates a soft semi-transparent red radial glow at the click point.
        """
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            width, height = img.size
            cx, cy = int(x * width), int(y * height)
            radius = max(30, width // 20) # Glow is larger than the ring
            
            # Create a red overlay with alpha
            overlay = Image.new('RGBA', img.size, (255, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Draw feathered radial circles
            for r in range(radius, 0, -2):
                alpha = int(100 * (1 - (r / radius))) # Max 100 alpha (semi-transparent)
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 0, 0, alpha))
            
            # Composite overlay with original image
            img.paste(overlay, (0, 0), overlay)
            img.save(output_path, "PNG")
        return output_path
