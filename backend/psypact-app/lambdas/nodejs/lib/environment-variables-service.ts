export class EnvironmentVariablesService {
    private readonly compactsVariable = 'COMPACTS';
    private readonly compactConfigurationTableNameVariable = 'COMPACT_CONFIGURATION_TABLE_NAME';
    private readonly dataEventTableNameVariable = 'DATA_EVENT_TABLE_NAME';
    private readonly uiBasePathUrlVariable = 'UI_BASE_PATH_URL';
    private readonly fromAddressVariable = 'FROM_ADDRESS';
    private readonly debugVariable = 'DEBUG';
    private readonly transactionReportsBucketNameVariable = 'TRANSACTION_REPORTS_BUCKET_NAME';
    private readonly userPoolTypeVariable = 'USER_POOL_TYPE';
    private readonly environmentNameVariable = 'ENVIRONMENT_NAME';

    public getEnvVar(name: string): string {
        return process.env[name]?.trim() || '';
    }

    public getDataEventTableName() {
        return this.getEnvVar(this.dataEventTableNameVariable);
    }

    public getUiBasePathUrl() {
        return this.getEnvVar(this.uiBasePathUrlVariable);
    }

    public getCompactConfigurationTableName() {
        return this.getEnvVar(this.compactConfigurationTableNameVariable);
    }

    public getCompacts(): string[] {
        return JSON.parse(this.getEnvVar(this.compactsVariable));
    }

    public getLogLevel() {
        return this.getEnvVar(this.debugVariable).toLowerCase() == 'true' ? 'DEBUG' : 'INFO';
    }

    public getFromAddress() {
        return this.getEnvVar(this.fromAddressVariable);
    }

    public getTransactionReportsBucketName() {
        return this.getEnvVar(this.transactionReportsBucketNameVariable);
    }

    public getUserPoolType() {
        return this.getEnvVar(this.userPoolTypeVariable);
    }

    public getEnvironmentName() {
        return this.getEnvVar(this.environmentNameVariable);
    }
}
