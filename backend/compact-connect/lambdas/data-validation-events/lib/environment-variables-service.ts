export class EnvironmentVariablesService {
    private dataEventTableNameVariable = 'DATA_EVENT_TABLE_NAME';
    private fromAddressVariable = 'FROM_ADDRESS';
    private debugVariable = 'DEBUG';


    public get(name: string): string {
        return process.env[name]?.trim() || '';
    }

    public getDataEventTableName() {
        return this.get(this.dataEventTableNameVariable);
    }

    public getLogLevel() {
        return this.get(this.debugVariable).toLowerCase() == 'true' ? 'DEBUG' : 'INFO';
    }

    public getFromAddress() {
        return this.get(this.fromAddressVariable);
    }
}
