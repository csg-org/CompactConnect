<!--
    MilitaryAffiliationInfoBlock.vue
    CompactConnect

    Created by InspiringApps on 2/28/2025.
-->

<template>
    <div class="core-info-block">
        <div class="info-row">
            <div class="chunk">
                <div class="chunk-title">{{statusTitleText}}</div>
                <div class="chunk-text">{{status}}</div>
            </div>
            <div class="chunk affiliation-type">
                <div class="chunk-title">{{affiliationTypeTitle}}</div>
                <div class="chunk-text">{{affiliationType}}</div>
            </div>
        </div>
        <div class="chunk">
            <div class="chunk-title">{{previouslyUploadedTitle}}</div>
            <div class="prev-doc-table">
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
                        />
                    </template>
                    <template v-slot:list>
                        <MilitaryDocumentRow
                            v-for="(record, index) in this.affiliations"
                            :key="index"
                            :item="record"
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
                class="end-aff-button"
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
            class="end-affiliation-modal"
            :closeOnBackgroundClick="true"
            :showActions="false"
            :title="endAffiliationModalTitle"
            @keydown.tab="focusTrap($event)"
            @keyup.esc="closeEndAffilifationModal"
            @close-modal="closeEndAffilifationModal"
        >
            <template v-slot:content>
                <div class="end-affiliation-modal-content">
                    {{endAffiliationModalContent}}
                    <form @submit.prevent="confirmEndMilitaryAffiliation">
                        <div class="action-button-row">
                            <InputButton
                                id="no-back-button"
                                ref="noBackButton"
                                class="no-back-button"
                                :label="backText"
                                :aria-label="backText"
                                :isTransparent="true"
                                :onClick="closeEndAffilifationModal"
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
