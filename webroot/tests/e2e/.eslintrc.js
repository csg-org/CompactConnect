//
//  .eslint.js
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
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
