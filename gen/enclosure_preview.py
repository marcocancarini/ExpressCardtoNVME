"""PNG preview of the case STLs. Usage: gen/.venv/bin/python gen/enclosure_preview.py"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import trimesh

root = Path(__file__).resolve().parent.parent
fig = plt.figure(figsize=(12, 6), dpi=110)
for i, w in enumerate((34, 54)):
    t = trimesh.load(root / "out" / "enclosure" / f"EC2M2_{w}_case.stl")
    ax = fig.add_subplot(1, 2, i + 1, projection="3d")
    v, f = trimesh.remesh.subdivide_to_size(t.vertices, t.faces, max_edge=1.5)
    t = trimesh.Trimesh(v, f)
    tri = t.vertices[t.faces]
    light = np.array([0.3, -0.5, 0.8]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(t.face_normals @ light, 0, 1)
    ax.add_collection3d(Poly3DCollection(tri, facecolors=np.c_[shade * 0.25, shade * 0.55, shade * 0.85], linewidths=0))
    ax.set_xlim(0, 60); ax.set_ylim(0, 75); ax.set_zlim(-25, 35)
    ax.set_box_aspect((60, 75, 60)); ax.view_init(elev=30, azim=60); ax.set_axis_off()
    ax.set_title(f"{w} mm case, seen from the open side")
plt.tight_layout()
plt.savefig(root / "docs" / "img" / "enclosure.png", facecolor="white")
