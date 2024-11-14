/*
 * Base License Event error record from the event database (after unmarshalling)
 */
export interface ILicenseErrorEventRecord {
    pk: string,
    sk: string,
    eventType: string,
    time: string,
    compact: string,
    jurisdiction: string,
    errors: string[],
}


export interface ILicenseValidationErrorEventRecord extends ILicenseErrorEventRecord {
    recordNumber: number,
    validData: object,
}
