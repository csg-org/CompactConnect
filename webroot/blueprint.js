//
//  blueprint.js
//  InspiringApps modules
//
//  Created by InspiringApps on 04/27/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

/* eslint-disable import/no-extraneous-dependencies */

const { promisify } = require('util');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const chalk = require('chalk');
const moment = require('moment');
const replaceInFile = require('replace-in-file');

const asyncStat = promisify(fs.stat);
const asyncMkdir = promisify(fs.mkdir);
const asyncExec = promisify(exec);

// ====================================
// =            CLI Config            =
// ====================================
//
// Commands
//
const COMMAND_CREATE = 'create';
const COMMAND_DESTROY = 'destroy';

const availableCommands = [
    COMMAND_CREATE,
    COMMAND_DESTROY,
];

//
// Module Types
//
const TYPE_COMPONENT = 'component';
const componentDir = '/src/components';
const blueprintComponentDir = '/blueprints/component';

const TYPE_PAGE = 'page';
const pageDir = '/src/pages';
const blueprintPageDir = '/blueprints/page';

const TYPE_MODEL = 'model';
const modelDir = '/src/models';
const blueprintModelDir = '/blueprints/model';

const availableTypes = [
    TYPE_COMPONENT,
    TYPE_PAGE,
    TYPE_MODEL,
];

// ====================================
// =           Capture Input          =
// ====================================
/**
 * Helper to convert initial string character to uspper / lower case.
 * @param  {string}  str     The input string.
 * @param  {boolean} isCap   TRUE if the first character should be capitalized.
 * @return {string}  updated The updated string.
 */
const strInitialCap = (str, isCap = true) => {
    let updated = str;

    if (typeof str === 'string' && str.length) {
        const initial = (isCap) ? str.charAt(0).toUpperCase() : str.charAt(0).toLowerCase();

        updated = `${initial}${str.slice(1)}`;
    }

    return updated;
};

// Capture command-line args
const params = process.argv;
const command = (params[2]) ? params[2].toLowerCase() : null;
const type = (params[3]) ? params[3].toLowerCase() : null;
const name = (params[4]) ? strInitialCap(params[4]) : null;
const subPath = (params[5]) ? params[5].replace(/^\/+/, '') : null; // Remove leading slash

/**
 * Validate CLI inputs.
 * @return {Boolean}
 */
const isValidInput = () => {
    const isCommandValid = availableCommands.includes(command);
    const isTypeValid = availableTypes.includes(type);
    const isNameValid = (name && typeof name === 'string');
    const isPathValid = ((subPath && typeof subPath === 'string') || subPath === null);

    return isCommandValid && isTypeValid && isNameValid && isPathValid;
};

/**
 * Show CLI Help.
 */
const showHelp = () => {
    console.log('');
    console.log(chalk.yellow('BLUEPRINT HELP:'));
    console.log('');
    console.log(`${chalk.bold('Usage:')} node blueprint [command] [type] [name] [sub-path]`);
    console.log('');
    console.log(`${chalk.bold('commands:')} ${availableCommands.join(', ')} ${chalk.italic('(requires 1)')}`);
    console.log(`${chalk.bold('types:')} ${availableTypes.join(', ')} ${chalk.italic('(requires 1)')}`);
    console.log(`${chalk.bold('name:')} <name of module; e.g. LoginForm> ${chalk.italic('(required)')}`);
    console.log(`${chalk.bold('sub-path:')} <sub-path under main module folder; e.g. /Forms> ${chalk.italic('(optional)')}`);
    console.log('');
    console.log(chalk.bold('Examples:'));
    console.log('node blueprint create component LoginForm');
    console.log('node blueprint create component LoginForm /Forms');
    console.log('');
    console.log('node blueprint create page Login');
    console.log('');
    console.log('node blueprint create model User');
    console.log('');
};

/**
 * Helper to create directories
 * @param  {string}  cwd The current working directory of the command.
 * @param  {string}  dir The directory to add.
 * @return {Promise}
 */
const createDirectory = async (cwd, dir) => {
    if (!cwd) {
        throw new Error('cwd required');
    } else if (!dir) {
        throw new Error('dir required');
    } else {
        await asyncMkdir(path.join(cwd, dir));
    }
};

/**
 * Helper to remove directories
 * @param  {string}  cwd The current working directory of the command.
 * @param  {string}  dir The directory to remove.
 * @return {Promise}
 */
const removeDirectory = async (cwd, dir) => {
    if (!cwd) {
        throw new Error('cwd required');
    } else if (!dir) {
        throw new Error('dir required');
    } else {
        await asyncExec(`rm -rf ${dir}`, { cwd });
    }
};

/**
 * Check and prepare the affected directories.
 * @param  {string}  moduleType       The module type.
 * @param  {string}  [moduleSubPath]  The optional sub-path under the module top-level.
 * @param  {string}  moduleName       The module name.
 * @param  {Boolean} [isDelete=false] TRUE if deleting module.
 * @return {Promise} workingPath      The new module directory path.
 */
const prepDirectories = async (moduleType, moduleSubPath, moduleName, isDelete = false) => {
    let moduleTopDir; // Relative top-level module path within project
    let workingPath;  // Full absolute working path (cwd / pwd)

    switch (moduleType) {
    case TYPE_COMPONENT:
        moduleTopDir = componentDir;
        break;
    case TYPE_PAGE:
        moduleTopDir = pageDir;
        break;
    case TYPE_MODEL:
        moduleTopDir = modelDir;
        break;
    default:
        break;
    }

    // Make sure the module top-level directory exists (e.g. /components)
    if (moduleTopDir) {
        workingPath = path.join(__dirname, moduleTopDir);
        const stats = await asyncStat(workingPath).catch(() => null);

        if (!stats || !stats.isDirectory()) {
            throw new Error(`Project folder not found for type '${moduleType}': ${moduleTopDir}`);
        }
    } else {
        throw new Error(`Project folder not found for type '${moduleType}'`);
    }

    // Make sure the optional subPath exists for deletes, or exists if creating a module
    if (moduleSubPath) {
        workingPath = path.join(__dirname, moduleTopDir, moduleSubPath);
        const stats = await asyncStat(workingPath).catch(() => null);

        if (isDelete && (!stats || !stats.isDirectory())) {
            // Deleting but doesn't exist
            throw new Error(`Sub-path not found: ${moduleTopDir}/${moduleSubPath}`);
        } else if (!stats || !stats.isDirectory()) {
            // Adding but subPath doesn't exist yet
            await createDirectory(path.join(__dirname, moduleTopDir), moduleSubPath);
        }
    }

    // Make sure the new module directory exists at the right path
    if (moduleName) {
        const modulePath = path.join(workingPath, moduleName);
        const msgPath = `${moduleTopDir}/${(moduleSubPath) ? `/${moduleSubPath}` : ''}${moduleName}`;
        const stats = await asyncStat(modulePath).catch(() => null);

        if (isDelete && (!stats || !stats.isDirectory())) {
            // Deleting but doesn't exist
            throw new Error(`Module path not found: ${msgPath}`);
        } else if (!isDelete && stats && stats.isDirectory()) {
            // Adding but already exists
            throw new Error(`Module path already exists: ${msgPath}`);
        } else if (isDelete && stats && stats.isDirectory()) {
            // Remove module directory
            await removeDirectory(workingPath, moduleName);
        } else if (!stats || !stats.isDirectory()) {
            // Create module directory
            await createDirectory(workingPath, moduleName);
        }

        workingPath = modulePath;
    } else {
        throw new Error(`Invalid module name '${moduleName}'`);
    }

    return workingPath;
};

/**
 * Copy blueprint files to new module, replace module-specific text.
 * @param  {string}  moduleType      The module type.
 * @param  {string}  workingPath     The full directory path of the module.
 * @param  {string}  [moduleSubPath] The optional sub-path under the module top-level.
 * @param  {string}  moduleName      The module name.
 * @return {Promise}
 */
const copyFiles = async (moduleType, workingPath, moduleSubPath, moduleName) => {
    let blueprintDir;
    const blueprintFiles = [];

    switch (moduleType) {
    case TYPE_COMPONENT:
        blueprintDir = path.join(__dirname, blueprintComponentDir);
        blueprintFiles.push('Blueprint.less');
        blueprintFiles.push('Blueprint.spec.ts');
        blueprintFiles.push('Blueprint.ts');
        blueprintFiles.push('Blueprint.vue');
        break;
    case TYPE_PAGE:
        blueprintDir = path.join(__dirname, blueprintPageDir);
        blueprintFiles.push('Blueprint.less');
        blueprintFiles.push('Blueprint.spec.ts');
        blueprintFiles.push('Blueprint.ts');
        blueprintFiles.push('Blueprint.vue');
        break;
    case TYPE_MODEL:
        blueprintDir = path.join(__dirname, blueprintModelDir);
        blueprintFiles.push('Blueprint.model.spec.ts');
        blueprintFiles.push('Blueprint.model.ts');
        break;
    default:
        break;
    }

    if (!blueprintDir || !workingPath) {
        throw new Error(`Unable to copy files from '${blueprintDir}' to '${workingPath}'`);
    } else if (!moduleName) {
        throw new Error(`moduleName is required to create module files`);
    }

    if (blueprintDir) {
        await Promise.all(blueprintFiles.map(async (blueprintFile) => {
            const moduleFile = blueprintFile.replace('Blueprint', moduleName);
            const moduleFilePath = `${workingPath}/${moduleFile}`;

            await asyncExec(`cp ${blueprintFile} ${moduleFilePath}`, { cwd: blueprintDir });
            await replaceInFile({
                files: moduleFilePath,
                from: [
                    /Blueprint/g,
                    /blueprint/g,
                    /\/SubPath/g,
                    /MM\/DD\/YYYY/g
                ],
                to: [
                    moduleName,
                    strInitialCap(moduleName, false),
                    (moduleSubPath) ? `/${moduleSubPath}` : '',
                    moment().format('M/D/YYYY')
                ],
            });
        }));
    }
};

/**
 * Helper to display an error object in the console.
 * @param {Error} errorObj A native Error object.
 */
const showError = (errorObj) => {
    if (errorObj) {
        if (errorObj.message) {
            console.log(chalk.red(errorObj.message));
        }
        if (errorObj.stack) {
            console.log(errorObj.stack);
        }
    } else {
        console.log(chalk.red('An unkown error ocurred'));
    }
};

/**
 * The main logic controller.
 * @return {Promise}
 */
const main = async () => {
    const isDelete = (command === COMMAND_DESTROY);
    const workingPath = await prepDirectories(type, subPath, name, isDelete);

    if (!isDelete) {
        await copyFiles(type, workingPath, subPath, name);
    }

    const action = (isDelete) ? 'deleted' : 'created';

    console.log(chalk.green(`${type} ${name} successfully ${action}`));
};

// Entry point
try {
    (async () => {
        if (isValidInput()) {
            await main();
        } else {
            showHelp();
        }
    })().catch((err) => {
        showError(err);
    });
} catch (err) {
    showError(err);
}
