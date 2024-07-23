//
//  Gruntfile.js
//  CompactConnect
//
//  Created by InspiringApps on 7/22/2024.
//

module.exports = function (grunt) {
    require('jit-grunt')(grunt);

    grunt.initConfig({
        //====================
        //= Directory config =
        //====================
        lambdaFiles: [
            '**/**.js',
            '!**/node_modules/**/*.js',
            '!**/dist/**/*.js',
            '!Gruntfile.js',
        ],
        changedFiles: ['<%= lambdaFiles %>'],

        //===========
        //= ES Lint =
        //===========
        eslint: {
            initial: {
                src: ['<%= lambdaFiles %>'],
            },
            watch: {
                src: '<%= changedFiles %>',
            }
        },

        //================
        //= Watch config =
        //================
        watch: {
            lambdaFiles: {
                files: ['<%= lambdaFiles %>'],
                tasks: ['eslint:watch'],
                options: { spawn: false }
            },
        }

    });

    // Update the `changedFiles` value with just the files that changed.
    // Tasks that operate on <%= changedFiles %> will then operate faster.
    var changedFiles = Object.create(null);
    var onChange = grunt.util._.debounce(function() {
        grunt.config('changedFiles', Object.keys(changedFiles));
        changedFiles = Object.create(null);
    }, 200);

    grunt.event.on('watch', function(action, filepath) {
        changedFiles[filepath] = action;
        onChange();
    });

    // Task definition
    grunt.registerTask('default', ['eslint:initial', 'watch']);
    grunt.registerTask('check', ['eslint:initial']);
};
