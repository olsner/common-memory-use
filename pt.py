#!/usr/bin/env python

import sys

PAGE_SIZE = 4096

def unpack4(b):
    return (ord(b[3]) << 24) | (ord(b[2]) << 16) | (ord(b[1]) << 8) | ord(b[0])
def unpack8(b):
    return (unpack4(b[4:]) << 32L) | unpack4(b)

def read8(h):
    bytes = h.read(8)
    if len(bytes) < 8:
        raise Exception, str(len(bytes)) + ' is too few bytes'
    return unpack8(bytes)

def countpfn(pfn):
    """
    Return true if pfn should be counted as used based on its flags.
    """
    if pfn & (1 << 63L): # present
        return True
    return False

class Map(object):
    def __init__(self, s):
        fields = s.split()
        start,end = fields[0].split('-')
        self.start = int(start, 16)
        self.end = int(end, 16)
        self.pages = set()

    def readPagemap(self, pagemap):
        for page in self.iterpages():
            pos = page * 8
            try:
                pagemap.seek(pos)
                pfn = read8(pagemap)
                if countpfn(pfn):
                    self.pages.add(pfn)
            except Exception, e:
                print >>sys.stderr, hex(page * 4096), e

    def iterpages(self):
        return xrange(self.start / 4096, self.end / 4096)

    def getpages(self):
        return (self.end - self.start) / 4096

    def netpages(self):
        return len(self.pages)

class Proc(object):
    def __init__(self, pid, n = None):
        self.pid = pid
        self.nr = n
        self.maps = []
        with open('/proc/%d/maps' % pid, 'r') as h:
            for l in h.read().split('\n'):
                if not l: continue
                try:
                    self.maps.append(Map(l))
                except:
                    print >>sys.stderr, 'Problem:', l
                    raise
        with open('/proc/%d/pagemap' % pid, 'r') as h:
            for m in self.maps:
                m.readPagemap(h)

    def mapcount(self):
        return len(self.maps)

    def netpages(self):
        return sum(map(Map.netpages, self.maps))

    def pages(self):
        return sum(map(Map.getpages, self.maps))

# Some nice additions might be:
# * Do all processes for uid=N: useful for getting a whole app including
# services and processes on Android
# * All processes rooted at parent pid: e.g. the main chrome process

pids = {}
n = 0
for p in sys.argv[1:]:
    try:
        p = int(p)
        pids[p] = Proc(p, n)
        n += 1
    except Exception, e:
        print >>sys.stderr, "Problem parsing maps for", p, e

print
allprs = (1 << n) - 1
mapuse = {}
allpages = set()
for p,pr in pids.items():
    print '%5d: %7d pages in %3d maps (%d net)' % (p, pr.pages(), pr.mapcount(), pr.netpages())
    for m in pr.maps:
        for p in m.pages:
            mapuse[p] = mapuse.get(p, 0) | (1 << pr.nr)
        allpages |= m.pages
totalpages = sum(map(Proc.pages, pids.values()))
print 'total: %7d pages %.1f MiB (%d %.1f MiB net)' % (totalpages, totalpages * PAGE_SIZE / 1048576.0, len(allpages), len(allpages) * PAGE_SIZE / 1048576.0)

def popcount(i):
    res = 0
    while i:
        if i & 1: res += 1
        i = i >> 1
    return res

print allprs, len(mapuse)
#try:
#    flipmapuse = [0] * int(allprs + 1)
#    for p,c in mapuse.iteritems():
#        flipmapuse[c] += 1
#except:

class SparseList(object):
    def __init__(self, default):
        self.dict = {}
        self.default = default
        self.length = 0
    def __getitem__(self, key):
        return self.dict.get(key, self.default)
    def __setitem__(self, key, value):
        self.length = max(self.length, key + 1)
        return self.dict.__setitem__(key, value)
    def __len__(self):
        return self.length

flipmapuse = SparseList(0)
for c in mapuse.itervalues():
    flipmapuse[c] += 1

def toPids(n):
    if n == allprs:
        return "all"
    else:
        res = []
        nres = []
        for p in pids.values():
            if n & (1 << p.nr):
                res.append(str(p.pid))
            else:
                nres.append(str(p.pid))
        if len(res) <= len(nres):
            return ','.join(res)
        else:
            return "all except "+','.join(nres)

print
for n,c in sorted([(v,c) for c,v in flipmapuse.dict.iteritems()], reverse = True):
    if n > 1024/4: # > 1MiB
        print (n * 4 / 1024), "MiB", n, 'pages used by', toPids(c)
