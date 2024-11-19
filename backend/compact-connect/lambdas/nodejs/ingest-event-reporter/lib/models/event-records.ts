/*
 * Base License Event error record from the event database (after unmarshalling)
 */
export interface IIngestFailureEventRecord {
    pk: string,
    sk: string,
    eventType: string,
    eventTime: string,
    compact: string,
    jurisdiction: string,
    errors: string[],
}


interface IValidationErrorEventErrors {
    [key: string]: string[]
}


export interface IValidationErrorEventRecord {
    pk: string,
    sk: string,
    eventType: string,
    eventTime: string,
    compact: string,
    jurisdiction: string,
    recordNumber: number,
    validData: object,
    errors: IValidationErrorEventErrors
}
