export type RecipientType =
    | 'COMPACT_OPERATIONS_TEAM'
    | 'COMPACT_ADVERSE_ACTIONS'
    | 'JURISDICTION_OPERATIONS_TEAM'
    | 'JURISDICTION_ADVERSE_ACTIONS'
    | 'SPECIFIC';

export interface EmailNotificationEvent {
    template: string;
    recipientType: RecipientType;
    compact: string;
    jurisdiction?: string;
    specificEmails?: string[];
    templateVariables: {
        [key: string]: any;
    };
}

export interface EmailNotificationResponse {
    message: string;
}
