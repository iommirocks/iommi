# Vendored from flameprof 0.4
# https://github.com/baverman/flameprof
#
# Copyright (c) Anton Bobrov
# License: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
from collections import Counter
from functools import partial
from hashlib import sha1
from struct import Struct
from xml.sax.saxutils import escape

DEFAULT_WIDTH = 1200
DEFAULT_ROW_HEIGHT = 24
DEFAULT_FONT_SIZE = 12
DEFAULT_THRESHOLD = 0.1

eprint = partial(print, file=sys.stderr)


def bstr(data):
    if type(data) is str:
        data = data.encode('utf-8')
    return data


int_struct = Struct('!L')


def name_hash(name):
    v, = int_struct.unpack(sha1(bstr(name)).digest()[:4])
    return v / (0xffffffff + 1.0)


def gen_colors(s, e, size):
    for i in range(size):
        yield (s[0] + (e[0] - s[0]) * i // size,
               s[1] + (e[1] - s[1]) * i // size,
               s[2] + (e[2] - s[2]) * i // size)


COLORS = list(gen_colors((255, 240, 141), (255, 65, 34), 7))
CCOLORS = list(gen_colors((44, 255, 210), (113, 194, 0), 5))
ECOLORS = list(gen_colors((230, 230, 255), (150, 150, 255), 5))
DCOLORS = list(gen_colors((190, 190, 190), (240, 240, 240), 7))


def calc_callers(stats):
    roots = []
    funcs = {}
    calls = {}
    for func, (cc, nc, tt, ct, clist) in stats.items():
        funcs[func] = {'calls': [], 'called': [], 'stat': (cc, nc, tt, ct)}
        if not clist:
            roots.append(func)
            calls[('root', func)] = funcs[func]['stat']

    for func, (_, _, _, _, clist) in stats.items():
        for cfunc, t in clist.items():
            assert (cfunc, func) not in calls
            funcs[cfunc]['calls'].append(func)
            funcs[func]['called'].append(cfunc)
            calls[(cfunc, func)] = t

    total = sum(funcs[r]['stat'][3] for r in roots)
    ttotal = sum(funcs[r]['stat'][2] for r in funcs)

    if not (0.8 < total / ttotal < 1.2):
        eprint('Warning: flameprof can\'t find proper roots, root cumtime is {} but sum tottime is {}'.format(total, ttotal))

    # Try to find suitable root
    newroot = max((r for r in funcs if r not in roots), key=lambda r: funcs[r]['stat'][3])
    nstat = funcs[newroot]['stat']
    ntotal = total + nstat[3]
    if 0.8 < ntotal / ttotal < 1.2:
        roots.append(newroot)
        calls[('root', newroot)] = nstat
        total = ntotal
    else:
        total = ttotal

    funcs['root'] = {'calls': roots,
                     'called': [],
                     'stat': (1, 1, 0, total)}

    return funcs, calls


def prepare(funcs, calls, threshold=0.0001):
    blocks = []
    bblocks = []
    block_counts = Counter()

    def _counts(parent, visited, level=0):
        for child in funcs[parent]['calls']:
            k = parent, child
            block_counts[k] += 1
            if block_counts[k] < 2:
                if k not in visited:
                    _counts(child, visited | {k}, level+1)

    def _calc(parent, timings, level, origin, visited, trace=(), pccnt=1, pblock=None):
        childs = funcs[parent]['calls']
        _, _, ptt, ptc = timings
        fchilds = sorted(((f, funcs[f], calls[(parent, f)], max(block_counts[(parent, f)], pccnt))
                          for f in childs),
                         key=lambda r: r[0])

        gchilds = [r for r in fchilds if r[3] == 1]

        bchilds = [r for r in fchilds if r[3] > 1]
        if bchilds:
            gctc = sum(r[2][3] for r in gchilds)
            bctc = sum(r[2][3] for r in bchilds)
            rest = ptc-ptt-gctc
            if bctc > 0:
                factor = rest / bctc
            else:
                factor = 1
            bchilds = [(f, ff, (round(cc*factor), round(nc*factor), tt*factor, tc*factor), ccnt)
                       for f, ff, (cc, nc, tt, tc), ccnt in bchilds]

        for child, _, (cc, nc, tt, tc), ccnt in gchilds + bchilds:
            if tc/maxw > threshold:
                ckey = parent, child
                ctrace = trace + (child,)
                block = {
                    'trace': ctrace,
                    'color': (pccnt == 1 and ccnt > 1),
                    'level': level,
                    'name': child[2],
                    'hash_name': '{0[0]}:{0[1]}:{0[2]}'.format(child),
                    'full_name': '{0[0]}:{0[1]}:{0[2]} {5:.2%} ({1} {2} {3} {4})'.format(child, cc, nc, tt, tc, tc/maxw),
                    'w': tc,
                    'ww': tt,
                    'x': origin
                }
                blocks.append(block)
                if ckey not in visited:
                    _calc(child, (cc, nc, tt, tc), level + 1, origin, visited | {ckey},
                          ctrace, ccnt, block)
            elif pblock:
                pblock['ww'] += tc

            origin += tc

    def _calc_back(names, level, to, origin, visited, pw):
        if to and names:
            denom = sum(calls[(r, to)][3] for r in names)
            factor = pw / denom if denom else 1
        else:
            factor = 1

        for name in sorted(names):
            func = funcs[name]
            if to:
                cc, nc, tt, tc = calls[(name, to)]
                ttt = tc * factor
            else:
                cc, nc, tt, tc = func['stat']
                ttt = tt * factor

            if ttt / maxw > threshold:
                block = {
                    'color': 2 if level > 0 else not func['calls'],
                    'level': level,
                    'name': name[2],
                    'hash_name': '{0[0]}:{0[1]}:{0[2]}'.format(name),
                    'full_name': '{0[0]}:{0[1]}:{0[2]} {5:.2%} ({1} {2} {3} {4})'.format(name, cc, nc, tt, tc, tt/maxw),
                    'w': ttt,
                    'x': origin
                }
                bblocks.append(block)
                key = name, to
                if key not in visited:
                    _calc_back(func['called'], level+1, name, origin, visited | {key}, ttt)

            origin += ttt

    maxw = funcs['root']['stat'][3] * 1.0
    _counts('root', set())
    _calc('root', (1, 1, maxw, maxw), 0, 0, set())
    _calc_back((f for f in funcs if f != 'root'), 0, None, 0, set(), 0)

    return blocks, bblocks, maxw


def render_svg_section(blocks, maxw, colors, h=24, fsize=12, width=1200, top=0, invert=False):
    maxlevel = max(r['level'] for r in blocks)
    height = (maxlevel + 1) * h
    content = []
    for b in blocks:
        x = b['x'] * width / maxw
        tx = h / 6
        if invert:
            y = top + height - (maxlevel - b['level']) * h - h
        else:
            y = top + height - b['level'] * h - h
        ty = h / 2
        w = max(1, b['w'] * width / maxw - 1)
        bcolors = colors[b['color']]
        fill = bcolors[int(len(bcolors) * name_hash(b['hash_name']))]
        content.append(ELEM.format(w=w, x=x, y=y, tx=tx, ty=ty,
                                   name=escape(b['name']),
                                   full_name=escape(b['full_name']),
                                   fsize=fsize, h=h-1, fill=fill))

    return content, top + height


def render_svg(blocks, bblocks, maxw, h=24, fsize=12, width=1200):
    if blocks:
        s1, h1 = render_svg_section(blocks, maxw, [COLORS, CCOLORS], h=h,
                                    fsize=fsize, width=width, top=0)
        h1 += h
    else:
        s1, h1 = [], 0
    s2, h2 = render_svg_section(bblocks, maxw, [COLORS, ECOLORS, DCOLORS], h=h,
                                fsize=fsize, width=width, top=h1, invert=True)
    return SVG.format('\n'.join(s1 + s2), width=width, height=h2)


def render(stats, out, threshold=DEFAULT_THRESHOLD/100,
           width=DEFAULT_WIDTH, row_height=DEFAULT_ROW_HEIGHT,
           fsize=DEFAULT_FONT_SIZE):
    funcs, calls = calc_callers(stats)
    blocks, bblocks, maxw = prepare(funcs, calls, threshold=threshold)
    result = render_svg(blocks, bblocks, maxw, h=row_height, fsize=fsize, width=width)
    print(result, file=out)
    out.flush()


SVG = '''\
<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" width="{width}" height="{height}"
     xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<style type="text/css">
    .func_g:hover {{ stroke:black; stroke-width:0.5; cursor:pointer; }}
</style>
{}
</svg>'''

ELEM = '''\
<svg class="func_g" x="{x}" y="{y}" width="{w}" height="{h}"><g>
    <title>{full_name}</title>
    <rect height="100%" width="100%" fill="rgb{fill}" rx="2" ry="2" />
    <text alignment-baseline="central" x="{tx}" y="{ty}" font-size="{fsize}px" fill="rgb(0,0,0)">{name}</text>
</g></svg>'''
