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
@click.option('-f', '--format', default=None, help="format: gltf usdz usda obj. Default is to take extension of out or else gltf")
@click.option('--check/--no-check', default=False, help="check produced file (currently only for usdz)")
def export(data, out=None, format=None, check=False):
    """Convert the DATA.json to OUT.format."""
    data_path = Path(data)
    with open(data, 'r') as f:
        input = json.load(f)
    if format is None:
        assert out is not None
        # data_path.suffix might be '' !
        format = Path(out).suffix.lstrip('.')
    elif out is None or out == '':
        format = format or 'usdz'
        out = data_path.with_suffix("."+format)
    mode = 'wb' if format.startswith("usd") else 'w'
    with open(out, mode) as outfile:
        if format == 'gltf':
            result = data2gltf(input)
            json.dump(result, outfile)
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
