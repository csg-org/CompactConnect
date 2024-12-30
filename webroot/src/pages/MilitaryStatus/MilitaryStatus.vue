<!--
    MilitaryStatus.vue
    CompactConnect

    Created by InspiringApps on 12/20/2024.
-->

<template>
   <div class="military-status-container">
        <InputButton
            :label="$t('common.back')"
            :aria-label="$t('common.back')"
            :isTextLike="true"
            :shouldHideMargin="true"
            class="back-btn"
            @click="goBack"
        />
        <div class="military-status-title">
            {{ $t('military.militaryStatusTitle') }}
        </div>
        <div class="core-info-block">
            <div class="info-row">
                <div class="chunk">
                    <div class="chunk-title">{{statusTitleText}}</div>
                    <div class="chunk-text">{{status}}</div>
                </div>
                <div class="chunk">
                    <div class="chunk-title">{{affiliationTypeTitle}}</div>
                    <div class="chunk-text">{{affiliationType}}</div>
                </div>
            </div>
            <div class="chunk">
                <div class="chunk-title">{{previouslyUploadedTitle}}</div>
                <div class="prev-doc-table">
                    <ListContainer
                        :listId="listId"
                        :listData="this.militaryDocuments"
                        :listSize="this.militaryDocuments.length"
                        :sortOptions="sortOptions"
                        :sortChange="sortingChange"
                        :pageChange="paginationChange"
                        :excludeSorting="true"
                        :excludeTopPagination="true"
                        :excludeBottomPagination="true"
                        :isServerPaging="false"
                        :emptyListMessage="$t('military.noUploadedDocuments')"
                        :isLoading="$store.state.styleguide.isLoading"
                    >
                        <template v-slot:headers>
                            <MilitaryDocumentRow
                                :item="militaryDocumentHeader"
                                :isHeaderRow="true"
                            />
                        </template>
                        <template v-slot:list>
                            <MilitaryDocumentRow
                                v-for="(record, index) in this.militaryDocuments"
                                :key="index"
                                :item="record"
                            />
                        </template>
                    </ListContainer>
                </div>
            </div>
            <div class="button-row">
                <InputButton
                    :label="$t('military.endMilitaryAffiliation')"
                    :aria-label="$t('military.endMilitaryAffiliation')"
                    :isTextLike="true"
                    :shouldHideMargin="true"
                    class="end-aff-button"
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
        </div>
         <Modal
            v-if="shouldShowEndAffilifationModal"
            class="end-affiliation-modal"
            :closeOnBackgroundClick="true"
            :showActions="false"
            :title="jurisprudenceModalTitle"
            @close-modal="closeAndInvalidateCheckbox"
        >
            <template v-slot:content>
                <div class="jurisprudence-modal-content">
                    {{jurisprudenceModalContent}}
                    <form @submit.prevent="confirmEndMilitaryAffiliation">
                        <div class="action-button-row">
                            <InputButton
                                class="back-button"
                                :label="backText"
                                :isTransparent="true"
                                :onClick="closeAndInvalidateCheckbox"
                            />
                            <InputSubmit
                                class="understand-button"
                                :formInput="formData.submitUnderstanding"
                                :label="iUnderstandText"
                            />
                        </div>
                    </form>
                </div>
            </template>
        </Modal>
   </div>
</template>

<script lang="ts" src="./MilitaryStatus.ts"></script>
<style scoped lang="less" src="./MilitaryStatus.less"></style>
