export class EnvironmentVariablesService {
    private readonly compactsVariable = 'COMPACTS';
    private readonly compactConfigurationTableNameVariable = 'COMPACT_CONFIGURATION_TABLE_NAME';
    private readonly dataEventTableNameVariable = 'DATA_EVENT_TABLE_NAME';
    private readonly fromAddressVariable = 'FROM_ADDRESS';
    private readonly debugVariable = 'DEBUG';


    public get(name: string): string {
        return process.env[name]?.trim() || '';
    }

    public getDataEventTableName() {
        return this.get(this.dataEventTableNameVariable);
    }

    public getCompactconfigurationTableName() {
        return this.get(this.compactConfigurationTableNameVariable);
    }

    public getCompacts(): string[] {
        return JSON.parse(this.get(this.compactsVariable));
    }

    public getLogLevel() {
        return this.get(this.debugVariable).toLowerCase() == 'true' ? 'DEBUG' : 'INFO';
    }

    public getFromAddress() {
        return this.get(this.fromAddressVariable);
    }
}
