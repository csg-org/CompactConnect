// No TypeScript dependencies needed for JavaScript-only project

const OFF = 0;
const WARNING = 1;
const ERROR = 2;

export default [
  {
    ignores: ['cdk.out/**/*'],
  },
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'commonjs',
      globals: {
        es2022: true,
        node: true,
      },
    },
    rules: {
      indent: [ERROR, 4],
      'linebreak-style': [ERROR, 'unix'],
      quotes: [ERROR, 'single', { allowTemplateLiterals: true }],
      semi: [ERROR, 'always'],
      'max-len': [ERROR, {
        code: 120,
        ignoreComments: true,
        ignoreUrls: true,
        ignoreTemplateLiterals: true,
        ignoreRegExpLiterals: true,
        ignoreStrings: true,
      }],
      'no-multi-spaces': [ERROR, { ignoreEOLComments: true }],
      'arrow-parens': [ERROR, 'always'],
      'comma-dangle': [ERROR, {
        functions: 'never',
        imports: 'never',
        exports: 'ignore',
        arrays: 'ignore',
        objects: 'ignore',
      }],
      'array-bracket-spacing': OFF,
      'object-curly-spacing': [ERROR, 'always', {
        objectsInObjects: false,
        arraysInObjects: false,
      }],
      'no-param-reassign': [ERROR, { props: false }],
      'max-classes-per-file': [WARNING, 8],
      'lines-between-class-members': [ERROR, 'always', { exceptAfterSingleLine: true }],
      'implicit-arrow-linebreak': OFF,
      'class-methods-use-this': OFF,
      'padding-line-between-statements': [
        ERROR,
        { blankLine: 'always', prev: ['const', 'let', 'var'], next: '*' },
        { blankLine: 'any', prev: ['const', 'let', 'var'], next: ['const', 'let', 'var'] },
      ],
    }
  },
  {
    files: ['**/__tests__/*.js'],
    rules: {
      'no-unused-expressions': OFF,
      'quote-props': OFF,
      'import/no-extraneous-dependencies': OFF,
    },
  }
];
