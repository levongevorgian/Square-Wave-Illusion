"""Refine fits, evaluate dense quadrature, and generate review figures/tables."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from model import Surface, sphere_directions, render, triangle_target
from fit import decode, encode_free, objective, metrics, bounds_for, fit_one

ROOT = Path(__file__).resolve().parent
OUT = ROOT/"results"/"optimization"


def evaluated_record(record, config, count=16384, q=15):
    surface, mu, k = decode(record["parameters"], record["family"], config["segments"])
    x, y = render(surface, sphere_directions(count), mu, k, samples_per_segment=q)
    target = triangle_target(x, mean=config["target_mean"], contrast=config["target_contrast"])
    return {**record, "evaluation_directions": count, "evaluation_samples_per_segment": q,
            "evaluation_metrics": metrics(y,target),
            "max_abs_height": float(np.max(np.abs(surface.heights))),
            "max_abs_slope": float(np.max(np.abs(np.diff(np.r_[surface.heights,surface.heights[0]])*config["segments"])))}


def run():
    fits = json.loads((OUT/"fits.json").read_text())
    if fits["status"] != "complete":
        raise ValueError("Finish fit.py first")
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
        surface, mu, k = decode(p,family,config["segments"])
        refined = {**start, "parameters": p.tolist(), "heights": surface.heights.tolist(),
                   "mean_light_vector":mu.tolist(), "azimuth_deg":float(p[-3]),
                   "elevation_deg":float(p[-2]), "kappa":k,
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
        ("N8", {"segments":8}), ("N32", {"segments":32}),
        ("no_smoothness", {"curvature_weight":0.0}),
        ("stronger_smoothness", {"curvature_weight":0.0001}),
        ("kappa60", {"kappa_bounds":[0.0,60.0]}),
    ]
    for label, changes in cases:
        cfg = {**config, **changes, "maxiter":120, "seeds":[71]}
        phase = np.arange(cfg["segments"])/cfg["segments"]
        initial_heights = np.interp(phase,np.arange(config["segments"]+1)/config["segments"],np.r_[best_surface.heights,best_surface.heights[0]])
        initial = encode_free(Surface(initial_heights), best["parameters"][-3:])
        record = fit_one("free",71,cfg,initial)
        record = evaluated_record(record,cfg)
        record.update(label=label,config=cfg)
        sensitivity.append(record)
        print("Sensitivity",label,record["evaluation_metrics"]["rmse"],flush=True)
        (OUT/"sensitivity.json").write_text(json.dumps(sensitivity,indent=2)+"\n")

    convergence = []
    surface,mu,k = decode(best["parameters"],"free",config["segments"])
    for m in (1024,2048,4096,8192,16384,32768):
        x,y = render(surface,sphere_directions(m),mu,k,samples_per_segment=15)
        target=triangle_target(x,mean=config["target_mean"],contrast=config["target_contrast"])
        convergence.append({"varied":"directions","value":m,**metrics(y,target)})
    for q in (1,3,5,7,15,31):
        x,y=render(surface,sphere_directions(16384),mu,k,samples_per_segment=q)
        target=triangle_target(x,mean=config["target_mean"],contrast=config["target_contrast"])
        convergence.append({"varied":"samples_per_segment","value":q,**metrics(y,target)})

    summary={"status":"complete", "target_is_provisional":True,"config":config,
             "refinement_config":fine,"selected_fits":selected,
             "all_seed_dense_evaluations":all_evaluated,"sensitivity":sensitivity,
             "convergence":convergence}
    (OUT/"analysis.json").write_text(json.dumps(summary,indent=2)+"\n")
    with (OUT/"model_comparison.csv").open("w",newline="") as f:
        fields=["family","rmse","mae","max_abs_error","mean_luminance","sampled_Michelson_contrast","r_squared","azimuth_deg","elevation_deg","kappa"]
        writer=csv.DictWriter(f,fields)
        writer.writeheader()
        for r in selected:
            writer.writerow({"family":r["family"],**r["evaluation_metrics"],"azimuth_deg":r["azimuth_deg"],"elevation_deg":r["elevation_deg"],"kappa":r["kappa"]})
    plot_results(summary)
    return summary


def plot_results(summary):
    plt.rcParams.update({"font.size":10,"font.family":"DejaVu Sans","axes.spines.top":False,"axes.spines.right":False})
    fig,axes=plt.subplots(4,2,figsize=(12,12),layout="constrained")
    profiles=[]
    names={"flat":"Flat control","sinusoid":"Fitted sinusoid","square_like":"Fitted square-like surface","free":"Fitted free surface (16 segments)"}
    for row,r in enumerate(summary["selected_fits"]):
        surface,mu,k=decode(r["parameters"],r["family"],summary["config"]["segments"])
        x,y=render(surface,sphere_directions(16384),mu,k,samples_per_segment=15)
        target=triangle_target(x,mean=summary["config"]["target_mean"],contrast=summary["config"]["target_contrast"])
        vertices=np.arange(len(surface.heights)+1)/len(surface.heights)
        axes[row,0].plot(vertices,np.r_[surface.heights,surface.heights[0]],"o-",color="#184b6b",ms=3)
        axes[row,0].set(title=names[r["family"]],xlabel="X / period",ylabel="Height / period",xlim=(0,1),ylim=(-0.15,0.15))
        axes[row,1].plot(x,target,color="#172b45",lw=2,label="Provisional target")
        axes[row,1].plot(x,y,color="#0b8b91",lw=1.6,label="Fitted render")
        axes[row,1].set(title=f"Dense-grid RMSE = {r['evaluation_metrics']['rmse']:.4f}",xlabel="X / period",ylabel="Relative linear luminance",xlim=(0,1),ylim=(0.2,1.8))
        axes[row,1].grid(alpha=0.15)
        if row==0:axes[row,1].legend(fontsize=9)
        profiles.extend((r["family"],float(a),float(b),float(c)) for a,b,c in zip(x,target,y))
    fig.suptitle("Inverse rendering | Target and fitted luminance\n16,384 light directions; 15 samples per segment",fontsize=16,fontweight="bold")
    fig.savefig(OUT/"fitted_models.png",dpi=155)
    plt.close(fig)
    with (OUT/"fitted_profiles.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["family","x","target","prediction"]);w.writerows(profiles)

    fig,axes=plt.subplots(1,3,figsize=(13,4.3),layout="constrained")
    labels=["N=8","N=16","N=32"]
    nrecords=[summary["sensitivity"][0],next(r for r in summary["selected_fits"] if r["family"]=="free"),summary["sensitivity"][1]]
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
    fig.savefig(OUT/"sensitivity.png",dpi=155)
    plt.close(fig)


if __name__=="__main__":
    run()
