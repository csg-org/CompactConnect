//
//  index.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/10/22.
//

//
// Constants
//
// @TODO Define constants items here

/**
 * Check if sessionStorage is available in the browser.
 * @return  TRUE if sessionStorage implementation is available.
 */
const isSessionStorageAvailable = (): boolean => {
    const storage = window.sessionStorage;
    let isAvailable = false;

    if (storage) {
        try {
            const test = '__storage_test__';

            storage.setItem(test, test);
            storage.removeItem(test);
            isAvailable = true;
        } catch (err) {
            console.warn('sessionStorage not available:');
            console.warn(err);
        }
    }

    return isAvailable;
};

/**
 * Set a property's value in storage.
 * @param  key   The storage key.
 * @param  value The storage value.
 * @return       The storage value.
 */
const setItem = (key: string, value: string): string|null => {
    let storageVal: string|null = null;

    if (isSessionStorageAvailable()) {
        window.sessionStorage.setItem(key, value);
        storageVal = value;
    }

    return storageVal;
};

/**
 * Set a property's JSON value in storage.
 * @param  key   The storage key.
 * @param  value The storage value.
 * @return       The storage value.
 */
const setItemJson = (key: string, value: any): string|null => {
    let storageVal: string|null = null;

    if (value) {
        try {
            storageVal = setItem(key, JSON.stringify(value));
        } catch (err) {
            console.warn(`sessionStorage set: ${value} could not be JSON.stringified:`);
            console.warn(err);
        }
    }

    return storageVal;
};

/**
 * Retrieve a property's value from storage.
 * @param  key The storage key.
 * @return     The storage value.
 */
const getItem = (key: string): string|null => {
    let storageVal: string|null = null;

    if (isSessionStorageAvailable()) {
        storageVal = window.sessionStorage.getItem(key);
    }

    return storageVal;
};

/**
 * Retrieve a property's JSON value from storage as an object.
 * @param  key The storage key.
 * @return     The storage value.
 */
const getItemJson = (key: string): any|null => {
    const storageVal = getItem(key);
    let storageJsonObj = null;

    if (storageVal) {
        try {
            storageJsonObj = JSON.parse(storageVal);
        } catch (err) {
            console.warn(`sessionStorage get: ${storageVal} could not be JSON.parsed:`);
            console.warn(err);
        }
    }

    return storageJsonObj;
};

/**
 * Remove a property's value from storage.
 * @param  key The storage key.
 * @return     TRUE if the value was removed.
 */
const removeItem = (key: string): boolean => {
    let isRemoved = false;

    if (isSessionStorageAvailable()) {
        window.sessionStorage.removeItem(key);
        isRemoved = true;
    }

    return isRemoved;
};

export default {
    isSessionStorageAvailable,
    setItem,
    setItemJson,
    getItem,
    getItemJson,
    removeItem,
};
