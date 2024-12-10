export default {
    preset: 'ts-jest',
    transform: {}, // Disables all transformations to commonJS
    testEnvironment: 'node',
    testMatch: ['**/tests/*.test.[jt]s?(x)'],
    moduleFileExtensions: ['ts', 'js'],
    verbose: true,
    testPathIgnorePatterns: [
        '<rootDir>/node_modules/',
    ],
    coverageThreshold: {
        global: {
            branches: 90,
            functions: 90,
            lines: 90,
            statements: 90,
        }
    }
};
