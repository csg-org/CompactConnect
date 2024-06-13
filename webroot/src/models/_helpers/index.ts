const deleteUndefinedProperties = (data = {}) => {
    const cleanObject = { ...data };

    Object.keys(cleanObject).forEach((key) => {
        if (`${key}` in cleanObject && cleanObject[key] === undefined) {
            delete cleanObject[key];
        }
    });

    return cleanObject;
};

export default deleteUndefinedProperties;
