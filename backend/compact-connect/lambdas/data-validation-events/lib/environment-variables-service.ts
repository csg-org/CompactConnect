export class EnvironmentVariablesService {
    private dataEventTableNameVariable = 'DATA_EVENT_TABLE_NAME';
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
}
