# Common Stacks

This package holds shared CDK **stacks** used across CompactConnect backend apps.

Import as `common_stacks.<module>` after the app adds `../common-cdk` to `sys.path` (see each app's `app.py`).

> **Note:** Do not add an `__init__.py` file to this package if you rely on namespace-package merging with app-local extensions in the future.