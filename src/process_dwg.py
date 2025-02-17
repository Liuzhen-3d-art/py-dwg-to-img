import os
import subprocess
import xml.etree.ElementTree as ET
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout, config

# Binary paths
ODA_EXE_PATH = r"src/modules/ODAFileConverter-v25.12.0/ODAFileConverter.exe"
INKSCAPE_EXE_PATH = "src/modules/Inkscape/bin/inkscape.exe"

def extract_png(input_file: str):
    """
    Convert a DWG file to PNG format and store in the same directory 
    
    - prints step error & returns False if failure occurs
    - else returns True
    """
    # Convert DWG to DXF
    input_file = input_file.replace("\\", "/").split("/")
    working_dir = "/".join(input_file[:-1])
    input_file = input_file[-1]

    output_version = "ACAD2018"
    output_format = "dxf"
    oda_exe_path = ODA_EXE_PATH.replace("/", "\\")
    recursive = True
    audit = True
    recursive = "1" if recursive else "0"
    audit = "1" if audit else "0"

    try:
        subprocess.run(
            args=[oda_exe_path, working_dir, working_dir, output_version, output_format, recursive, audit, input_file],
            shell=True
        )
    except Exception as e:
        print(f"DWG to DXF error : {e}")
        return False

    # Convert dxf to svg
    try:
        doc = ezdxf.readfile(f"{working_dir}/{input_file.replace('.dwg', '.dxf')}")
        msp = doc.modelspace()
        context = RenderContext(doc)

        class CustomSVGBackend(svg.SVGBackend):
            def draw_entity(self, entity):
                if hasattr(entity, 'pattern'):
                    pattern = entity.pattern
                    pattern_id = f"pattern_{id(entity)}"
                    svg_pattern = ET.Element('pattern', id=pattern_id, width="10", height="10", patternUnits="userSpaceOnUse")
                    line = ET.SubElement(svg_pattern, 'line', x1="0", y1="0", x2="10", y2="10", stroke="black", stroke_width="1")
                    self.svg.root.append(svg_pattern)
                    fill = f'url(#{pattern_id})'
                    entity.set_fill(fill)
                super().draw_entity(entity)

        backend = CustomSVGBackend()
        cfg = config.Configuration(
            color_policy=config.ColorPolicy.BYLAYER,
            text_policy=config.TextPolicy.FILLING,
            hatching_timeout=120,
        )
        frontend = Frontend(context, backend, cfg)
        frontend.draw_layout(msp)

        page = layout.Page(
            width=0,
            height=0,
            units=layout.Units.mm,
            margins=layout.Margins.all(10),
            max_width=1800,
        )
        svg_string = backend.get_string(
            page=page,
            settings=layout.Settings(
                scale=4,
                fit_page=True,
                page_alignment=layout.PageAlignment.MIDDLE_CENTER,
                crop_at_margins=True,
            ),
        )
    except Exception as e:
        print(f"DXF to SVG error : {e}")
        return False

    output_path = f"{working_dir}/{input_file.replace('.dwg', '.svg')}"
    with open(output_path, "wt", encoding="utf8") as fp:
        fp.write(svg_string)

    # Convert SVG file to PNG with Inkscape
    try:
        ET.parse(output_path)
    except Exception as e:
        print(f"SVG parsing error : {e}")
        return False

    try:
        subprocess.check_call([INKSCAPE_EXE_PATH, '--export-type=png', output_path])
    except Exception as e:
        print(f"Inkscape binary error : {e}")
        return False

    # Clean up temp files
    os.remove(output_path.replace(".svg", ".dxf"))
    os.remove(output_path)

    return True
