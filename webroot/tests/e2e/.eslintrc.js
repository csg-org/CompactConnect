//
//  .eslint.js
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

module.exports = {
    plugins: [
        'cypress',
    ],
    env: {
        mocha: true,
        'cypress/globals': true,
    },
    rules: {
        strict: 'off',
    },
};
