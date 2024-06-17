//
//  .eslintrc.js
//  InspiringApps modules
//
//  Created by InspiringApps on 04/27/2021.
//

const OFF = 0;
const WARNING = 1;
const ERROR = 2;

module.exports = {
    root: true,
    env: {
        node: true,
    },
    plugins: [
        'vue-a11y', // https://github.com/maranran/eslint-plugin-vue-a11y
    ],
    extends: [
        'plugin:vue/essential',
        '@vue/airbnb',
        '@vue/typescript/recommended',
        'plugin:vue-a11y/base',
        'plugin:json/recommended',
    ],
    parserOptions: {
        ecmaVersion: 2020,
        parser: '@typescript-eslint/parser'
    },
    rules: {
        'no-console': (process.env.NODE_ENV === 'production') ? WARNING : OFF,
        'no-debugger': (process.env.NODE_ENV === 'production') ? WARNING : OFF,
        indent: [ ERROR, 4 ],
        quotes: [ ERROR, 'single', {
            allowTemplateLiterals: true,
        }],
        'max-len': [ ERROR, {
            code: 120,
            ignoreComments: true,
            ignoreUrls: true,
            ignoreTemplateLiterals: true,
            ignoreRegExpLiterals: true,
            ignoreStrings: true,
        }],
        'no-multi-spaces': [ ERROR, {
            ignoreEOLComments: true,
        }],
        'arrow-parens': [ ERROR, 'always'],
        'comma-dangle': [ ERROR, {
            functions: 'never',
            imports: 'never',
            exports: 'ignore',
            arrays: 'ignore',
            objects: 'ignore'
        }],
        'array-bracket-spacing': OFF,
        'object-curly-spacing': [ ERROR, 'always', {
            objectsInObjects: false,
            arraysInObjects: false,
        }],
        'no-param-reassign': [ ERROR, { props: false }],
        'max-classes-per-file': [ WARNING, 2 ],
        'lines-between-class-members': [ ERROR, 'always', {
            exceptAfterSingleLine: true,
        }],
        'implicit-arrow-linebreak': OFF,
        'class-methods-use-this': OFF,
        '@typescript-eslint/no-explicit-any': OFF,
        'vue-a11y/click-events-have-key-events': OFF,
        'vue-a11y/no-onchange': OFF,
        'vue-a11y/label-has-for': [ ERROR, {
            components: [ 'Label' ],
            required: {
                some: [ 'nesting', 'id' ]
            },
            allowChildren: false,
        }],
        'padding-line-between-statements': [
            'error',
            {
                blankLine: 'always',
                prev: ['const', 'let', 'var'],
                next: '*'
            },
            {
                blankLine: 'any',
                prev: ['const', 'let', 'var'],
                next: ['const', 'let', 'var'],
            }
        ],
        'no-shadow': OFF,
        '@typescript-eslint/no-shadow': WARNING,
        'vuejs-accessibility/label-has-for': [ ERROR, {
            required: {
                some: ['nesting', 'id'],
            },
        }],
        'vue/multi-word-component-names': OFF,
        'prefer-regex-literals': OFF,
        'no-promise-executor-return': OFF,
    },
    overrides: [
        {
            files: ['**/*.js'],
            rules: {
                '@typescript-eslint/no-var-requires': OFF,
                '@typescript-eslint/camelcase': OFF,
            },
        },
        {
            files: [
                '**/__tests__/*.{j,t}s?(x)',
                '**/*.spec.{j,t}s?(x)',
            ],
            env: {
                mocha: true,
            },
            rules: {
                'no-unused-expressions': 'off',
                'quote-props': 'off',
                'import/no-extraneous-dependencies': 'off',
                '@typescript-eslint/no-var-requires': 'off',
            }
        },
    ],
};
