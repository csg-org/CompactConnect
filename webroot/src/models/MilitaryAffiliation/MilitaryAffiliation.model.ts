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
type DownloadLink = {
    filename?: string;
    url?: string;
};

export interface InterfaceMilitaryAffiliationCreate {
    affiliationType?: string | null;
    compact?: Compact | null;
    dateOfUpdate?: string | null;
    dateOfUpload?: string | null;
    documentKeys?: Array<string>;
    fileNames?: Array<string>;
    downloadLinks?: Array<DownloadLink>;
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
    public documentKeys?: Array<string> = [];
    public fileNames?: Array<string> = [];
    public downloadLinks?: Array<DownloadLink> = [];
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

    // These first* helpers take advantage of the fact that only 1 document can be uploaded
    // at a time; to simplify all of the denormalized-but-loosely-keyed array props received from the server.
    public firstFilenameDisplay(): string {
        return this.fileNames?.[0] || '';
    }

    public firstDownloadLink(): string {
        return this.downloadLinks?.[0]?.url || '';
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
