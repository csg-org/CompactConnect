# NodeJS Lambdas

This folder contains all lambda runtimes that are written with NodeJS/TypeScript. Because these lambdas are each bundled through CDK with ESBuild, we can pull common code and tests together, leaving only the entrypoints in a lambda-specific folder, leaving ESBuild to pull in only needed lib code.

## Testing

The code in this folder can be tested by running:
- `yarn install`
- `yarn test`

or by using the utility scripts located at `backend/bin`.
