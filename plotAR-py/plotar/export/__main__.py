import json
from pathlib import Path

import click

from .common import data2obj
from .usd import data2usdz, data2usd_ascii
from .gltf import data2gltf

if False:
    print("Welcome")
    # output = 'iris.gltf'
    import json
    with open(input) as f:
        pass
    with open(output, 'wb') as f:
        f.write(result)
        # json.dump(result, f, indent=True)
    with open('data_tmp.gltf', 'w') as f:
        result = data2gltf(payload)
        json.dump(result, f, indent=4)
    print("Byebye.")

@click.command()
@click.argument('data', type=click.Path(exists=True))
@click.argument('out', default='', type=click.Path())
@click.option('-f', '--format', default=None, help="format: gltf glb usdz usda obj. Can be a comma-separated list of formats. Default is to take extension of out or else gltf")
@click.option('--check/--no-check', default=False, help="check produced file (currently only for usdz)")
def export(data, out=None, format=None, check=False):
    """Convert the DATA.json to OUT.format."""
    if out is '':
        out = None
    data_path = Path(data)
    with open(data, 'r') as f:
        input = json.load(f)
    if format is None:
        if out is not None:
            # data_path.suffix might be '' !
            format = Path(out).suffix.lstrip('.')
    if format is None or format == '':
        format = format or 'usdz,gltf'
    format_list = format.split(",")
    assert out is None or len(format_list) == 1
    assert all(_ in 'gltf glb usdz usda obj'.split() for _ in format_list)
    del format # will be set in for loop below

    out_name_generated = False
    for format in format_list:
        if out is None or out_name_generated:
            out_name_generated = True
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
            else:
                result = data2usdz(input, save_usda=False, check=check)
                outfile.write(result)

if __name__ == '__main__':
    export()
