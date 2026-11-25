"""Generate the explanatory forward-model figures (no fitting)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from model import example_surface, light_direction, sphere_directions, render, triangle_target, transport_matrix

OUT = Path(__file__).resolve().parent.parent / "results" / "figures"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.labelcolor": "#344256", "text.color": "#172b45"})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    directions = sphere_directions(4096)
    mu = light_direction(180, 30)  # Source to the left, above the horizon.
    colors = {"uniform": "#8793a2", "directional": "#147d92", "no_shadows": "#cf814a"}
    figure, axes = plt.subplots(3, 2, figsize=(12, 10), constrained_layout=True,
                                gridspec_kw={"width_ratios": [1, 1.5]})
    for row, kind in enumerate(("flat", "sinusoid", "square_like")):
        surface = example_surface(kind)
        vertices = np.arange(3*len(surface.heights)+1) / len(surface.heights)
        z = surface.heights[np.arange(len(vertices)) % len(surface.heights)]
        ax = axes[row, 0]
        ax.plot(vertices, z, color="#172b45", lw=1.8)
        ax.fill_between(vertices, z, -0.19, color="#e3ebf1")
        ax.set(xlim=(0, 3), ylim=(-0.19, 0.22), xlabel="X / period", ylabel="Height / period",
               title={"flat": "Flat control", "sinusoid": "Sinusoidal corrugation", "square_like": "Square-like corrugation (finite ramps)"}[kind])
        ax.set_aspect(3)
        x, uniform = render(surface, directions, samples_per_segment=7)
        _, directional = render(surface, directions, mu, 8, samples_per_segment=7)
        _, unshadowed = render(surface, directions, mu, 8, samples_per_segment=7, shadows=False)
        ax = axes[row, 1]
        ax.plot(x, uniform, color=colors["uniform"], lw=1.7, label="Uniform lighting + shadows")
        ax.plot(x, directional, color=colors["directional"], lw=2, label="Directional lighting + shadows")
        ax.plot(x, unshadowed, color=colors["no_shadows"], ls="--", label="Directional lighting, shadows disabled")
        ax.set(xlabel="X / period (one cycle)", ylabel="Relative linear luminance", xlim=(0, 1), ylim=(0, 4.1))
        ax.grid(alpha=0.15)
        if row == 0:
            ax.legend(fontsize=8, loc="upper right")
    figure.suptitle("Square-wave illusion project | Forward model", fontsize=19, fontweight="bold")
    figure.savefig(OUT / "2_forward_model.png", dpi=160)
    plt.close(figure)

    # Show binary visibility separately from the cosine factor.
    surface = example_surface("sinusoid")
    x, z, _ = surface.samples(7)
    sun = light_direction(180, 18)
    visible = surface.visibility([sun], 7)[:, 0]
    response = transport_matrix(surface, [sun], 7)[:, 0]
    fig, axes = plt.subplots(2, 1, figsize=(11, 5.5), constrained_layout=True)
    axes[0].plot(x, z, color="#bec8d0")
    axes[0].scatter(x[visible], z[visible], c="#e7aa41", s=13, label="Can see the light source")
    axes[0].scatter(x[~visible], z[~visible], c="#304764", s=13, label="Blocked by the surface")
    axes[0].set(xlabel="X / period", ylabel="Height / period", title="Single light source: left, elevation 18 degrees")
    axes[0].legend(fontsize=9)
    axes[1].plot(x, response, color="#147d92", lw=2)
    axes[1].set(xlabel="X / period", ylabel="Visibility × cosine", title="Direct shading contribution (unit directional irradiance)", ylim=(-0.03, 1.03))
    fig.savefig(OUT / "3_shadow_check.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(11, 4.6), constrained_layout=True,
                             gridspec_kw={"height_ratios": [1, 1.3]})
    target_x = (np.arange(1200)+0.5)/400
    target = triangle_target(target_x)
    axes[0].plot(target_x, target, color="#172b45", lw=2)
    axes[0].set(xlabel="X / period", ylabel="Linear luminance", title="Provisional optimization target: triangle-wave luminance")
    # This is a schematic stimulus preview, not a calibrated luminance display.
    linear = np.tile((target/2)[None, :], (160, 1))
    srgb = np.where(linear <= 0.0031308, 12.92*linear, 1.055*linear**(1/2.4)-0.055)
    axes[1].imshow(srgb, cmap="gray", vmin=0, vmax=1, aspect="auto", extent=(0,3,0,1))
    axes[1].set(xticks=[], yticks=[], title="Illustration only: sRGB-encoded preview, no display calibration")
    fig.savefig(OUT / "1_target.png", dpi=160)
    plt.close(fig)
    print(f"Saved three explanatory figures to {OUT}")


if __name__ == "__main__":
    main()
