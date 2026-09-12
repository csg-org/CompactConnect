# Common Python

This directory is the only git source of truth for the `common_lambdas` package used by compact-app lambdas.

PsyPact is currently the only consumer. Do not commit `common_lambdas` under `psypact-app/lambdas/`. At CDK synth,
`PythonCommonLayerVersions(include_shared_python=True)` copies `common_lambdas/` into `lambdas/python/common/` so the
common Lambda layer can bundle it. That copy is gitignored.

PsyPact tests import `common_lambdas` by putting this directory on `sys.path` (the same approach used for `common-cdk`).
