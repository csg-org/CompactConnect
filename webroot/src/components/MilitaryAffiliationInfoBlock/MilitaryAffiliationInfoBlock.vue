<!--
    MilitaryAffiliationInfoBlock.vue
    CompactConnect

    Created by InspiringApps on 2/28/2025.
-->

<template>
    <div class="core-info-block rr-block">
        <div class="info-row">
            <div class="chunk status">
                <div class="chunk-title">{{ $t('military.militaryStatusTitle') }}</div>
                <div class="chunk-text emphasis" :class="{ 'error': isStatusInitializing}">{{ status }}</div>
            </div>
            <div class="chunk affiliation-type">
                <div class="chunk-title">{{ $t('military.affiliationType') }}</div>
                <div class="chunk-text emphasis">{{ affiliationType }}</div>
            </div>
            <div class="chunk audit-status">
                <div class="chunk-title">{{ $t('military.auditStatus') }}</div>
                <div class="chunk-text emphasis">{{ auditStatus }}</div>
                <div v-if="isCompactAdmin" class="audit-button-container">
                    <InputButton
                        :label="$t('military.auditApprove')"
                        :aria-label="$t('military.auditApprove')"
                        :isTransparent="true"
                        :shouldHideMargin="true"
                        class="audit-button approve"
                        @keyup.enter="auditApprove"
                        @click="auditApprove"
                    />
                    <InputButton
                        :label="$t('military.auditDecline')"
                        :aria-label="$t('military.auditDecline')"
                        :isTransparent="true"
                        :shouldHideMargin="true"
                        class="audit-button decline"
                        @keyup.enter="auditDecline"
                        @click="auditDecline"
                    />
                </div>
            </div>
        </div>
        <div v-if="isStatusInitializing" class="info-row error">
            {{$t('military.initializingMessage')}}
        </div>
        <div class="chunk">
            <div v-if="isLoggedInAsLicensee" class="chunk-title">{{ $t('military.previousDocuments') }}</div>
            <div v-else class="chunk-title">{{ $t('military.uploadedDocuments') }}</div>
            <div class="document-list-container" :class="{ 'can-edit': shouldShowEditButtons }">
                <ListContainer
                    listId="military-affiliations"
                    :listData="this.affiliations"
                    :listSize="this.affiliations.length"
                    :sortOptions="sortOptions"
                    :sortChange="sortingChange"
                    :pageChange="paginationChange"
                    :excludeSorting="true"
                    :excludeTopPagination="true"
                    :excludeBottomPagination="true"
                    :isServerPaging="false"
                    :emptyListMessage="$t('military.noUploadedDocuments')"
                    :isLoading="$store.state.user.isLoadingAccount"
                >
                    <template v-slot:headers>
                        <MilitaryDocumentRow
                            :item="militaryDocumentHeader"
                            :isHeaderRow="true"
                            :isDownloadAvailable="isCompactAdmin"
                        />
                    </template>
                    <template v-slot:list>
                        <MilitaryDocumentRow
                            v-for="(record, index) in this.affiliations"
                            :key="index"
                            :item="record"
                            :isDownloadAvailable="isCompactAdmin"
                        />
                    </template>
                </ListContainer>
            </div>
        </div>
        <div v-if="shouldShowEditButtons" class="button-row" :class="{ 'one-button': !shouldShowEndButton }">
            <InputButton
                v-if="shouldShowEndButton"
                :label="$t('military.endMilitaryAffiliation')"
                :aria-label="$t('military.endMilitaryAffiliation')"
                :isTextLike="true"
                :shouldHideMargin="true"
                class="end-affiliation-button"
                @keyup.enter="focusOnModalCancelButton()"
                @click="startEndAffiliationFlow"
            />
            <InputButton
                :label="$t('military.editInfo')"
                :aria-label="$t('military.editInfo')"
                :shouldHideMargin="true"
                class="edit-info-button"
                @click="editInfo"
            />
        </div>
        <Modal
            v-if="shouldShowEndAffiliationModal"
            modalId="end-affiliation-modal"
            class="end-affiliation-modal"
            :closeOnBackgroundClick="true"
            :showActions="false"
            :title="$t('military.endAffiliationModalTitle')"
            @keydown.tab="focusTrap($event)"
            @keyup.esc="closeEndAffiliationModal"
            @close-modal="closeEndAffiliationModal"
        >
            <template v-slot:content>
                <div class="end-affiliation-modal-content">
                    {{ $t('military.endAffiliationModalContent') }}
                    <form @submit.prevent="confirmEndMilitaryAffiliation">
                        <div class="action-button-row">
                            <InputButton
                                id="no-back-button"
                                ref="noBackButton"
                                class="no-back-button"
                                :label="$t('military.noGoBack')"
                                :aria-label="$t('military.noGoBack')"
                                :isTransparent="true"
                                :onClick="closeEndAffiliationModal"
                            />
                            <InputSubmit
                                class="yes-end-button"
                                :formInput="formData.submitEnd"
                                :label="yesEndText"
                                :aria-label="yesEndText"
                            />
                        </div>
                    </form>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script lang="ts" src="./MilitaryAffiliationInfoBlock.ts"></script>
<style scoped lang="less" src="./MilitaryAffiliationInfoBlock.less"></style>
