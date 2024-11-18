//
//  eslint.config.mjs
//  Adapted from IA Website (all vue-related stuff removed):
//      https://github.com/InspiringApps/IA-Website/blob/cfbaf96be5841cb762a7dcd00a4ccca10fafa672/2021v2/webroot/.eslintrc.js
//
//  Created by InspiringApps on 10/18/2024.
//  Copyright © 2024. All rights reserved.
//
import typescriptParser from '@typescript-eslint/parser';
import typescriptPlugin from '@typescript-eslint/eslint-plugin';

const OFF = 0;
const WARNING = 1;
const ERROR = 2;

export default [
  {
    ignores: ['cdk.out/**/*'],
  },
  {
    files: ['**/*.ts', '**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parser: typescriptParser,
      globals: {
        es2022: true,
        node: true,
      },
    },
    plugins: {
      '@typescript-eslint': typescriptPlugin,
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
      '@typescript-eslint/no-explicit-any': OFF,
      'padding-line-between-statements': [
        ERROR,
        { blankLine: 'always', prev: ['const', 'let', 'var'], next: '*' },
        { blankLine: 'any', prev: ['const', 'let', 'var'], next: ['const', 'let', 'var'] },
      ],
    }
  },
  {
    files: ['**/*.js'],
    rules: {
      '@typescript-eslint/no-var-requires': OFF,
      '@typescript-eslint/camelcase': OFF,
    },
  },
  {
    files: ['**/__tests__/*.{j,t}s?(x)'],
    rules: {
      'no-unused-expressions': OFF,
      'quote-props': OFF,
      'import/no-extraneous-dependencies': OFF,
      '@typescript-eslint/no-var-requires': OFF,
    },
  }
];
