//
//  utils.js
//  InspiringApps modules
//
//  Created by InspiringApps on 8/25/21.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

export const hexToRgb = (hex) => {
    const rgb = hex
        .replace(/^#?([a-f\d])([a-f\d])([a-f\d])$/i, (m, r, g, b) => `#${r}${r}${g}${g}${b}${b}`)
        .substring(1)
        .match(/.{2}/g)
        .map((x) => parseInt(x, 16));

    return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
};

export const appColors = {
    blue: hexToRgb('#1C7CB0'),
    get midBlue() { return this.blue; },
    lightGrey: hexToRgb('#c8c8c8'),
    midGrey: hexToRgb('#9a9a9a'),
    midGreen: hexToRgb('#359444'),
    midOrange: hexToRgb('#f9b625'),
    midRed: hexToRgb('#ac2d2f'),
    white: hexToRgb('#ffffff'),
    black: hexToRgb('#000000'),
    purple: hexToRgb('#6625f9'),
    pink: hexToRgb('#f125f9'),
    red: hexToRgb('#ac2d2f'),
    get primaryColor() { return this.midBlue; },
};

export const getNumberOfPages = (recordsListLength, pageSize) =>
    ((recordsListLength % pageSize > 0)
        ? (Math.floor(recordsListLength / pageSize)) + 1
        : Math.floor(recordsListLength / pageSize));
