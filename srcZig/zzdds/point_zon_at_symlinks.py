#!/bin/python3
import re
path = 'build.zig.zon'
with open(path) as f:
    c = f.read()
c = re.sub(r'\.zzdds\s*=\s*\.\{[^}]+\}',
           '.zzdds = .{\n            .path = "packages/zzdds",\n        }', c)
c = re.sub(r'\.zidl\s*=\s*\.\{[^}]+\}',
           '.zidl = .{\n            .path = "packages/zidl",\n        }', c)
with open(path, 'w') as f:
    f.write(c)
print('build.zig.zon: zzdds and zidl rewritten to use local path symlinks')
