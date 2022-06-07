
from pathlib import Path
import json

from .usd import data2usd_ascii, data2usdz
from .gltf import data2gltf
from .common import data2obj


def export(input, data_path, format_list, out=None, check=False):
    data_path = Path(data_path)
    out_name_generated = False
    for format in format_list:
        if out is None or out_name_generated:
            out_name_generated = True
            if data_path.name.endswith('.'):
                data_path = data_path.parent / data_path.name[:-1]
            out = data_path.with_suffix("."+format)
        print(f"Generating format {format} in file {out}")
        mode = 'wb' if format.startswith("usd") or format == 'glb' else 'w'
        with open(out, mode) as outfile:
            if format == 'gltf':
                result = data2gltf(input).format_gltf()
                json.dump(result, outfile)
            elif format == 'glb':
                result = data2gltf(input).format_glb()
                outfile.write(result)
            elif format == 'obj':
                result = data2obj(input)
                outfile.write(result)
            elif format == 'usda':
                usda, assets = data2usd_ascii(input)
                outfile.write(usda.encode("utf-8"))
                for key, val in assets.items():
                    with open(key, 'wb') as f:
                        f.write(val)
            elif format == 'html':
                glb = data2gltf(input).format_glb()
                import base64
                buffer_url = "data:model/gltf-binary;base64," + base64.b64encode(glb).decode("ASCII")
                with open(Path(__file__).parent.parent / 'html/model.html') as f:
                    html = "\n".join(f.readlines())
                html = html.replace("data.glb", buffer_url)
                html = html.replace("js/third-party/model-viewer.min.js", "https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js")
                outfile.write(html)
            else:
                result = data2usdz(input, save_usda=False, check=check)
                outfile.write(result)
