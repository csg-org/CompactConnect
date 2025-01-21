//
//  PrivilegeAttestation.ts
//  CompactConnect
//
//  Created by InspiringApps on 1/21/2025.
//

import deleteUndefinedProperties from '@models/_helpers';
import { dateDisplay } from '@models/_formatters/date';
import { Compact } from '@models/Compact/Compact.model';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfacePrivilegeAttestation {
    id?: string | null;
    dateCreated?: string | null;
    compact?: Compact | null;
    type?: string | null;
    text?: string | null;
    version?: string | null;
    isRequired?: boolean;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class PrivilegeAttestation implements InterfacePrivilegeAttestation {
    public $tm?: any = () => [];
    public id? = null;
    public dateCreated? = null;
    public compact? = null;
    public type? = null;
    public text? = null;
    public version? = null;
    public isRequired? = false;

    constructor(data?: InterfacePrivilegeAttestation) {
        const cleanDataObject = deleteUndefinedProperties(data);
        const global = window as any;
        const $tm = global.Vue?.config?.globalProperties?.$tm;

        if ($tm) {
            this.$tm = $tm;
        }

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public dateCreatedDisplay(): string {
        return dateDisplay(this.dateCreated);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class PrivilegeAttestationSerializer {
    static fromServer(json: any, attestationId: string): PrivilegeAttestation {
        const privilegeAttestationData = {
            id: attestationId,
            dateCreated: json.dateCreated,
            compact: new Compact({ type: json.compact }),
            type: json.type,
            text: json.text,
            version: json.version,
            isRequired: json.required || false,
        };

        return new PrivilegeAttestation(privilegeAttestationData);
    }

    static toServer(privilegeAttestation: PrivilegeAttestation): any {
        return {
            attestationId: privilegeAttestation.id,
            version: privilegeAttestation.version,
        };
    }
}
