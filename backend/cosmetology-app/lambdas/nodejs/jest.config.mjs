export default {
    preset: 'ts-jest',
    transform: {}, // Disables all transformations to commonJS
    testEnvironment: 'node',
    testMatch: ['**/tests/**/*.test.[jt]s?(x)'],
    moduleFileExtensions: ['ts', 'js'],
    verbose: true,
    testPathIgnorePatterns: [
        '<rootDir>/node_modules/',
    ],
    collectCoverageFrom: [
        '**/*.ts',
        '!**/node_modules/**',
        '!**/tests/**',
        '!**/coverage/**',
        '!**/*.d.ts',
        '!**/__mocks__/**',
        '!**/__fixtures__/**',
        '!**/__snapshots__/**',
        '!**/*.config.*',
        '!**/*.test.*',
        '!**/*.spec.*'
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
