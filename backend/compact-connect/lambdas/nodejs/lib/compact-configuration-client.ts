import { Logger } from '@aws-lambda-powertools/logger';
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { unmarshall } from '@aws-sdk/util-dynamodb';
import { EnvironmentVariablesService } from './environment-variables-service';
import { Compact } from './models/compact';

const environmentVariables = new EnvironmentVariablesService();

interface CompactConfigurationClientProperties {
    logger: Logger;
    dynamoDBClient: DynamoDBClient;
}

export class CompactConfigurationClient {
    private readonly logger: Logger;
    private readonly dynamoDBClient: DynamoDBClient;

    constructor(props: CompactConfigurationClientProperties) {
        this.logger = props.logger;
        this.dynamoDBClient = props.dynamoDBClient;
    }

    public async getCompactConfiguration(compact: string): Promise<Compact> {
        this.logger.info('Getting compact configuration', { compact });

        const command = new GetItemCommand({
            TableName: environmentVariables.getCompactConfigurationTableName(),
            Key: {
                'pk': { S: `${compact}#CONFIGURATION` },
                'sk': { S: `${compact}#CONFIGURATION` }
            }
        });

        const response = await this.dynamoDBClient.send(command);

        if (!response.Item) {
            throw new Error(`No configuration found for compact: ${compact}`);
        }

        return unmarshall(response.Item) as Compact;
    }
}
