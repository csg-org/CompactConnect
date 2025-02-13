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
    dateUpdated?: string | null;
    compact?: Compact | null;
    type?: string | null;
    name?: string | null;
    text?: string | null;
    version?: string | null;
    locale?: string | null;
    isRequired?: boolean;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class PrivilegeAttestation implements InterfacePrivilegeAttestation {
    public $tm?: any = () => [];
    public id? = null;
    public dateCreated? = null;
    public dateUpdated? = null;
    public compact? = null;
    public type? = null;
    public name? = null;
    public text? = null;
    public version? = null;
    public locale? = null;
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

    public dateUpdatedDisplay(): string {
        return dateDisplay(this.dateUpdated);
    }

    public textDisplay(): string {
        const displayText: string = this.text || '';

        return displayText.replace(/(?:\r\n|\r|\n)/g, '<br>');
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class PrivilegeAttestationSerializer {
    static fromServer(json: any): PrivilegeAttestation {
        const privilegeAttestationData = {
            id: json.attestationId,
            dateCreated: json.dateCreated,
            dateUpdated: json.dateOfUpdate,
            compact: new Compact({ type: json.compact }),
            type: json.type,
            name: json.displayName,
            text: json.text,
            version: json.version,
            locale: json.locale,
            isRequired: json.required || false,
        };

        return new PrivilegeAttestation(privilegeAttestationData);
    }
}
