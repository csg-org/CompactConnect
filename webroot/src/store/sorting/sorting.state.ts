//
//  sorting.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//

export enum SortDirection {
    asc = 'asc',
    desc = 'desc'
}

export interface State {
    sortingMap: object;
}

export const state: State = {
    sortingMap: {}
};
