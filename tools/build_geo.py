"""Convierte el TopoJSON de ec-atlas (provincias, INEC 2015, MIT) en un GeoJSON liviano para el tablero."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
t = json.load(open(src))
sx, sy = t["transform"]["scale"]; tx, ty = t["transform"]["translate"]
arcs = []
for arc in t["arcs"]:
    x = y = 0; pts = []
    for dx, dy in arc:
        x += dx; y += dy
        pts.append([round(x * sx + tx, 4), round(y * sy + ty, 4)])
    arcs.append(pts)
def ring(idx):
    out = []
    for i in idx:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        out.extend(a if not out else a[1:])
    return out
def area(r):
    """Área con signo (fórmula del cordón, lon/lat): negativa = sentido horario."""
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:])) / 2


def orient(rings):
    """Convención de d3/Plotly geo: anillo exterior en sentido HORARIO y huecos antihorario.
    Con la orientación al revés, d3 interpreta el polígono como 'todo el planeta menos la provincia'."""
    out = []
    for i, r in enumerate(rings):
        cw = area(r) < 0
        out.append(r if (cw if i == 0 else not cw) else r[::-1])
    return out


feats = []
for g in t["objects"]["level2"]["geometries"]:
    if g["id"] in ("20", "90"):          # Galápagos y zona no delimitada: fuera del mapa continental
        continue
    if g["type"] == "Polygon":
        geom = {"type": "Polygon", "coordinates": orient([ring(r) for r in g["arcs"]])}
    else:
        geom = {"type": "MultiPolygon", "coordinates": [orient([ring(r) for r in p]) for p in g["arcs"]]}
    feats.append({"type": "Feature", "id": g["id"], "properties": {"dpa": g["id"], "name": g["properties"]["name"]}, "geometry": geom})
json.dump({"type": "FeatureCollection", "features": feats}, open(dst, "w"), separators=(",", ":"))
print(len(feats), "provincias")
