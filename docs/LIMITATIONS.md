# Limitations

This repository evaluates candidate image matches under a specified physical model. It does not establish a unique physical reconstruction or explain the perceptual mechanism of the square-wave illusion.

## Model scope

- The surface is an opaque, periodic, single-valued height graph, extruded along Y and viewed orthographically. Overhangs, vertical faces, finite surface boundaries, and perspective are not modeled.
- Reflectance is constant and Lambertian. The renderer includes direct illumination only; it omits interreflection, specular reflection, texture, finite-area emitters, camera response, and display calibration.
- The triangular luminance target, bounds, and relative intensity scale are modeling choices. They are not calibrated measurements of a historical stimulus or display.
- The computation predicts relative linear luminance. It does not model sRGB display values, adaptation, neural processing, or observer responses.

## Numerical and optimization limits

- Fibonacci sphere points and within-segment samples approximate the illumination integral. Results can depend on quadrature resolution; convergence checks are numerical diagnostics, not proof of exact integration.
- The optimizer uses stochastic differential evolution followed by bounded Powell refinement. Local termination does not prove a global optimum. The free-shape searches reached their generation limit in the saved historical results.
- Height and slope constraints use a penalty in the objective rather than a general hard-constrained solver. Candidate bounds should be checked in the saved fit records.
- Shape and lighting can trade off while producing similar profiles. The reported fit metrics describe deterministic profile matching; they are not confidence intervals or statistical evidence.

## Evidence limits

No human-participant data were collected. The included references motivate the model but their stimuli, apparatus, and behavioral results are not reproduced. A good fit is a candidate explanation within this model, not evidence that observers perceive that surface or use this mechanism.

The figures and JSON files currently committed under `results/` were generated with an earlier parameterization. Run `python run_all.py --full` to regenerate them before interpreting them as results for the current code.

