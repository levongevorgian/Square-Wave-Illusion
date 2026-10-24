"""Create the review PDF from saved, verified analysis outputs.

Optional authoring dependencies: pip install -r requirements-report.txt
"""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT=Path(__file__).resolve().parent
INK=colors.HexColor('#19364d')
TEAL=colors.HexColor('#147d92')
PALE=colors.HexColor('#edf4f7')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=24,leading=29,textColor=INK,spaceAfter=14))
styles.add(ParagraphStyle(name='ReportSub',fontName='Helvetica',fontSize=11,leading=15,textColor=TEAL,spaceAfter=12))
styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=9.5,leading=13.2,spaceAfter=7,textColor=INK))
styles.add(ParagraphStyle(name='SmallCustom',fontName='Helvetica',fontSize=8,leading=10.5,spaceAfter=4,textColor=INK))
styles.add(ParagraphStyle(name='HCustom',fontName='Helvetica-Bold',fontSize=14,leading=18,spaceBefore=10,spaceAfter=8,textColor=INK))
styles.add(ParagraphStyle(name='CodeCustom',fontName='Courier',fontSize=8.2,leading=12,spaceAfter=6,textColor=INK))


def p(text,kind='BodyCustom'):return Paragraph(text,styles[kind])
def h(text):return p(text,'HCustom')
def gap(size=7):return Spacer(1,size)
def table(rows,widths):
    data=[[p(str(cell),'SmallCustom') for cell in row] for row in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),0.7,TEAL),('LINEBELOW',(0,1),(-1,-1),0.3,colors.HexColor('#d7e2e8')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t

def picture(path,width):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:w,ht=im.size
    return Image(str(path),width=width,height=width*ht/w)

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#d7e2e8'))
    canvas.line(1.8*cm,1.5*cm,A4[0]-1.8*cm,1.5*cm)
    canvas.setFillColor(INK);canvas.setFont('Helvetica',8)
    canvas.drawString(1.8*cm,1.05*cm,'Group 2 | Physical simulation | 22 October 2026')
    canvas.drawRightString(A4[0]-1.8*cm,1.05*cm,str(doc.page))


def main():
    data=json.loads((ROOT/'results/optimization/analysis.json').read_text())
    fits={r['family']:r for r in data['selected_fits']}
    free=fits['free']
    n32=next(r for r in data['sensitivity'] if r['label']=='N32')
    validation=json.loads((ROOT/'results/validation.json').read_text())
    q={r['value']:r['rmse'] for r in data['convergence'] if r['varied']=='samples_per_segment'}
    m={r['value']:r['rmse'] for r in data['convergence'] if r['varied']=='directions'}
    s=[]
    s += [p('Square-Wave Illusion','ReportTitle'),p('Physical simulation and inverse rendering','ReportSub'),p('Design and Analysis of Experiments | Group 2<br/>Computational study. Baseline triangle-wave target; no human data.','SmallCustom'),gap(12)]
    s += [h('What has been completed?'),p('All six computational steps of the computational model are implemented: periodic surface geometry, light visibility and self-shadowing, spherical integration, Lambertian shading, von Mises-Fisher lighting, and joint optimization of surface heights and lighting. The repository includes source code, an executed notebook, saved results, numerical checks, and reproduction instructions.')]
    s += [h('Current finding'),p(f'A bounded periodic height field can approximate the provisional triangle-wave target under the stated direct-light model. The free-surface candidate has RMSE <b>{free["evaluation_metrics"]["rmse"]:.5f}</b> at N=16. An additional N=32 search gives <b>{n32["evaluation_metrics"]["rmse"]:.5f}</b>. Target mean luminance is one. These values describe image matching, not observer performance.')]
    rows=[['Model','Segments','Dense RMSE','R-squared']]
    for label,r,n in [('Flat control',fits['flat'],16),('Sinusoid',fits['sinusoid'],16),('Square-like',fits['square_like'],16),('Free surface',free,16),('Free: resolution check',n32,32)]:
        rows.append([label,n,f'{r["evaluation_metrics"]["rmse"]:.5f}',f'{r["evaluation_metrics"]["r_squared"]:.4f}'])
    s += [table(rows,[7*cm,2.3*cm,3.2*cm,3.2*cm]),gap(),p('Dense metrics use 16,384 light directions and 15 samples per segment. The N=32 result is a one-seed sensitivity case, not part of the three-seed N=16 comparison. R-squared is descriptive.','SmallCustom')]
    s += [h('What is not established?'),p('The fitted geometry is not constrained to be rectangular. A low residual does not show that it is the surface people perceive, identify a unique shape/light solution, prove global optimality, or establish a psychological explanation. Final interpretation requires agreement on the exact stimulus and admissible model.')]
    s += [picture(ROOT/'results/optimization/best_candidate.png',14.8*cm),p('Additional N=32 fit. The Z axis is exaggerated and the grayscale is illustrative.','SmallCustom')]
    s += [PageBreak(),p('1. Physical model','ReportTitle')]
    s += [p('Geometry. One period contains N equally spaced height vertices, joined by planar segments with periodic closure. The cross-section repeats along X and extends along Y. An orthographic observer looks down Z. Surfaces are opaque and single-valued; vertical walls and overhangs are excluded.')]
    s += [p('Visibility. A light vector points toward its source. A point receives direct light only if the ray clears the maximum surface-elevation slope on that side. Checking vertices within one full period on each side includes neighboring cycles exactly for this geometry. Several samples are needed because a segment can be partly shadowed.')]
    s += [picture(ROOT/'results/shadow_check.png',16.5*cm)]
    s += [p('Example above: a low light source illuminates yellow points; dark points are blocked by the surface. The second plot multiplies binary visibility by the Lambertian cosine factor.','SmallCustom')]
    s += [p('Lighting. Approximately equal-solid-angle Fibonacci points avoid uniform-latitude pole bias. A full-sphere von Mises-Fisher radiance profile has mean direction mu and concentration kappa. Zero concentration is uniform; larger values make the light more directional. Total angular radiance is fixed.')]
    s += [p('L = (rho/pi) sum [R(light) V max(0, normal.light) 4pi/M]','CodeCustom')]
    s += [p('Constant albedo rho=1; output is relative linear luminance. No interreflection, specular reflection, texture, or calibrated display response is included. A flat white surface under uniform unit radiance has output one. See docs/METHODS.md for the full definitions and proof of the horizon construction.')]
    s += [PageBreak(),p('2. Fitted candidate models','ReportTitle')]
    s += [p('Each model is fitted to the same provisional triangle wave (period one, mean one, Michelson contrast 0.6). No free brightness gain or offset is used. Geometry appears on the left; target and rendered luminance appear on the right. These are synthetic modeling outputs.')]
    s += [picture(ROOT/'results/optimization/fitted_models.png',16.5*cm)]
    s += [p(f'The selected free candidate has maximum absolute height {free["max_abs_height"]:.5f} periods and maximum absolute slope {free["max_abs_slope"]:.5f}. Its light has azimuth {free["azimuth_deg"]:.2f} degrees, elevation {free["elevation_deg"]:.2f} degrees, and kappa {free["kappa"]:.3f}. These are one candidate set of parameters, not a unique reconstruction.','SmallCustom')]
    s += [PageBreak(),p('3. Optimization and numerical checks','ReportTitle')]
    s += [p('The objective combines mean squared luminance error with a curvature penalty and penalties for height/slope bound violations. Mean height is fixed to zero. The N=16 free model has N-1 height coordinates plus three lighting coordinates; this removes the redundant vertical offset from the nominal N+3 outline.')]
    s += [table([['Reference setting','Value'],['Height and slope limits','Absolute height <=0.25 periods; absolute slope <=6'],['Light bounds','Azimuth 0-180 degrees; elevation 5-85 degrees; kappa 0-30'],['Reference search','1,024 directions; 3 samples/segment; seeds 11, 29, 47'],['Solver','Differential evolution; bounded Powell refinement'],['Regularization','Mean squared periodic curvature; weight 0.00001'],['Refinement and evaluation','Refine at 2,048 directions and 5 samples; evaluate at 16,384 and 15']],[4.3*cm,12.2*cm])]
    s += [gap(),p('All free-surface global searches reached their iteration limit. Selected final local refinements terminated successfully; that stopping condition is not a proof of a global minimum. Free searches share the best fixed-shape initialization. Other initializations may yield different solutions.')]
    s += [picture(ROOT/'results/optimization/sensitivity.png',16.5*cm)]
    s += [p(f'<b>Midpoint trap:</b> the same N=16 candidate gives RMSE {q[1]:.5f} at segment midpoints, but {q[15]:.5f} across 15 samples per segment ({q[31]:.5f} at 31). A midpoint-only claim would substantially overstate the fit. Increasing light directions from 16,384 to 32,768 changes the error from {m[16384]:.5f} to {m[32768]:.5f}.')]
    s += [p('N=8 and N=32, changed smoothness, and a kappa upper bound of 60 were tested with one additional warm-started seed each. These are diagnostics, not exhaustive searches or inferential comparisons. Geometry resolution remains influential.','SmallCustom')]
    s += [PageBreak(),p('4. Validation and reproduction','ReportTitle')]
    s += [p(f'<b>{sum(validation.values())} of {len(validation)} physical/numerical checks passed.</b> These include sphere-unit vectors, light normalization, the flat-surface analytic result, overhead illumination, the cosine law, lower-hemisphere blocking, nonnegativity, and invariance to height translation and light reflection along the ridges.')]
    s += [p('The shadow algorithm matches an independent explicit ray/segment intersection calculation at 576 sample/direction pairs containing both lit and shadowed points. Eight regression tests additionally check periodic normals, uniform radiance on tilted unoccluded facets, parameter encoding, invalid inputs, bounds, saved result consistency, and recovery of known synthetic kappa. All eight pass.')]
    s += [table([['Open this','Purpose'],['README.md','Status, findings, links, and quick start'],['simulation_walkthrough.ipynb','Executed explanation with embedded plots and results'],['docs/METHODS.md','Geometry, light conventions, constraints, and objective'],['docs/RESULTS.md','Metrics, interpretation, and numerical sensitivity'],['docs/LIMITATIONS.md','Model limitations and future work'],['results/optimization/fits.json','All 12 reference searches and solver statuses'],['results/optimization/analysis.json','Dense evaluation, sensitivity, and convergence'],['results/optimization/*.csv','Numerical comparisons and sampled luminance profiles'],['configs/reference.json','Editable target and search configuration']],[7*cm,9.5*cm])]
    s += [gap(10),p('Quick checks, from the repository root:','BodyCustom'),p('python validate.py<br/>python -m unittest -v test_project.py','CodeCustom'),p('Full computational reproduction:','BodyCustom'),p('python run_all.py --full','CodeCustom')]
    s += [p('The full pipeline regenerates demonstrations, fitting, analysis, summaries, the executed notebook, and tests. Generated outputs are replaced. The PDF is rebuilt separately with build_report.py and the optional requirements-report.txt dependencies. Saved reference versions are in requirements-reference.txt. Single-thread BLAS settings and fixed seeds improve reproducibility, but exact timings and final digits may vary across environments.')]
    s += [PageBreak(),p('5. Limitations and future work','ReportTitle')]
    s += [p('The results are conditional on the baseline target and the specified physical model. The following extensions address the main remaining uncertainties.')]
    decisions=[('Alternative target profiles','Evaluate specified harmonic approximations or measured luminance profiles, varying phase, mean, contrast, and period.'),('Admissible surface shapes','Compare unconstrained bounded height fields with shapes constrained to match a particular reported square-like percept.'),('Illumination and geometry','Assess additional illumination lobes, alternative bounds, and interreflection beyond the current direct-only model.'),('Resolution and search robustness','Evaluate whole-profile luminance and contrast tolerances at higher geometry resolutions and with additional search initializations.'),('Perceptual validation','A separate behavioral study could test whether the candidate rendered surfaces correspond to the reported percept. No such inference follows from image matching alone.')]
    for title,body in decisions:s += [h(title),p(body)]
    s += [h('Literature context'),p('Leguire, L. E., Blake, R., and Sloane, M. E. (1981). A Novel Illusion of Bars Made from Triangles. <i>Science, 212</i>, 1172-1175.','SmallCustom'),p('Wildzunas, R. M., and May, J. G. (1992). Phase shifts and the square-wave illusion. <i>Spatial Vision, 6</i>, 209-220.','SmallCustom'),p('May, J. G. (1994). Stimulus manipulations that reduce the square-wave illusion. <i>Spatial Vision, 8</i>, 329-340.','SmallCustom'),p('These papers motivate the question; their behavioral experiments are not reproduced here. Additional technical references and links are in docs/REFERENCES.md. Paper PDFs, private email text, and unpublished collaborator material are not redistributed.','SmallCustom')]
    output=ROOT/'docs/project_report.pdf'
    doc=SimpleDocTemplate(str(output),pagesize=A4,leftMargin=1.8*cm,rightMargin=1.8*cm,topMargin=1.5*cm,bottomMargin=1.9*cm,title='Square-Wave Illusion: Physical Simulation and Inverse Rendering',author='Group 2')
    doc.build(s,onFirstPage=footer,onLaterPages=footer)
    print(output)


if __name__=='__main__':main()
