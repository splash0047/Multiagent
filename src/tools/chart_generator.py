"""
KEEP v2 — Chart Generator Tool

Executes LLM-generated Python plotting code (matplotlib/seaborn).
Captures the output image and converts it to a Base64 string for 
embedding directly into Markdown/HTML.
"""

import os
import base64
import tempfile
import uuid
from typing import Optional

from src.utils.logger import get_logger

log = get_logger("ChartGenerator")

def generate_chart_base64(python_code: str) -> Optional[str]:
    """
    Executes Python plotting code in a sandboxed-ish environment.
    The code is expected to generate a plot and save it to a filename
    we inject into the environment.
    
    Returns the base64 encoded string of the PNG image, or None if it fails.
    """
    # Create a temporary file path for the output image
    temp_dir = tempfile.gettempdir()
    output_filename = os.path.join(temp_dir, f"chart_{uuid.uuid4().hex}.png")
    
    # We provide a safe global dictionary. We inject the target output path.
    # The LLM should be instructed to save the figure to `OUTPUT_PATH`.
    global_env = {
        "OUTPUT_PATH": output_filename,
        "__builtins__": __builtins__
    }
    
    try:
        # Pre-process the code slightly to ensure it doesn't call plt.show()
        # which would block the execution, and enforce saving to OUTPUT_PATH if not done.
        clean_code = python_code.replace("plt.show()", "")
        
        # If the LLM forgot to use OUTPUT_PATH, we append it
        if "OUTPUT_PATH" not in clean_code and "savefig" not in clean_code:
            clean_code += "\nimport matplotlib.pyplot as plt\nplt.savefig(OUTPUT_PATH, bbox_inches='tight')\n"
        elif "savefig" in clean_code and "OUTPUT_PATH" not in clean_code:
            # It saved to some random file, we try to intercept or just hope it used OUTPUT_PATH
            pass 
        
        log.info("Executing chart generation code...")
        exec(clean_code, global_env)
        
        # Check if the file was created
        if not os.path.exists(output_filename):
            # Maybe the LLM hardcoded a filename like 'chart.png'
            # Let's check the current directory just in case
            possible_files = ["chart.png", "plot.png", "output.png"]
            for pf in possible_files:
                if os.path.exists(pf):
                    output_filename = pf
                    break
            else:
                log.error("Chart execution succeeded, but no output file was found.")
                return None
                
        # Read the image and convert to base64
        with open(output_filename, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            
        log.info("Chart generated and converted to Base64 successfully.")
        return encoded_string
        
    except Exception as e:
        log.error(f"Failed to generate chart: {e}")
        return None
        
    finally:
        # Cleanup the temporary file
        if os.path.exists(output_filename):
            try:
                os.remove(output_filename)
            except OSError:
                pass
