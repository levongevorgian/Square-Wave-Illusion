# Questions for professor review

The implementation of all six computational steps is available. The reference results use a provisional synthetic target. These choices should be reviewed before interpreting the simulation as a test of the final project hypothesis.

1. **Exact target:** Should the target be the ideal triangle wave, a specified harmonic approximation, or measured luminance values? Confirm phase, mean, contrast, and cycle width.
2. **Shape class:** Is any bounded periodic height field admissible, or must it match the particular perceived corrugation? A successful fit by a sinusoidal-like shape does not by itself validate a specifically square-shaped percept.
3. **Light model:** Is the full-sphere vMF radiance model appropriate? Are fixed total angular radiance, the 5–85 degree source-elevation interval, and the kappa bound acceptable? Should an ambient component or multiple lobes be considered?
4. **Physical bounds:** Agree on acceptable height, slope, and curvature. Current bounds and smoothness weights are explicit modeling choices.
5. **Success criterion:** Define an acceptable whole-profile luminance error and contrast tolerance before finalizing the claim. The current error is measured across segments, not only at their midpoints.
6. **Resolution:** N=32 improved the error compared with N=16. Choose a final geometry resolution and compute budget; investigate higher N if a stricter error threshold requires it.
7. **Additional physics:** Is direct illumination sufficient, or should interreflection be included? The current model does not include light bouncing between corrugations.
8. **Perceptual interpretation:** What shape features would count as consistent with the reported percept? Human-participant validation is a separate possible extension, not part of the implemented simulation.
9. **Course submission:** Confirm report length, required deliverables, group contributions, and presentation date. The generated report is a review draft with no invented deadline or author order.
10. **Collaborator integration:** Any relation to Dr. Giesel's unpublished work remains for the instructor to clarify. No unpublished work has been assumed, quoted, or included here; communication remains with the instructor as described in the supplied email.

## What is already available

- Periodic surface geometry and segment normals.
- Binary light visibility, including shadowing by neighboring cycles.
- Approximately uniform spherical quadrature.
- Lambertian integration and vMF lighting.
- Bounded, regularized optimization of geometry and lighting.
- Flat, sinusoidal, square-like, and free-surface comparisons.
- Three reference seeds, denser reevaluation, and one-seed sensitivity cases.
- Independent ray-intersection checks, a synthetic parameter-recovery check, saved numerical outputs, and runnable code.

These results show candidate image matches within the stated model. They do not establish a unique reconstruction, global optimality, publication novelty, or a psychological mechanism.
