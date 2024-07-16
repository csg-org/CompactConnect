//
//  InputFile.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/8/2020.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinInput from '@components/Forms/_mixins/input.mixin';
import UploadFileIcon from '@components/Icons/UploadFile/UploadFile.vue';
import { FormInput } from '@models/FormInput/FormInput.model';

@Component({
    name: 'InputFile',
    components: {
        UploadFileIcon,
    },
})
class InputFile extends mixins(MixinInput) {
    selectedFiles: Array<File> = reactive([]);
    isDragOver = false;

    //
    // Computed
    //
    get selectLabel(): string {
        const { allowMultiple } = this.formInput.fileConfig;
        let label = (allowMultiple) ? this.$t('common.selectFiles') : this.$t('common.selectFile');

        if (this.selectedFiles.length) {
            label = (allowMultiple) ? this.$t('common.replaceFiles') : this.$t('common.replaceFile');
        }

        return label;
    }

    //
    // Methods
    //
    formatBytes(bytes: number, decimals = 2): string {
        const kilo = 1024;
        const deci = (decimals < 0) ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        let formatted = '0 Bytes';

        if (bytes) {
            const kb = Math.floor(Math.log(bytes) / Math.log(kilo));

            formatted = `${parseFloat((bytes / (kilo ** kb)).toFixed(deci))} ${sizes[kb]}`;
        }

        return formatted;
    }

    blur(formInput: FormInput): void {
        this.validateSelectedFiles(formInput);
    }

    input(formInput: FormInput): void {
        this.updateSelectedFiles();
        this.validateSelectedFiles(formInput);
    }

    dragEnter(event: DragEvent): void {
        const dragTypes = event.dataTransfer?.types || [];

        event.stopPropagation();
        event.preventDefault();

        if (dragTypes.includes('Files')) {
            this.isDragOver = true;
        }
    }

    dragLeave(event: DragEvent): void {
        event.stopPropagation();
        event.preventDefault();

        this.isDragOver = false;
    }

    drop(event: DragEvent): void {
        const dropFiles = event.dataTransfer?.files || [];
        const input: any = this.$refs.inputFiles || {};

        event.stopPropagation();
        event.preventDefault();

        if (dropFiles.length) {
            input.files = dropFiles; // FileLists are read-only, so we can't manipulate based on allowMultiple here
            this.input(this.formInput);
        }

        this.isDragOver = false;
    }

    updateSelectedFiles(): void {
        // $refs are not reactive, so we have to manually update the selected files to a reactive array
        const input = this.$refs.inputFiles || {};
        const { files: fileList = []} = (input as any);
        const files: Array<File> = Array.from(fileList);

        this.selectedFiles = files;
    }

    resetFiles(): void {
        const input: any = this.$refs.inputFiles || {};

        input.value = null;
        this.input(this.formInput);
    }

    validateSelectedFiles(formInput: FormInput): void {
        const { isRequired } = this;
        const files = this.selectedFiles;
        const { fileConfig } = formInput;
        const { maxSizeMbPer, maxSizeMbAll, accepts } = fileConfig;
        const maxSizePer = maxSizeMbPer * 1024 * 1024;
        const maxSizeAll = maxSizeMbAll * 1024 * 1024;
        let areMissing = false;
        let areTooMany = false;
        let areAnyTooLarge = false;
        let areAllTooLarge = false;
        let sizeAll = 0;
        let areAnyWrongType = false;

        // Check number of files
        if (!files.length && isRequired) {
            areMissing = true;
        } else if (files.length > 1 && !fileConfig.allowMultiple) {
            areTooMany = true;
        }

        // Check each selected file
        files.forEach((file) => {
            const { size, type } = file;

            sizeAll += size;

            if (size > maxSizePer) {
                // Size
                (file as any).ia_errorMessage = `${this.$t('inputErrors.sizeTooLargeBy')} ${this.formatBytes(size - maxSizePer)}`;
                areAnyTooLarge = true;
            } else if (!accepts.includes((type as never))) {
                // Type
                (file as any).ia_errorMessage = `${this.$t('inputErrors.fileWrongType')}`;
                areAnyWrongType = true;
            }
        });

        // Check total size
        if (sizeAll > maxSizeAll) {
            areAllTooLarge = true;
        }

        // Update formInput validation fields
        if (areMissing) {
            formInput.errorMessage = this.$t('inputErrors.required');
            formInput.isValid = false;
        } else if (areTooMany) {
            formInput.errorMessage = this.$t('inputErrors.tooManyFiles');
            formInput.isValid = false;
        } else if (areAllTooLarge || areAnyTooLarge) {
            if (formInput.fileConfig.allowMultiple) {
                if (areAllTooLarge) {
                    formInput.errorMessage = `${this.$t('inputErrors.fileGroupTooLargeBy')} ${this.formatBytes(sizeAll - maxSizeAll)}`;
                    formInput.isValid = false;
                } else if (areAnyTooLarge) {
                    formInput.errorMessage = this.$t('inputErrors.oneOrMoreFilesTooLarge');
                    formInput.isValid = false;
                }
            } else if (areAllTooLarge) {
                formInput.errorMessage = `${this.$t('inputErrors.fileTooLargeBy')} ${this.formatBytes(sizeAll - maxSizeAll)}`;
                formInput.isValid = false;
            } else {
                formInput.errorMessage = `${this.$t('inputErrors.fileMaxSize')} ${maxSizeMbPer} MB`;
                formInput.isValid = false;
            }
        } else if (areAnyWrongType) {
            formInput.errorMessage = this.$t('inputErrors.fileWrongType');
            formInput.isValid = false;
        } else {
            formInput.errorMessage = '';
            formInput.isValid = true;
            (formInput as any).value = files;
        }
    }
}

export default toNative(InputFile);

// export { InputFile };
