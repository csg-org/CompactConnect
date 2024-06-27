//
//  cors-test.js
//  InspiringApps modules
//
//  Created by InspiringApps on 04/27/2021.
//

/* eslint-disable import/no-extraneous-dependencies */

const { promisify } = require('util');
const { exec } = require('child_process');
const chalk = require('chalk');
const inputOptions = require('inquirer');

const log = console.log; // eslint-disable-line prefer-destructuring
const asyncExec = promisify(exec);

/**
 * Log error output to the console.
 * @param {string}  message       The error message.
 * @param {boolean} [shouldAbort] TRUE if the process should also exit.
 */
const logError = (message, shouldAbort = true) => {
    let logMessage = message || 'Error';

    if (shouldAbort) {
        logMessage += `\nAborting.`;
    }

    log(chalk.red.bold(logMessage));
    log('');

    if (shouldAbort) {
        process.exit();
    }
};

/**
 * Log job success to the console.
 * @param {string} [message] The success message.
 */
const logSuccess = (message) => {
    if (message) {
        log(chalk.green.bold(message));
        log('');
    }
    console.timeEnd('Elapsed Time');
    log('');
};

/**
 * Ask the user to select the origin (browser) domain that would be making the network request.
 * @return {Promise.<string>} The ORIGIN value.
 */
const getOriginDomain = async () => {
    const { originDomain } = await inputOptions.prompt([{
        type: 'list',
        name: 'originDomain',
        message: `What is the Origin (browser) domain?`,
        choices: [
            'http://localhost:3018',
            'https://dev.compactconnect.com', // @TODO: Update once DNS is completed
            'https://test.compactconnect.com', // @TODO: Update once DNS is completed
            'https://www.compactconnect.com', // @TODO: Update once DNS is completed
        ],
    }]);

    return originDomain;
};

/**
 * Ask the user to enter the network endpoint on which CORS will be checked.
 * @return {Promise.<string>} The network endpoint.
 */
const getApiEndpoint = async () => {
    const { apiEndpoint } = await inputOptions.prompt([{
        type: 'input',
        name: 'apiEndpoint',
        message: `What is the fully-qualified API endpoint?`,
    }]);

    return apiEndpoint;
};

/**
 * Ask the user to select the request method for the network endpoint.
 * @return {Promise.<string>} The METHOD value.
 */
const getApiEndpointMethod = async () => {
    const { apiEndpointMethod } = await inputOptions.prompt([{
        type: 'list',
        name: 'apiEndpointMethod',
        message: `What is the API endpoint Method?`,
        choices: [
            'GET',
            'POST',
            'PUT',
            'DELETE',
            'OPTIONS',
        ],
    }]);

    return apiEndpointMethod;
};

/**
 * Perform the cURL command based on user inputs.
 * @return {Promise}
 */
const init = async () => {
    const originDomain = await getOriginDomain();
    const apiEndpoint = await getApiEndpoint();
    const apiEndpointMethod = await getApiEndpointMethod();

    if (originDomain && apiEndpoint && apiEndpointMethod) {
        console.time('Elapsed Time');
        const curlCommand = [
            `curl -i`,
            `-H "Origin: ${originDomain}"`,
            `-H "Access-Control-Request-Method: ${apiEndpointMethod}"`,
            `-H "Access-Control-Request-Headers: X-Requested-With"`,
            `-X OPTIONS ${apiEndpoint}`
        ].join(' ');

        const result = await asyncExec(curlCommand).catch((err) => {
            logError(err, true);
        });

        log('');
        log(result.stdout);
    }
};

// Script Entrypoint
(async () => {
    await init();
})().then(() => {
    logSuccess();
}).catch((err) => {
    logError(err);
});
