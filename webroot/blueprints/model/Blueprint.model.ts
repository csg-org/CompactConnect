//
//  Blueprint.ts
//  CompactConnect
//
//  Created by InspiringApps on MM/DD/YYYY.
//

import { deleteUndefinedProperties } from '@models/_helpers';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceBlueprintCreate {
    id?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class Blueprint implements InterfaceBlueprintCreate {
    public id? = null;

    constructor(data?: InterfaceBlueprintCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    // @TODO
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class BlueprintSerializer {
    static fromServer(json: any): Blueprint {
        const blueprintData = {
            id: json.id,
        };

        return new Blueprint(blueprintData);
    }

    static toServer(blueprintModel: Blueprint): any {
        return {
            id: blueprintModel.id,
        };
    }
}
