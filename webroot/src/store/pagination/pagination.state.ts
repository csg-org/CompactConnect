//
//  pagination.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//

export const DEFAULT_PAGE = 1;
export const DEFAULT_PAGE_SIZE = 25;

export interface State {
    paginationMap: {
        page?: number;
        size?: number;
    };
}

export const paginationTemplate = {
    page: DEFAULT_PAGE,
    size: DEFAULT_PAGE_SIZE,
};

export interface PageChangeConfig {
    firstIndex: number;
    lastIndexExclusive: number;
    prevNext?: number; // The increment of the page from the previous page; assists with storing the correct prev / next paging keys sent by the server.
}

export const state: State = {
    paginationMap: {}
};
