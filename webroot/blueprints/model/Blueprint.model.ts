//
//  Blueprint.ts
//  <the-app-name>
//
//  Created by InspiringApps on MM/DD/YYYY.
//  Copyright © 2024. <the-customer-name>. All rights reserved.
//

import deleteUndefinedProperties from '@models/_helpers';

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

        // @DEBUG
        // console.log(blueprintData);

        return new Blueprint(blueprintData);
    }

    static toServer(blueprintModel: Blueprint): any {
        return {
            id: blueprintModel.id,
        };
    }
}
