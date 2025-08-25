<!--
    MilitaryDocumentRow.vue
    InspiringApps modules

    Created by InspiringApps on 4/30/2021.
-->

<template>
    <li class="military-document-row">
        <div class="cell filename" :class="{ 'is-header': isHeaderRow }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('military.fileName') }}:</span>
            {{ item.firstFilenameDisplay() }}
        </div>
        <div class="cell upload-date" :class="{ 'is-header': isHeaderRow }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('military.dateUploaded') }}:</span>
            {{ item.dateOfUploadDisplay() }}
        </div>
        <div v-if="isDownloadAvailable" class="cell download" :class="{ 'is-header': isHeaderRow }">
            <span v-if="$matches.phone.only" class="cell-title">{{ $t('common.downloadFile') }}:</span>
            <span v-else-if="isHeaderRow">{{ item.firstDownloadLink() }}</span>
            <a
                v-if="!isHeaderRow && item.firstDownloadLink()"
                :href="item.firstDownloadLink()"
                :download="item.firstFilenameDisplay()"
                class="download-link"
            >
                <span class="download-text">{{ $t('common.downloadFile') }}</span>
                <DownloadIcon class="download-icon" aria-hidden="true" />
            </a>
            <span v-else-if="!isHeaderRow" class="download-unavailable">
                {{ $t('military.downloadUnavailable') }}
            </span>
        </div>
    </li>
</template>

<script lang="ts" src="./MilitaryDocumentRow.ts"></script>
<style scoped lang="less" src="./MilitaryDocumentRow.less"></style>
