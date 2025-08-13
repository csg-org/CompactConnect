//
//  MilitaryAffiliation.model.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import { deleteUndefinedProperties } from '@models/_helpers';
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
    documentKeys?: Array<string>;
    fileNames?: Array<string>;
    downloadLinks?: Array<{
        filename?: string,
        url?: string,
    }>;
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
    public documentKeys? = [];
    public fileNames? = [];
    public downloadLinks? = [];
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

    public firstFilenameDisplay(): string {
        return this.fileNames?.[0] || '';
    }

    public firstDownloadLink(): string {
        return (this.downloadLinks?.[0] as any)?.url || ''; // any needed to make TS compiler happy since it loses track of its own types here; open to suggestion
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
            downloadLinks: [],
            status: json.status
        };

        if (Array.isArray(json.downloadLinks)) {
            json.downloadLinks.forEach((downloadLink) => {
                data.downloadLinks.push({
                    filename: downloadLink.fileName || '',
                    url: downloadLink.url || '',
                });
            });
        }

        return new MilitaryAffiliation(data);
    }
}
