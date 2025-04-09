//
//  AcceptedAttestationToSend.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/4/2025.
//

import { deleteUndefinedProperties } from '@models/_helpers';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceAcceptedAttestationToSendCreate {
    attestationId?: string | null;
    version?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class AcceptedAttestationToSend implements InterfaceAcceptedAttestationToSendCreate {
    public attestationId? = null;
    public version? = null;

    constructor(data?: InterfaceAcceptedAttestationToSendCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }
}
