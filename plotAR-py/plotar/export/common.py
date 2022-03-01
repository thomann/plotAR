import math
import re
from collections import defaultdict
from pathlib import Path
from io import BytesIO

import numpy as np

# Do; this in R:
# library(RColorBrewer);library(dplyr)
# (brewer.pal(9, name='Set1') %>% col2rgb /256) %>% round(3) %>% apply(2, paste, collapse=',', sep='') %>%
#     paste0('(',., ')', collapse = ',') %>% cat

COLORS = [(0.891,0.102,0.109),(0.215,0.492,0.719),(0.301,0.684,0.289),(0.594,0.305,0.637),(0.996,0.496,0),(0.996,0.996,0.199),(0.648,0.336,0.156),(0.965,0.504,0.746),(0.598,0.598,0.598)]
COLORS_LEN = len(COLORS)

def hex2float(x):
    return([ int(x[_:_+2], base=16)/256 for _ in range(1,7,2) ])

def data2obj(data):
    result = ['# OBJ file for dataset']
    def add(x):
        result.append(x)
    numVert = 1
    colors = [ " ".join(_) for _ in COLORS ]
    for i,row in enumerate(data['data']):
        x, y, z = row[:3]
        col = COLORS[0]
        if 'col' in data and i <= len( data['col']):
            col = colors[ data['col'][i] % COLORS_LEN ]
        add(f'o Point {i}')
        for a in [1,-1]:
            for b in [1,-1]:
                for c in [1,-1]:
                    r = 0.05
                    v = " ".join(map(str, [x+a*r,y+b*r,z+c*r]))
                    add(f'v {v} {col}')
        f = [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [0, 2, 4, 6],
            [1, 3, 5, 7],
            [0, 1, 4, 5],
            [2, 3, 6, 7],
        ]
        for a,b,c,d in f:
            add(f"f {a+numVert} {b+numVert} {c+numVert} {a+numVert}")
            add(f"f {a+numVert} {c+numVert} {b+numVert} {a+numVert}")
            add(f"f {d + numVert} {b + numVert} {c + numVert} {d + numVert}")
            add(f"f {d + numVert} {c + numVert} {b + numVert} {d + numVert}")
        numVert += 8
    return "\n".join(result)


def obj2usdz(data):
    from .usd import run_usdconvert_python_cli
    obj = data2obj(data)
    usdz = run_usdconvert_python_cli(obj, in_suffix='obj')
    return usdz


def text2png(text, truetype=None, fontsize=10, color=(1, 0, 1), dpi_factor=10,
             font=[ "HelveticaNeue123", "HelveticaNeue", "Helvetica", "DejaVuSans", "Arial", ]):
    from PIL import Image, ImageDraw, ImageFont

    f = None
    # we also need to search lower case on Windows
    for fontname in font + [f.lower() for f in font]:
        try:
            f = ImageFont.truetype(fontname, fontsize * dpi_factor)
            # print(f"found font {f.font.family}")
            break
        except:
            pass
    if f is None:
        f = ImageFont.load_default()
        dpi_factor = 1
    w, h = f.getsize(text)

    img = Image.new("RGBA", (w, h), (0,0,0,0))
    # get a drawing context
    d = ImageDraw.Draw(img)
    # draw text, half opacity
    d.text((0, 0), text, font=f, fill=tuple(int(c*255) for c in color) + (255,) )

    buffer = BytesIO()
    img.save(buffer, format='png', compress_level=0)
    return w / dpi_factor, h / dpi_factor, buffer.getvalue()


class BitmapFont(object):
    # https://www.angelcode.com/products/bmfont/doc/file_format.html
    PAT = re.compile(r'(?:^|\s+)(?:([^"= ]+)(?:=([^" ]+|"[^="]*"))?)')
    def loadFont(self, f):
        font = defaultdict(list)
        def parse(_):
            if _[0] == _[-1] == '"':
                return _.strip('"')
            if ',' in _:
                return [ int(x) for x in _.split(",") ]
            return int(_)
        for line in f:
            tp, *vals = self.PAT.findall(line.strip())
            vals = { k: parse(v) for k,v in vals }
            font[tp[0]].append(vals)
        return font
    def __init__(self, fontpath) -> None:
        self.fontpath = fontpath
        with open(fontpath) as f:
            self._font = self.loadFont(f)
        self.chars = { chr(_['id']): _ for _ in self._font.get('char', []) }
    def png(self):
        from PIL import Image

        img_uri = self.page[0]['file']
        with open(self.fontpath.parent / img_uri, mode='rb') as img_f:
            # img = img_f.read()
            data = np.array(Image.open(img_f))
        data[:,:,3] = data[:,:,3].astype('uint16') * 255 / data[:,:,3].max()
        img = Image.fromarray(data)
        buffer = BytesIO()
        img.save(buffer, format='png', compress_level=0)
        return buffer.getvalue()

    @property
    def common(self):
        return self._font['common'][0]
    @property
    def page(self):
        return self._font['page']
    def layoutText(self, text, min_xoffset=0):
        # https://www.angelcode.com/products/bmfont/doc/render_text.html
        layout = []
        left = 0
        for ch in text:
            if ch not in self.chars:
                ch = ' '
            glyph = self.chars[ch].copy()
            glyph['left'] = left
            if min_xoffset is not None and glyph['xoffset'] < min_xoffset:
                glyph['xadvance'] += min_xoffset - glyph['xoffset']
                glyph['xoffset'] = min_xoffset
            layout.append(glyph)
            left += glyph['xadvance']
        return layout

def create_surface(surface):
    n, m = [int(_) for _ in surface['shape']]
    # print('surface:', n, m)
    arr = np.array(surface['data'])
    assert len(surface['data']) == n
    xvec = surface.get('x') or np.arange(-1, 1, 2 / m).tolist()
    yvec = surface.get('y') or np.arange(-1, 1, 2 / n).tolist()
    # TODO convert the following for loops into numpy
    vertices = np.array([
        [x, z / 2.0, y]
        for y, row in zip(yvec, surface['data'])
        for x, z in zip(xvec, row)
    ])
    indices = np.array([
        [j, j + m + 1, j + 1, j, j + m, j + m + 1]
        for j in range((n - 1) * m) if (j + 1) % m
    ]).flatten()#.tolist()
    # print('surface:', indices.max(), vertices.shape)
    # TODO handle edges better than roll-over
    dx = (np.roll(arr, 1, axis=0) - np.roll(arr, -1, axis=0)) / (np.roll(xvec, 1) - np.roll(xvec, -1))[np.newaxis, :]
    dy = (np.roll(arr, 1, axis=1) - np.roll(arr, -1, axis=1)) / (np.roll(yvec, 1) - np.roll(yvec, -1))[:, np.newaxis]
    dz = np.zeros((n, m)) + 2
    dlen = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    # print(dlen.shape, dlen.max())
    normals = np.stack((dx / dlen, dz / dlen, dy / dlen), axis=-1)
    # print(normals.shape)
    return indices, normals, vertices


def create_line(data_list, line, radius=0.01, segments=8):
    indices, normals, vertices, a, b = [], [], [], None, None
    n = len(data_list)

    def flip_yz(x):
        x = np.array(x)
        x = x[..., (0, 2, 1)]
        x[..., 2] *= -1
        return x
    def normalize(x):
        _ = np.linalg.norm(x)
        if _ == 0:
            return x
        return x / _
    # print(n,len(np.linspace(0, 2*math.pi, segments)), np.linspace(0,10,segments))
    def add_disk(x, v1, v2):
        base = len(vertices)//3
        for alpha in np.linspace(0, 2*math.pi, segments+1)[:-1]:
            _ = np.cos(alpha) * v1 + np.sin(alpha) * v2
            vertices.extend( x + radius*_ )
            # here we assume that v1 and v2 are normalized!
            normals.extend( normalize(_) )
        if base > 0:
            # we already had a previous add_disk so let's connect it
            for i in range(segments):
                p1 = (i + 1) % segments
                indices.extend([
                    base + p1, base+i-segments, base + i,
                    base + p1, base+p1-segments, base+i-segments,
                ])
    # n = 5
    for c in [flip_yz(data_list[_][:3]) for _ in line.get('points', []) if _ < n]:
        if a is not None and b is not None:
            ## calculate basis of plane in angle between vectors a-b and c-b
            v1 = normalize(normalize(a-b) + normalize(c-b))
            v2 = normalize(np.cross(a-b, c-b))
            if len(vertices) == 0:
                # let's quickly cheat here and use the same vectors...
                add_disk(a, v1, v2)
            add_disk(b, v1, v2)
        a = b
        b = c
    # let's quickly cheat here and use the same vectors...
    add_disk(c, v1, v2)
    return indices, vertices, normals

def line_segments(data_list, line, n, flip_vector=False):
    mids, quats, scales, a = [], [], [], None
    front_vector = (0,1,0) if flip_vector else (1, 0, 0)
    front_vector = np.array(front_vector)

    def flip_yz(x):
        x = np.array(x)
        x = x[..., (0, 2, 1)]
        x[..., 2] *= -1
        return x

    for b in [flip_yz(data_list[_][:3]) for _ in line.get('points', []) if _ < n]:
        if a is not None:
            # calculate quat for cylinder from a to b
            d = (b - a) / 2
            dlen = np.linalg.norm(d)
            if dlen == 0:
                # b==a so we do not add anything at that point
                continue
            mids.append(tuple((a + b) / 2))
            scales.append(dlen)
            if all(np.abs(d) == np.abs(d*front_vector)):
                # we do not need to rotate anything
                quats.append((1, 0, 0, 0))
            else:
                theta_2 = math.acos(np.dot(front_vector, d / dlen)) / 2
                rot_axis = np.cross(front_vector, d / dlen)
                if flip_vector:
                    rot_axis = rot_axis[[2,1,0]]
                    rot_axis[2] *= -1
                rot_axis = rot_axis / np.linalg.norm(rot_axis) * np.sin(theta_2)
                quats.append((np.cos(theta_2),) + tuple(rot_axis))
        a = b
    return zip(mids, quats, scales)