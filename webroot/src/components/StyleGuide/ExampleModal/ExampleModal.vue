<!--
    ExampleModal.vue
    InspiringApps modules

    Created by InspiringApps on 5/4/2021.
-->

<template>
    <Section class="example-modal-section">
        <h2>{{ $t('styleGuide.exampleModal') }}</h2>
        <div class="buttons-container">
            <InputButton :label="$t('styleGuide.openModal')" @click="openModal" />
            <InputButton :label="$t('styleGuide.openErrorModal')" @click="openErrorModal" />
            <InputButton :label="$t('styleGuide.openModalCustomActions')" @click="openCustomActionsModal" />
        </div>
        <Modal
            v-if="isModalVisible"
            :closeOnBackgroundClick="true"
            :title="isErrorModal ? $t('styleGuide.errorModal') : $t('styleGuide.modal')"
            :isErrorModal="isErrorModal"
            @close-modal="closeModal"
        >
            <template v-slot:content>
                <div>
                    {{ modalContent }}
                </div>
            </template>
            <template v-if="showCustomActions" v-slot:actions>
                <div class="custom-actions-container">
                    <InputButton :label="$t('styleGuide.customAction1')" @click="closeModal" />
                    <InputButton :label="$t('styleGuide.customAction2')" @click="closeModal" />
                </div>
            </template>
        </Modal>
    </Section>
</template>

<script lang="ts" src="./ExampleModal.ts"></script>
<style scoped lang="less" src="./ExampleModal.less"></style>
