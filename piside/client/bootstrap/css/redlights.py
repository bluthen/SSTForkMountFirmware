import re
import fileinput
import sys

# css-color-extractor bootstrap.min.css.redlights.css > colors
# awk '{ print length($0) " " $0; }' colors | sort -r -n | cut -d ' ' -f 2- > colors2
# python redlights colors2 bootstrap.min.css.redlights.css

rgbaregex = re.compile('rgba\((\d+),(\d+),(\d+),(\d*.?\d*)\)')
hexsix = re.compile('#(..)(..)(..)')
hexthree = re.compile('#(...)')
replacements = []
with open(sys.argv[1]) as f:
    for l in f:
        l = l.strip()
        r = rgbaregex.match(l)
        if r:
            red = float(r.group(1))
            green = float(r.group(2))
            blue = float(r.group(3))
            alpha = r.group(4)
            real_red = int(0.21 * red + 0.72 * green + 0.07 * blue + 0.5)
            rstr = 'rgba(%d,0,0,%s)' % (real_red, alpha)
            print(l + ':' + rstr)
            replacements.append((l, rstr))
            continue
        r = hexsix.match(l)
        if r:
            red = int(r.group(1), 16)
            green = int(r.group(2), 16)
            blue = int(r.group(3), 16)
            real_red = int(0.21 * red + 0.72 * green + 0.07 * blue + 0.5)
            red = hex(real_red)[2:]
            if len(red) < 2:
                red = '0'+red
            rstr = '#%s0000' % (red,)
            print(l + ':' + rstr)
            replacements.append((l, rstr))
            continue
        r = hexthree.match(l)
        if r:
            red = int(r.group(1)[0:2], 16)
            red = hex(red)[2:]
            if len(red) < 2:
                red = '0'+red
            rstr = '#%s0000' % (red,)
            print(l + ':' + rstr)
            replacements.append((l, rstr))

for c in replacements:
    for line in fileinput.input([sys.argv[2]], inplace=True):
        print(line.replace(c[0], c[1]), end='')
