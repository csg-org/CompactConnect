export class EnvironmentVariablesService {
    private readonly compactsVariable = 'COMPACTS';
    private readonly compactConfigurationTableNameVariable = 'COMPACT_CONFIGURATION_TABLE_NAME';
    private readonly dataEventTableNameVariable = 'DATA_EVENT_TABLE_NAME';
    private readonly uiBasePathUrlVariable = 'UI_BASE_PATH_URL';
    private readonly fromAddressVariable = 'FROM_ADDRESS';
    private readonly debugVariable = 'DEBUG';


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
}
