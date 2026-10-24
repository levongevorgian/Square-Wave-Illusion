# Limitations and future work

## Target specification

The current baseline is an ideal triangle-wave luminance profile with mean one, Michelson contrast 0.6, and period one. Harmonic approximations and measured luminance profiles would provide additional target conditions.

## Shape and illumination assumptions

The surface is an opaque periodic height field, extruded along Y and viewed orthographically. The free surface is not constrained to a rectangular cross-section. A low luminance residual therefore does not establish a match to a particular perceived shape.

Illumination uses a single full-sphere von Mises-Fisher radiance distribution with fixed total angular radiance. Height, slope, elevation, and concentration bounds are specified in the configuration. Interreflection, specular reflection, overhangs, and display calibration are outside the current model.

## Numerical limitations

The global free-surface searches reached their iteration budgets. Local Powell termination does not establish global optimality. The reference searches share a fixed-shape initialization. Additional initializations and higher geometry resolution are useful extensions.

Whole-profile errors must include multiple positions within each segment; midpoint-only evaluation materially understates the residual. The N=32 result is a single additional sensitivity search rather than a three-seed comparison.

## Interpretation and extensions

The results establish candidate physical image matches under the stated assumptions. Shape and illumination are not uniquely identifiable from one profile. Error metrics describe deterministic luminance matching, not observer performance or a psychological mechanism.

Further work can assess alternative target profiles, admissible shape classes, multiple illumination lobes, interreflection, stricter error tolerances, and perceptual validation. No human-participant data are included in this study.
