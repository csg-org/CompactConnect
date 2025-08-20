//
//  nyc.config.js
//  InspiringApps modules
//
//  Created by InspiringApps on 04/27/2021.
//

module.exports = {
    extends: '@istanbuljs/nyc-config-typescript',
    instrument: false,
    'source-map': false,
    all: true,
    include: [
        'src/**/*.ts',
    ],
    exclude: [
        '**/*.d.ts',
        '**/mock*.ts',
        '**/exampleApi/**/*.*',
    ],
    extension: [
        '.ts',
        '.vue',
    ],
    reporter: [
        'text',
        'text-summary',
    ],
    cache: false,
};
