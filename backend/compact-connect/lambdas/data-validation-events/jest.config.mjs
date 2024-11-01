export default {
    preset: 'ts-jest',
    transform: {}, // Disables all transformations to commonJS
    testEnvironment: 'node',
    testMatch: ['**/tests/**/*.[jt]s?(x)'],
    moduleFileExtensions: ['ts', 'js'],
    verbose: true,
    testPathIgnorePatterns: [
        '<rootDir>/cdk.out/', // It was running tests in the cdk.out directory! Funny.
        '<rootDir>/node_modules/',
    ],
};
