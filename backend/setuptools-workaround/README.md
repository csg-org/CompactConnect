# Authorize.Net setuptools bug workaround

Authorize.Net's python SDK, `authorizenet` currently has [a bug that makes it uninstallable in environments that use the latest
of python-maintained library management tools](https://github.com/AuthorizeNet/sdk-python/issues/166). Specifically, `setuptools`, with version `78+` stopped supporting some long-deprecated configuration arguments, which the `authorizenet` library still uses. In the hopes that Authorize.Net will quickly remedy this bug, we have adopted a temporary work-around to unblock our deploy pipelines: We've custom-built a docker image for building our lambdas that includes a downgraded version of `setuptools`.

If the Authorize.Net bug is not resolved quickly, we should consider a more permanent work-around, as this manually-built image is not an ideal or supportable feature to maintain.

## Steps to reproduce this work-around:
1) Create a public docker repository with one of the many services that offer one
2) Build an image with this `Dockerfile`:

   `docker build . -t local/build-python3.12`

3) Push this image to the public registry that you control:
   ```sh
   docker tag local/build-python3.12 <your registry url>:build-python3.12
   docker push <your registry url>:build-python3.12
   ```

4) Override the default bundler image url with your custom one in `PythonFunction` at [python_function.py](../compact-connect/common_constructs/python_function.py) by adding this to the `super().__init__()` call:
   ```python
   bundling=BundlingOptions(
       image=DockerImage.from_registry('<your registry url>:build-python3.12'),
   ),
   ```
