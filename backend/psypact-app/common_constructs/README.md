# Common Constructs

This is the application node of a [namespace package](https://docs.python.org/3/glossary.html#term-namespace-package), which
houses common CDK constructs that are used across different apps in the CompactConnect project. Modules in this package
will be merged in Python with similarly-named namespace packages in each app's specific folder.

> **Note: Do not add an `__init__.py` file to any of the `common_constructs` packages, or they will break the
> import behavior.
