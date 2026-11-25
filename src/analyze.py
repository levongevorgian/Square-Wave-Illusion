"""Refine fits, evaluate dense quadrature, and generate result figures."""
import json
import platform
from pathlib import Path
import numpy as np
import scipy
from scipy.optimize import minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from model import Surface, sphere_directions, render, triangle_target
from fit import decode, encode_free, objective, metrics, bounds_for, fit_one, shape_parameter_count

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"results"/"data"
FIGURES = ROOT/"results"/"figures"


def environment():
    return {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__, "platform": platform.system(),
            "note": "Timing depends on machine and BLAS settings."}


def evaluated_record(record, config, count=16384, q=15):
    surface, mu, k, intensity, target_shift = decode(record["parameters"], record["family"], config["segments"])
    x, y = render(surface, sphere_directions(count), mu, k, samples_per_segment=q, light_intensity=intensity)
    target = triangle_target(x, mean=config["target_mean"], contrast=config["target_contrast"], vertical_shift=target_shift)
    return {**record, "evaluation_directions": count, "evaluation_samples_per_segment": q,
            "evaluation_metrics": metrics(y,target),
            "max_abs_height": float(np.max(np.abs(surface.heights))),
            "max_abs_slope": float(np.max(np.abs(np.diff(np.r_[surface.heights,surface.heights[0]])*config["segments"])))}


def run():
    fits = json.loads((DATA/"fits.json").read_text())
    if fits["status"] != "complete":
        raise ValueError("Run fit_fixed.py and fit_free.py first")
    config = fits["config"]
    fine = {**config, "directions": 2048, "samples_per_segment": 5}
    directions = sphere_directions(fine["directions"])
    selected = []
    all_evaluated = []
    for family in ("flat", "sinusoid", "square_like", "free"):
        records = [r for r in fits["runs"] if r["family"] == family]
        all_evaluated.extend(evaluated_record(r, config, count=8192, q=15) for r in records)
        start = min(records,key=lambda r:r["objective"])
        fun = lambda p: objective(p, family, fine, directions)
        local = minimize(fun, start["parameters"], method="Powell", bounds=bounds_for(family,fine),
                         options={"maxiter": 150, "maxfev": 12000, "xtol":1e-7, "ftol":1e-8})
        p = local.x if local.fun < fun(start["parameters"]) else np.asarray(start["parameters"])
        surface, mu, k, intensity, target_shift = decode(p,family,config["segments"])
        light_values = p[shape_parameter_count(family, config["segments"]):]
        refined = {**start, "parameters": p.tolist(), "heights": surface.heights.tolist(),
                   "mean_light_vector":mu.tolist(), "azimuth_deg":float(light_values[0]),
                   "elevation_deg":float(light_values[1]), "kappa":k,
                   "light_intensity":intensity, "target_vertical_shift":target_shift,
                   "refinement_objective": fun(p), "refinement_success":bool(local.success),
                   "refinement_message":str(local.message)}
        # Distinguish scores of the originating coarse search from the refined
        # parameters, so machine-readable records cannot imply they are equal.
        for key in ("training_metrics", "objective", "selected_candidate"):
            refined["source_coarse_"+key] = refined.pop(key)
        refined = evaluated_record(refined, config)
        selected.append(refined)
        print("Dense evaluation", family, refined["evaluation_metrics"]["rmse"], flush=True)

    best = next(r for r in selected if r["family"] == "free")
    best_surface = Surface(best["heights"])
    sensitivity = []
    # Change resolution, regularization, and the upper concentration bound.
    cases = [
        ("N8", {"segments":8}), ("N16", {"segments":16}),
        ("no_smoothness", {"curvature_weight":0.0}),
        ("stronger_smoothness", {"curvature_weight":0.0001}),
        ("kappa60", {"kappa_bounds":[0.0,60.0]}),
    ]
    for label, changes in cases:
        cfg = {**config, **changes, "maxiter":120, "seeds":[71]}
        phase = np.arange(cfg["segments"])/cfg["segments"]
        initial_heights = np.interp(phase,np.arange(config["segments"]+1)/config["segments"],np.r_[best_surface.heights,best_surface.heights[0]])
        initial = encode_free(Surface(initial_heights), best["parameters"][-5:])
        record = fit_one("free",71,cfg,initial)
        record = evaluated_record(record,cfg)
        record.update(label=label,config=cfg)
        sensitivity.append(record)
        print("Sensitivity",label,record["evaluation_metrics"]["rmse"],flush=True)

    convergence = []
    surface,mu,k,intensity,target_shift = decode(best["parameters"],"free",config["segments"])
    for m in (1024,2048,4096,8192,16384,32768):
        x,y = render(surface,sphere_directions(m),mu,k,samples_per_segment=15,light_intensity=intensity)
        target=triangle_target(x,mean=config["target_mean"],contrast=config["target_contrast"],vertical_shift=target_shift)
        convergence.append({"varied":"directions","value":m,**metrics(y,target)})
    for q in (1,3,5,7,15,31):
        x,y=render(surface,sphere_directions(16384),mu,k,samples_per_segment=q,light_intensity=intensity)
        target=triangle_target(x,mean=config["target_mean"],contrast=config["target_contrast"],vertical_shift=target_shift)
        convergence.append({"varied":"samples_per_segment","value":q,**metrics(y,target)})

    summary={"status":"complete","environment":environment(),"target_is_provisional":True,"config":config,
             "refinement_config":fine,"selected_fits":selected,
             "all_seed_dense_evaluations":all_evaluated,"sensitivity":sensitivity,
             "convergence":convergence}
    (DATA/"analysis.json").write_text(json.dumps(summary,indent=2)+"\n")
    plot_results(summary)
    return summary


def plot_results(summary):
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size":10,"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(4,2,figsize=(12,12),layout="constrained")
    names={"flat":"Flat control","sinusoid":"Fitted sinusoid","square_like":"Fitted square-like surface","free":f"Fitted free surface ({summary['config']['segments']} vertices)"}
    for row,r in enumerate(summary["selected_fits"]):
        surface,mu,k,intensity,target_shift=decode(r["parameters"],r["family"],summary["config"]["segments"])
        x,y=render(surface,sphere_directions(16384),mu,k,samples_per_segment=15,light_intensity=intensity)
        target=triangle_target(x,mean=summary["config"]["target_mean"],contrast=summary["config"]["target_contrast"],vertical_shift=target_shift)
        vertices=np.arange(len(surface.heights)+1)/len(surface.heights)
        axes[row,0].plot(vertices,np.r_[surface.heights,surface.heights[0]],"o-",color="#184b6b",ms=3)
        axes[row,0].set(title=names[r["family"]],xlabel="X / period",ylabel="Height / period",xlim=(0,1),ylim=(-0.15,0.15))
        axes[row,1].plot(x,target,color="#172b45",lw=2,label="Provisional target")
        axes[row,1].plot(x,y,color="#0b8b91",lw=1.6,label="Fitted render")
        axes[row,1].set(title=f"Dense-grid RMSE = {r['evaluation_metrics']['rmse']:.4f}",xlabel="X / period",ylabel="Relative linear luminance",xlim=(0,1))
        axes[row,1].set_ylim(min(0.0, float(np.min(target)), float(np.min(y))),
                             max(1.8, float(np.max(target)), float(np.max(y))) * 1.05)
        axes[row,1].grid(alpha=0.15)
        if row==0:axes[row,1].legend(fontsize=9)
    fig.suptitle("Inverse rendering | Target and fitted luminance\n16,384 light directions; 15 samples per segment",fontsize=16,fontweight="bold")
    fig.savefig(FIGURES/"4_model_comparison.png",dpi=155)
    plt.close(fig)

    plot_best_fit(summary)

    fig,axes=plt.subplots(1,3,figsize=(13,4.3),layout="constrained")
    labels=["N=8","N=16","N=32"]
    nrecords=[summary["sensitivity"][0],summary["sensitivity"][1],next(r for r in summary["selected_fits"] if r["family"]=="free")]
    axes[0].bar(labels,[r["evaluation_metrics"]["rmse"] for r in nrecords],color="#147d92")
    axes[0].set(title="Geometry resolution",ylabel="Dense-grid RMSE")
    c=[r for r in summary["convergence"] if r["varied"]=="directions"]
    axes[1].plot([r["value"] for r in c],[r["rmse"] for r in c],"o-",color="#147d92")
    axes[1].set(xscale="log",title="Light-sampling convergence",xlabel="Number of directions",ylabel="RMSE")
    labels=["No penalty","Reference","Stronger","Kappa ≤60"]
    cases=[summary["sensitivity"][2],nrecords[1],summary["sensitivity"][3],summary["sensitivity"][4]]
    axes[2].bar(labels,[r["evaluation_metrics"]["rmse"] for r in cases],color="#147d92")
    axes[2].tick_params(axis="x",rotation=25)
    axes[2].set(title="Assumption sensitivity",ylabel="Dense-grid RMSE")
    fig.suptitle("Numerical checks | Sensitivity cases use one additional seed",fontsize=15)
    fig.savefig(FIGURES/"6_sensitivity.png",dpi=155)
    plt.close(fig)


def plot_best_fit(summary):
    record=next(r for r in summary["sensitivity"] if r["label"]=="N16")
    segments=16
    surface,mu,k,intensity,target_shift=decode(record["parameters"],"free",segments)
    x,y=render(surface,sphere_directions(16384),mu,k,samples_per_segment=15,light_intensity=intensity)
    fig=plt.figure(figsize=(12,4.3),layout="constrained")
    ax=fig.add_subplot(121,projection="3d")
    xv=np.arange(3*segments+1)/segments
    yv=np.linspace(0,1,9)
    xx,yy=np.meshgrid(xv,yv)
    zz=np.tile(surface.heights[np.arange(len(xv))%segments],(len(yv),1))
    segment_luminance=y.reshape(segments,15).mean(axis=1)
    linear=np.clip(segment_luminance[np.arange(3*segments)%segments]/2,0,1)
    gray=np.where(linear<=0.0031308,12.92*linear,1.055*linear**(1/2.4)-0.055)
    faces=np.tile(np.column_stack((gray,gray,gray,np.ones(3*segments)))[None,:,:],(len(yv)-1,1,1))
    ax.plot_surface(xx,yy,zz,facecolors=faces,shade=False,linewidth=0.2,edgecolor="#75828c",rstride=1,cstride=1)
    ax.set(xlabel="X / period",ylabel="Y / period",zlabel="Height / period",title="Fitted N=16 surface (Z exaggerated)")
    ax.set_box_aspect((3,1,0.65));ax.view_init(elev=28,azim=-65)
    ax=fig.add_subplot(122)
    ax.plot(x,triangle_target(x,mean=summary["config"]["target_mean"],contrast=summary["config"]["target_contrast"],vertical_shift=target_shift),color="#172b45",lw=2,label="Provisional target")
    ax.plot(x,y,color="#0b8b91",lw=1.5,label="Candidate render")
    ax.set(xlabel="X / period",ylabel="Relative linear luminance",title=f"N=16 candidate | dense RMSE {record['evaluation_metrics']['rmse']:.5f}")
    ax.legend(fontsize=9);ax.grid(alpha=0.15)
    fig.suptitle("One additional resolution fit | Visualized geometry and predicted luminance",fontsize=13)
    fig.savefig(FIGURES/"5_best_fit_N16.png",dpi=160)
    plt.close(fig)


if __name__=="__main__":
    run()

