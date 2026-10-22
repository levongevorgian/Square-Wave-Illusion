# Methods and scope

Status: computational implementation for group/professor review, 22 October 2026. No human-participant data were collected. The current target is provisional.

## Research question

Can a bounded, periodically corrugated, constant-reflectance Lambertian surface under directional environmental illumination approximate a triangle-wave luminance profile? This tests existence of a candidate physical explanation within a specified model. It does not establish the visual mechanism or recover the surface people perceive.

## Surface and viewing geometry

One period P=1 is represented by N vertices `(j/N, z_j)`. Adjacent vertices are connected, including the last vertex to the first in the next cycle. The surface is extruded along Y and repeated infinitely along X. It is opaque, single-valued in Z, and viewed orthographically along Z. The model excludes overhangs and vertical faces. The square-like family uses finite ramps.

Each segment has constant normal proportional to `(-s_j,0,1)`, where `s_j=N*(z_(j+1)-z_j)`. Samples within each segment use evenly spaced midpoint quadrature in X. The model predicts image radiance per projected position, so it does not multiply the result by surface area.

## Visibility

Light vectors point from the surface toward the source. At a sample point, compute the maximum slope to surface vertices on each side, with zero as the infinite-distance limit. An upward ray is visible if `l_z > horizon * abs(l_x)`. The horizon uses the side indicated by the sign of `l_x`.

For the infinitely extruded surface, Y displacement has no effect on shadowing. On a planar segment, the elevation slope from a fixed point is monotonic, so vertices suffice. For any above-sample vertex, its nearest periodic copy on each side gives the largest positive elevation slope. Consequently a full period on either side suffices, without a finite-distance truncation approximation. Below-horizon rays are blocked by the unbounded graph. Grazing rays are treated as blocked; they have zero measure in the illumination integral.

Visibility is binary at a sample point. Several samples are required because one planar segment can be partly shadowed. The independent validation uses explicit ray/segment intersections over neighboring cycles rather than the horizon formula.

## Light distribution and Lambertian rendering

Equal-weight Fibonacci sphere points approximate uniform solid-angle quadrature. This avoids the pole bias of uniform latitude-longitude sampling. Points are deterministic and approximately uniform; the integration is still approximate.

A von Mises-Fisher density on the sphere is proportional to `exp(kappa * mu dot l)`. The mean direction mu is a unit vector with azimuth and elevation parameters. Kappa is a concentration, not a linear variance. At zero the distribution is uniform. The radiance profile is `R(l)=4*pi*f_vMF(l)` so sphere-average radiance is analytically one. Total incident angular radiance is fixed during fitting; there is no fitted brightness gain or offset.

The stable implementation uses `R(l)=[2*kappa/(1-exp(-2*kappa))]*exp(kappa*(mu dot l-1))`, with the uniform limit handled separately.

The predicted output is

`L_i = (rho/pi) * sum_j [R(l_j) * V_ij * max(0, n_i dot l_j) * 4*pi/M]`.

Albedo rho is fixed at one. Units are relative linear luminance. A flat surface under uniform unit radiance gives output one. Only direct light is included: there is no interreflection, specular reflection, texture, cast light from finite emitters, camera response, or calibrated screen model.

vMF definition reference: [SciPy documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.vonmises_fisher.html).

## Target

`T(x)=1+0.6*(4*abs((x mod 1)-0.5)-1)`.

The period is one, the mean is one, and Michelson contrast is 0.6, giving a continuous range 0.4 to 1.6. The peak is at phase zero. These are explicit choices for a synthetic baseline; they do not claim exact reproduction of the historical stimuli or final specifications from the instructor. Evaluate errors on the linear profile, not on the sRGB preview.

## Optimization

Reference comparison: N=16, M=1,024 light directions, and 3 samples per segment. Seeds are 11, 29, and 47. Four model families are fitted:

| Family | Geometry parameters | Lighting parameters |
|---|---|---|
| Flat control | None | Azimuth, elevation, kappa |
| Sinusoid | Amplitude and phase | Azimuth, elevation, kappa |
| Square-like | Amplitude and phase; tanh sharpness fixed at 4 | Azimuth, elevation, kappa |
| Free surface | N-1 heights; final height fixes mean zero | Azimuth, elevation, kappa |

The objective is `mean((L-T)^2) + lambda*mean(c_j^2) + constraint_penalty`, where `c_j=N^2*(z_(j-1)-2*z_j+z_(j+1))` and reference lambda is 0.00001. The penalty is 1,000 times summed squared height/slope bound violations. Candidates with penalty above one return early. Final bound satisfaction is checked independently; this soft-penalty implementation is not a general hard-constraint solver.

Bounds: absolute height <=0.25 periods; absolute slope <=6; azimuth 0 to 180 degrees; elevation 5 to 85 degrees; kappa 0 to 30. Template amplitudes range 0 to 0.25 and phase 0 to 1. Source means below the horizon are excluded by the elevation bound, although the vMF radiance distribution itself covers the whole sphere.

Differential evolution is followed by bounded Powell refinement. Global search uses at most 160 generations with a population multiplier of 7; local passes have finite evaluation budgets. Free-surface runs start from the best fixed-shape fit, with a population containing local perturbations and global samples. They are separate stochastic searches around a shared initialization, not independent random initial geometries. The best available candidate is retained if refinement worsens the objective.

The selected candidate for each family is locally refined at 2,048 directions and 5 samples per segment. Final primary comparisons are evaluated at 16,384 directions and 15 samples per segment. All three original seeds are also reevaluated at 8,192 directions and 15 samples. Retaining the same candidate on denser grids checks numerical integration; it is not a new target or behavioral validation.

Global free-surface searches reached their iteration limit; successful local termination does not establish a global minimum. Saved JSON records retain solver statuses. Report results as candidate fits under the documented bounds.

## Sensitivity checks

Additional one-seed searches change one setting at a time: N=8, N=32, no curvature penalty, lambda=0.0001, or kappa upper bound 60. They are initialized from the reference free fit (periodically interpolated when N changes). They have at most 120 global generations. These are numerical diagnostics rather than exhaustive model comparisons or statistical tests.

For the selected reference free fit, vary light-direction counts from 1,024 to 32,768 and within-segment samples from 1 to 31. The 1-sample case measures only segment midpoints and can underestimate whole-profile error. Increasing N changes the allowable geometry; increasing M or within-segment samples changes how the same geometry is evaluated.

## Identifiability and interpretation

Adding a constant height changes no image, so mean height is fixed to zero. Reflecting the light direction across the XZ plane is indistinguishable for a Y-invariant surface in the exact integral; azimuth is restricted to one representative half-sphere. Finite sphere quadrature only approximates this symmetry. At kappa zero the mean direction is undefined in effect. Shape/light tradeoffs remain, so a low residual is not a unique 3D reconstruction.

The nominal N+3 parameters in the instructor's outline include a redundant height offset; the implementation uses N-1+3 independent coordinates. Error measures and R-squared describe deterministic profile matching. They are not inferential statistics, confidence intervals, or evidence that observers use this model. Failure to find a fit would not prove that no physical explanation exists.
