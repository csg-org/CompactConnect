//
//  MilitaryAffiliation.model.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import deleteUndefinedProperties from '@models/_helpers';
import { Compact } from '@models/Compact/Compact.model';
import { dateDisplay } from '@models/_formatters/date';

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceMilitaryAffiliationCreate {
    affiliationType?: string | null;
    compact?: Compact | null;
    dateOfUpdate?: string | null;
    dateOfUpload?: string | null;
    documentKeys?: Array<string> | null;
    fileNames?: Array<string> | null;
    status?: string | null;
}

// ========================================================
// =                        Model                         =
// ========================================================
export class MilitaryAffiliation implements InterfaceMilitaryAffiliationCreate {
    public affiliationType? = null;
    public compact? = null;
    public dateOfUpdate? = null;
    public dateOfUpload? = null;
    public documentKeys? = null;
    public fileNames? = null;
    public status? = null;

    constructor(data?: InterfaceMilitaryAffiliationCreate) {
        const cleanDataObject = deleteUndefinedProperties(data);

        Object.assign(this, cleanDataObject);
    }

    // Helpers
    public dateOfUpdateDisplay(): string {
        return dateDisplay(this.dateOfUpdate);
    }

    public dateOfUploadDisplay(): string {
        return dateDisplay(this.dateOfUpload);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class MilitaryAffiliationSerializer {
    static fromServer(json: any): MilitaryAffiliation {
        const data: any = {
            affiliationType: json.affiliationType,
            compact: json.compact,
            dateOfUpdate: json.dateOfUpdate,
            dateOfUpload: json.dateOfUpload,
            documentKeys: json.documentKeys,
            fileNames: json.fileNames,
            status: json.status
        };

        return new MilitaryAffiliation(data);
    }
}
