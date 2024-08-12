//
//  index.js
//  CompactConnect
//
//  Created by InspiringApps on 7/22/2024.
//

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);
const chalk = require('chalk');
const lambdaLocal = require('lambda-local');
const path = require('path');

const _ = chaiMatchPattern.getLodashModule();

process.env.NODE_ENV = 'integration-tests';

const expect = chai.expect;
const testFilename = (filePath) => `test/${path.basename(filePath)}`;
const runLambda = async (config) => {
    const result = await lambdaLocal.execute(config);

    delete result.level;

    return result;
};
const cloner = (obj) => JSON.parse(JSON.stringify(obj));
const lambdaPath = (filePath) => path.join(__dirname, '../..', filePath);
const lambdaConfig = (options = {}) => {
    const config = {
        lambdaPath: (options?.lambdaPath) ? lambdaPath(options.lambdaPath) : null,
        event: {
            Records: [
                {
                    cf: {
                        request: (options?.request) ? cloner(options.request) : {},
                        response: (options?.response) ? cloner(options.response) : {},
                    },
                },
            ],
        },
        timeoutMs: options?.timeoutMs || 3000,
        verboseLevel: options?.verboseLevel || 0, // @DEBUG: Set to 3 to see console.log() statements from Lambda code
    };

    return config;
};

console.log(chalk.blue.bold(`\nUsing environment name: ${process.env.NODE_ENV}`));

module.exports = {
    expect,
    _,
    chalk,
    testFilename,
    runLambda,
    lambdaPath,
    lambdaConfig
};
