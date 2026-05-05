import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

def get_font_path():
    font_path = os.path.join(os.path.expanduser("~"), "Desktop", "PRO부동산_자동화_로컬최종본", "assets", "malgunbd.ttf")
    if not os.path.exists(font_path):
        # Fallback to Apple SD Gothic Neo on Mac if malgunbd.ttf is not found
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    return font_path

def stitch_law_text_to_image(base_img_path, law_text, output_path):
    """
    Appends a legal warning text section to the bottom of the existing property card image.
    """
    try:
        if not os.path.exists(base_img_path):
            return False
            
        base_img = Image.open(base_img_path)
        img_width, img_height = base_img.size
        
        # UI Margin and Constraints
        margin = 40
        text_width = img_width - (margin * 2)
        
        # Load fonts
        font_path = get_font_path()
        try:
            title_font = ImageFont.truetype(font_path, 40) # Title font
            text_font = ImageFont.truetype(font_path, 32)  # Body font
        except Exception:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            
        # Character wrap calculation based on approximate font width
        char_width_approx = 32 * 0.55
        chars_per_line = int(text_width / char_width_approx)
        
        wrapped_text = textwrap.wrap(law_text, width=chars_per_line)
        
        # Render settings
        title_text = "👨‍⚖️ [서프로의 실전 재개발 상식]"
        title_height = 50
        line_height = 42
        
        # Calculate final canvas dimensions
        text_bg_height = margin + title_height + 30 + (len(wrapped_text) * line_height) + margin
        
        # Create text canvas (light gray background)
        text_canvas = Image.new('RGB', (img_width, int(text_bg_height)), color='#F7F7F7')
        draw = ImageDraw.Draw(text_canvas)
        
        # Top border line for design
        draw.line([(0, 0), (img_width, 0)], fill='#E0E0E0', width=4)
        
        curr_y = margin
        # Draw Title in Red
        draw.text((margin, curr_y), title_text, font=title_font, fill='#D32F2F')
        curr_y += title_height + 30
        
        # Draw Body text
        for line in wrapped_text:
            draw.text((margin, curr_y), line, font=text_font, fill='#333333')
            curr_y += line_height
            
        # Stitch
        final_height = img_height + text_canvas.height
        stitched_img = Image.new('RGB', (img_width, final_height))
        stitched_img.paste(base_img, (0, 0))
        stitched_img.paste(text_canvas, (0, img_height))
        
        # Save updating the original or to new path
        stitched_img.save(output_path, quality=95)
        return True
        
    except Exception as e:
        print(f"Error in stitch_law_text_to_image: {e}")
        return False
