//
//  search.api.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/15/25.
//

// import { FeatureGates } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import {
    requestError,
    requestSuccess,
    responseSuccess,
    responseError
} from '@network/searchApi/interceptors';
import { SortDirection } from '@store/sorting/sorting.state';
import { LicenseeSerializer } from '@models/Licensee/Licensee.model';
import axios, { AxiosInstance } from 'axios';

export interface SearchParamsInterfaceLocal {
    isPublic?: boolean;
    compact?: string;
    licenseeFirstName?: string;
    licenseeLastName?: string;
    homeState?: string;
    privilegeState?: string;
    privilegePurchaseStartDate?: string;
    privilegePurchaseEndDate?: string;
    militaryStatus?: string;
    investigationStatus?: string;
    encumberStartDate?: string;
    encumberEndDate?: string;
    npi?: string;
    pageSize?: number;
    pageNumber?: number;
    sortBy?: string;
    sortDirection?: string;
    isForPrivileges?: boolean;
}

export interface SearchParamsInterfaceRemote {
    from?: number;
    size?: number;
    sort?: Array<{
        [key: string]: {
            order?: string,
        }
    }>;
    query?: {
        match_all?: object, // eslint-disable-line camelcase
        bool?: {
            must: Array<{
                [key: string]: any,
            }>,
        },
    };
}

const appWindow = window as any;

appWindow.ccQueryToggle = (): void => {
    if (appWindow.ccIsQueryLogEnabled) {
        appWindow.ccIsQueryLogEnabled = false;
        console.log('CompactConnect search query logging: DISABLED');
    } else {
        appWindow.ccIsQueryLogEnabled = true;
        console.log('CompactConnect search query logging: ENABLED');
    }
};

export interface DataApiInterface {
    api: AxiosInstance;
}

export class SearchDataApi implements DataApiInterface {
    api: AxiosInstance;

    public constructor() {
        // Initial Axios config
        this.api = axios.create({
            baseURL: envConfig.apiUrlSearch,
            timeout: 30000,
            headers: {
                'Cache-Control': 'no-cache',
                Accept: 'application/json',
                get: {
                    Accept: 'application/json',
                },
                post: {
                    'Content-Type': 'application/json',
                },
                put: {
                    'Content-Type': 'application/json',
                },
            },
        });
    }

    /**
     * Attach Axios interceptors with injected contexts.
     * https://github.com/axios/axios#interceptors
     * @param {Store} store
     */
    public initInterceptors(store) {
        const requestSuccessInterceptor = requestSuccess();
        const requestErrorInterceptor = requestError();
        const responseSuccessInterceptor = responseSuccess();
        const responseErrorInterceptor = responseError(store);

        // Request Interceptors
        this.api.interceptors.request.use(
            requestSuccessInterceptor,
            requestErrorInterceptor
        );
        // Response Interceptors
        this.api.interceptors.response.use(
            responseSuccessInterceptor,
            responseErrorInterceptor
        );
    }

    /**
     * Prep a query request for Search requests.
     * @param  {SearchParamsInterfaceLocal}  params The request query parameters config.
     * @return {SearchParamsInterfaceRemote}        The request query body.
     */
    public prepRequestSearchParams(params: SearchParamsInterfaceLocal = {}): SearchParamsInterfaceRemote {
        const {
            licenseeFirstName,
            licenseeLastName,
            homeState,
            privilegeState,
            privilegePurchaseStartDate,
            privilegePurchaseEndDate,
            militaryStatus,
            investigationStatus,
            encumberStartDate,
            encumberEndDate,
            npi,
            pageSize,
            pageNumber,
            sortBy,
            sortDirection,
            isForPrivileges
        } = params;
        const hasSearchTerms = Boolean(
            licenseeFirstName
            || licenseeLastName
            || homeState
            || privilegeState
            || privilegePurchaseStartDate
            || privilegePurchaseEndDate
            || militaryStatus
            || investigationStatus
            || encumberStartDate
            || encumberEndDate
            || npi
        );
        const requestParams: SearchParamsInterfaceRemote = {};

        // QUERY
        // https://docs.opensearch.org/latest/query-dsl/
        if (hasSearchTerms) {
            requestParams.query = {
                bool: {
                    must: [],
                },
            };
            const conditions = requestParams.query?.bool?.must || [];

            //
            // Licensee search props
            //
            if (licenseeFirstName) {
                conditions.push({ match_phrase_prefix: { givenName: licenseeFirstName }});
            }
            if (licenseeLastName) {
                conditions.push({ match_phrase_prefix: { familyName: licenseeLastName }});
            }
            if (homeState) {
                conditions.push({ term: { licenseJurisdiction: homeState }});
            }
            if (militaryStatus) {
                conditions.push({ term: { militaryStatus }});
            }
            if (npi) {
                conditions.push({ match: { npi }});
            }
            //
            // Privilege search props
            //
            if (privilegeState || privilegePurchaseStartDate || privilegePurchaseEndDate) {
                const privilegeCondition: any = {
                    nested: {
                        path: 'privileges',
                        query: {
                            bool: {},
                        },
                    },
                };
                const privilegeConditionBool = privilegeCondition.nested.query.bool;

                if (isForPrivileges) {
                    privilegeCondition.nested.inner_hits = {};
                }

                if (privilegeState) {
                    privilegeConditionBool.must = [
                        { term: { 'privileges.jurisdiction': privilegeState }},
                    ];
                }

                if (privilegePurchaseStartDate || privilegePurchaseEndDate) {
                    privilegeConditionBool.should = [];
                    privilegeConditionBool.minimum_should_match = 1;
                    const dateConditions = [
                        {
                            range: {
                                'privileges.dateOfIssuance': {},
                            },
                        },
                        {
                            range: {
                                'privileges.dateOfRenewal': {},
                            },
                        },
                    ];

                    dateConditions.forEach((dateCondition) => {
                        const { range } = dateCondition;

                        Object.keys(range).forEach((nestedDateKey) => {
                            if (privilegePurchaseStartDate) {
                                range[nestedDateKey].gte = privilegePurchaseStartDate;
                            }
                            if (privilegePurchaseEndDate) {
                                range[nestedDateKey].lte = privilegePurchaseEndDate;
                            }
                        });
                        privilegeConditionBool.should.push(dateCondition);
                    });
                }

                conditions.push(privilegeCondition);
            }
            //
            // Adverse action search props
            //
            if (encumberStartDate || encumberEndDate) {
                const subConditions: any = {
                    bool: {
                        should: [],
                        minimum_should_match: 1,
                    }
                };
                const getSubCondition = (topPath: string) => {
                    const nestedPath = `${topPath}.adverseActions`;
                    const subCondition = {
                        nested: {
                            path: topPath,
                            query: {
                                nested: {
                                    path: nestedPath,
                                    query: {
                                        range: {
                                            [`${nestedPath}.effectiveStartDate`]: {},
                                        },
                                    },
                                },
                            },
                        },
                    };
                    const subConditionRule: { gte?: string, lte?: string } = subCondition.nested.query.nested.query.range[`${nestedPath}.effectiveStartDate`];

                    if (encumberStartDate) {
                        subConditionRule.gte = encumberStartDate;
                    }
                    if (encumberEndDate) {
                        subConditionRule.lte = encumberEndDate;
                    }

                    return subCondition;
                };

                subConditions.bool.should.push(getSubCondition('licenses'));
                subConditions.bool.should.push(getSubCondition('privileges'));

                conditions.push(subConditions);
            }
            //
            // Investigation search props
            //
            if (investigationStatus) {
                const subConditions: any = { bool: {}};
                const getSubCondition = (topPath: string) => {
                    const nestedPath = `${topPath}.investigations`;
                    const subCondition = {
                        nested: {
                            path: topPath,
                            query: {
                                nested: {
                                    path: nestedPath,
                                    query: {
                                        term: { [`${nestedPath}.type`]: 'investigation' },
                                    },
                                },
                            },
                        },
                    };

                    return subCondition;
                };

                if (investigationStatus === 'underInvestigation') {
                    subConditions.bool.should = [
                        getSubCondition('licenses'),
                        getSubCondition('privileges'),
                    ];
                    subConditions.bool.minimum_should_match = 1;
                } else {
                    subConditions.bool.must_not = [
                        getSubCondition('licenses'),
                        getSubCondition('privileges'),
                    ];
                }

                conditions.push(subConditions);
            }
        } else {
            requestParams.query = {
                match_all: {},
            };
        }

        // PAGING
        // https://docs.opensearch.org/latest/search-plugins/searching-data/paginate/#the-from-and-size-parameters
        if (pageSize) {
            requestParams.size = pageSize;

            if (pageNumber) {
                requestParams.from = pageSize * (pageNumber - 1);
            }
        }

        // SORT
        // https://docs.opensearch.org/latest/search-plugins/searching-data/sort/
        if (sortBy) {
            requestParams.sort = [{
                [`${sortBy}.keyword`]: {
                    order: sortDirection || SortDirection.asc,
                },
            }];
        }

        return requestParams;
    }

    /**
     * GET Licensees (Search - Staff).
     * @param  {SearchParamsInterfaceLocal} [params={}] The request query parameters config.
     * @return {Promise<object>}                        Response metadata + an array of licensees.
     */
    public async getLicenseesSearchStaff(params: SearchParamsInterfaceLocal = {}) {
        const requestParams: SearchParamsInterfaceRemote = this.prepRequestSearchParams(params);

        if (appWindow.ccIsQueryLogEnabled) {
            console.log(`${new Date()}:`);
            console.log(JSON.stringify(requestParams, null, 2));
            console.log(``);
        }

        const serverResponse: any = await this.api.post(`/v1/compacts/${params.compact}/providers/search`, requestParams);
        const { total = {}, providers } = serverResponse;
        const { value: totalMatchCount } = total;
        const response = {
            totalMatchCount,
            licensees: providers.map((serverItem) => LicenseeSerializer.fromServer(serverItem)),
        };

        return response;
    }

    /**
     * GET Privileges (Export - Staff).
     * @param  {SearchParamsInterfaceLocal} [params={}] The request query parameters config.
     * @return {Promise<object>}                        Response metadata + an array of licensees.
     */
    public async getPrivilegesExportStaff(params: SearchParamsInterfaceLocal = {}) {
        const requestParams: SearchParamsInterfaceRemote = this.prepRequestSearchParams(params);

        if (appWindow.ccIsQueryLogEnabled) {
            console.log(`${new Date()}:`);
            console.log(JSON.stringify(requestParams, null, 2));
            console.log(``);
        }

        const serverResponse: any = await this.api.post(`/v1/compacts/${params.compact}/privileges/export`, requestParams);

        return serverResponse;

        // return {
        //     downloadUrl: 'https://cdn.prod.website-files.com/66a083c22bdfd06a6aee5193/6913a447111789a56d2f13b9_IA-Logo-Primary-FullColor.svg',
        // };
    }
}

export const searchDataApi = new SearchDataApi();
